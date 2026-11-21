"""Lab booking backend extracted from the verified project notebook."""
import os
import sqlite3
from pathlib import Path
from datetime import date, timedelta
from langchain.tools import tool, ToolRuntime
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langchain_groq import ChatGroq
from ddgs import DDGS

DB_PATH = Path(__file__).with_name("lab_booking.db")
conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
conn.execute("PRAGMA foreign_keys = ON")
cursor = conn.cursor()


cursor.executescript("""
CREATE TABLE IF NOT EXISTS tests (
    test_id INTEGER PRIMARY KEY,
    test_name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL CHECK(price >= 0)
);

CREATE TABLE IF NOT EXISTS slots (
    slot_id INTEGER PRIMARY KEY,
    test_id INTEGER NOT NULL,
    slot_date TEXT NOT NULL,
    slot_time TEXT NOT NULL,
    is_available INTEGER DEFAULT 1
        CHECK(is_available IN (0, 1)),
    FOREIGN KEY (test_id) REFERENCES tests(test_id),
    UNIQUE(test_id, slot_date, slot_time)
);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,
    test_id INTEGER NOT NULL,
    slot_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'confirmed'
        CHECK(status IN ('confirmed', 'cancelled')),
    FOREIGN KEY (test_id) REFERENCES tests(test_id),
    FOREIGN KEY (slot_id) REFERENCES slots(slot_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS unique_active_slot
ON bookings(slot_id)
WHERE status = 'confirmed';
""")

conn.commit()
print("All three tables created successfully!")



from datetime import date, timedelta

# Adding 8 tests across 3 categories
tests_data = [
    (1, "Complete Blood Count", "Blood", 350),
    (2, "Blood Sugar", "Blood", 150),
    (3, "Lipid Profile", "Blood", 600),
    (4, "Thyroid Profile", "Hormonal", 550),
    (5, "Vitamin D", "Hormonal", 900),
    (6, "HbA1c", "Diabetes", 500),
    (7, "Fasting Glucose", "Diabetes", 200),
    (8, "Insulin Test", "Hormonal", 750)
]

cursor.executemany(
    "INSERT OR IGNORE INTO tests VALUES (?, ?, ?, ?)",
    tests_data
)

# Creating 3 slots for each test
start_date = date.today() + timedelta(days=7)
slots_data = []

for test_id in range(1, 9):
    for day in range(3):
        slot_id = test_id * 10 + day + 1
        slot_date = str(start_date + timedelta(days=day))
        slot_time = ["09:00", "10:00", "11:00"][day]

        # Test 8 has no free slots
        available = 0 if test_id == 8 else 1

        slots_data.append(
            (slot_id, test_id, slot_date, slot_time, available)
        )

cursor.executemany(
    "INSERT OR IGNORE INTO slots VALUES (?, ?, ?, ?, ?)",
    slots_data
)

conn.commit()




from langchain.tools import tool, ToolRuntime

@tool
def list_tests() -> str:
    """List all available lab tests with their categories and prices."""
    rows = conn.execute(
        "SELECT test_id, test_name, category, price FROM tests ORDER BY test_id"
    ).fetchall()

    return str([
        {
            "test_id": row[0],
            "test_name": row[1],
            "category": row[2],
            "price": row[3]
        }
        for row in rows
    ])


@tool
def check_slots(test_id: int) -> str:
    """Check available appointment slots for a given test ID."""
    rows = conn.execute(
        """
        SELECT slot_id, slot_date, slot_time
        FROM slots
        WHERE test_id = ? AND is_available = 1
        ORDER BY slot_date, slot_time
        """,
        (test_id,)
    ).fetchall()

    return str([
        {
            "slot_id": row[0],
            "date": row[1],
            "time": row[2]
        }
        for row in rows
    ])


from dataclasses import dataclass

@dataclass
class UserContext:
    user_id: str

@tool
def my_bookings(runtime: ToolRuntime[UserContext]) -> str:
    """Show bookings belonging to the current user."""
    user_id = runtime.context.user_id

    rows = conn.execute(
        """
        SELECT b.booking_id, t.test_name,
               s.slot_date, s.slot_time, b.status
        FROM bookings b
        JOIN tests t ON b.test_id = t.test_id
        JOIN slots s ON b.slot_id = s.slot_id
        WHERE b.user_id = ?
        ORDER BY s.slot_date, s.slot_time
        """,
        (user_id,)
    ).fetchall()

    return str(rows)


@tool
def book_test(test_id: int, slot_id: int,
              runtime: ToolRuntime[UserContext]) -> str:
    """Book a lab test in an available slot for the current user."""
    user_id = runtime.context.user_id

    test = conn.execute(
        "SELECT test_name, price FROM tests WHERE test_id = ?",
        (test_id,)
    ).fetchone()

    if not test:
        return "Test does not exist."

    duplicate = conn.execute(
        """SELECT booking_id FROM bookings
           WHERE user_id = ? AND test_id = ?
           AND status = 'confirmed'""",
        (user_id, test_id)
    ).fetchone()

    if duplicate:
        return "You already have an active booking for this test."

    with conn:
        updated = conn.execute(
            """UPDATE slots SET is_available = 0
               WHERE slot_id = ? AND test_id = ?
               AND is_available = 1""",
            (slot_id, test_id)
        )

        if updated.rowcount == 0:
            return "Slot is unavailable or does not belong to this test."

        booking = conn.execute(
            """INSERT INTO bookings (user_id, test_id, slot_id)
               VALUES (?, ?, ?)""",
            (user_id, test_id, slot_id)
        )

        receipt = conn.execute(
            """SELECT b.booking_id, t.test_name, t.price,
                      s.slot_date, s.slot_time
               FROM bookings b
               JOIN tests t ON b.test_id = t.test_id
               JOIN slots s ON b.slot_id = s.slot_id
               WHERE b.booking_id = ?""",
            (booking.lastrowid,)
        ).fetchone()

    return f"Booking confirmed. Receipt: {receipt}"


@tool
def cancel_booking(
    booking_id: int,
    runtime: ToolRuntime[UserContext]
) -> str:
    """Cancel an active booking belonging to the current user."""
    user_id = runtime.context.user_id

    with conn:
        booking = conn.execute(
            """SELECT slot_id FROM bookings
               WHERE booking_id = ? AND user_id = ?
               AND status = 'confirmed'""",
            (booking_id, user_id)
        ).fetchone()

        if booking is None:
            return "Booking not found or cancellation not allowed."

        conn.execute(
            """UPDATE bookings SET status = 'cancelled'
               WHERE booking_id = ? AND user_id = ?""",
            (booking_id, user_id)
        )

        conn.execute(
            """UPDATE slots SET is_available = 1
               WHERE slot_id = ?""",
            (booking[0],)
        )

    return f"Booking {booking_id} cancelled successfully."


from ddgs import DDGS

@tool
def web_search(query: str) -> str:
    """Search general information about lab tests, fasting, and what tests measure. Never search for prices or appointment slots."""
    blocked = ["price", "cost", "fee", "slot", "booking", "appointment"]

    if any(word in query.lower() for word in blocked):
        return "Use the SQLite database tools for prices and appointments."

    try:
        results = DDGS().text(query, max_results=3)

        return str([
            {
                "title": r.get("title"),
                "summary": r.get("body"),
                "url": r.get("href")
            }
            for r in results
        ])
    except Exception as e:
        return f"Web search unavailable: {type(e).__name__}"


import re
from langchain.agents.middleware import before_model
from langchain.agents.middleware import AgentState
from langgraph.runtime import Runtime
from langchain_core.messages import HumanMessage

@before_model
def redact_email(state: AgentState, runtime: Runtime):
    """Replace email addresses before the model processes messages."""
    messages = []

    for message in state["messages"]:
        if isinstance(message, HumanMessage):
            clean_text = re.sub(
                r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',
                '[EMAIL_REDACTED]',
                message.content
            )
            message = HumanMessage(content=clean_text, id=message.id)

        messages.append(message)

    return {"messages": messages}


system_prompt = """
You are a helpful lab test booking assistant for a fictional diagnostic lab.

Follow these rules:
1. Use database tools for lab tests, prices, slots and bookings.
2. Never guess test prices or appointment availability.
3. Ask for approval before booking or cancelling a test.
4. Only access bookings belonging to the current user.
5. Use web search only for general lab test information.
6. Never diagnose diseases or recommend tests based on symptoms.
7. For medical symptoms, suggest consulting a qualified healthcare professional.
8. Keep responses clear, short and helpful.
"""


def create_booking_agent(api_key):
    if not api_key:
        raise ValueError("GROQ_API_KEY is required")
    llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0, api_key=api_key)
    approval = HumanInTheLoopMiddleware(
        interrupt_on={
            "book_test": {"allowed_decisions": ["approve", "reject"]},
            "cancel_booking": {"allowed_decisions": ["approve", "reject"]},
        }
    )
    agent = create_agent(
        model=llm,
        tools=[list_tests, check_slots, my_bookings, book_test, cancel_booking, web_search],
        system_prompt=system_prompt,
        context_schema=UserContext,
        middleware=[redact_email, approval],
        checkpointer=InMemorySaver(),
    )
    return agent
