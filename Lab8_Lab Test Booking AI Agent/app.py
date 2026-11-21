"""Simple Streamlit UI for the existing LangChain lab booking agent."""
import os
from uuid import uuid4
import streamlit as st
from langgraph.types import Command
from backend import create_booking_agent, UserContext

st.set_page_config(page_title="Lab Booking Assistant", page_icon="🧪", layout="centered")
st.title("🧪 Lab Test Booking Assistant")
st.caption("Demo lab • Chat, check slots, and manage bookings")

try:
    key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))
except Exception:
    key = os.getenv("GROQ_API_KEY", "")
if not key:
    st.error("Add GROQ_API_KEY to Streamlit secrets or your environment before starting.")
    st.stop()

@st.cache_resource
def get_agent():
    return create_booking_agent(key)

agent = get_agent()
st.session_state.setdefault("chats", {})

with st.sidebar:
    st.header("Demo patient")
    user_id = st.selectbox("Choose user", ["user_101", "user_202"])
    st.caption("For demonstration only; real applications need authenticated identities.")
    st.info("Prices and appointment times are read from SQLite.")

if user_id not in st.session_state.chats:
    st.session_state.chats[user_id] = {
        "thread_id": str(uuid4()), "history": [], "pending": False
    }
chat = st.session_state.chats[user_id]
config = {"configurable": {"thread_id": chat["thread_id"]}}
context = UserContext(user_id=user_id)


def show_result(result):
    # Show each call, then the latest response. Do not execute any tools here.
    calls = [c["name"] for m in result.get("messages", [])
             for c in (getattr(m, "tool_calls", None) or [])]
    if calls:
        chat["history"].append(("caption", "Tools: " + ", ".join(calls)))
    interrupts = result.get("__interrupt__", [])
    if interrupts:
        chat["pending"] = True
        chat["requests"] = interrupts[0].value.get("action_requests", [])
    else:
        chat["pending"] = False
        reply = next((str(m.content) for m in reversed(result["messages"])
                      if m.type == "ai" and m.content), "No response generated.")
        chat["history"].append(("assistant", reply))

for role, content in chat["history"]:
    if role == "caption":
        st.caption(content)
    else:
        with st.chat_message(role):
            st.markdown(content)

if chat["pending"]:
    st.warning("Approval required before modifying the database.")
    for request in chat.get("requests", []):
        st.code(f"{request['name']}: {request['args']}", language="text")
    col1, col2 = st.columns(2)
    choice = None
    if col1.button("✅ Approve", type="primary", use_container_width=True):
        choice = "approve"
    if col2.button("❌ Reject", use_container_width=True):
        choice = "reject"
    if choice:
        with st.spinner("Processing decision..."):
            try:
                decisions = [{"type": choice} if choice == "approve"
                             else {"type": "reject", "message": "Patient rejected this action."}
                             for _ in chat["requests"]]
                result = agent.invoke(Command(resume={"decisions": decisions}),
                                      config=config, context=context)
                show_result(result)
                st.rerun()
            except Exception as exc:
                st.error(f"Could not process decision: {exc}")
else:
    prompt = st.chat_input("Ask about tests, slots, or your bookings...")
    if prompt:
        chat["history"].append(("user", prompt))
        with st.spinner("Checking..."):
            try:
                result = agent.invoke({"messages": [{"role": "user", "content": prompt}]},
                                      config=config, context=context)
                show_result(result)
                st.rerun()
            except Exception as exc:
                st.error(f"Request failed: {exc}")
