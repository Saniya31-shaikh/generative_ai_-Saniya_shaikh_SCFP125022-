# Lab Test Booking Assistant — Streamlit UI

This UI reuses the database schema and LangChain tool definitions from the uploaded Colab notebook. It uses a local persistent SQLite file, the Groq model, session-based conversation memory, email redaction, and Approve/Reject controls for protected writes.

## Run locally

```bash
pip install -r requirements.txt
```

Set your environment variable `GROQ_API_KEY`, or create `.streamlit/secrets.toml` with:

```toml
GROQ_API_KEY = "your_api_key_here"
```

Then run:

```bash
streamlit run app.py
```

Open the local address shown by Streamlit (normally `http://localhost:8501`). Do not upload API keys or the SQLite database to a public repository. Selecting demo users is not authentication.

## Notes

- Model may ask for conversational confirmation before requesting middleware approval.
- Writes require approval through LangChain HumanInTheLoopMiddleware.
- No mock booking confirmation is shown: writes happen only through the existing tools.
- This is a classroom demo, not a production-ready clinical booking system. Concurrent booking requests would need a stronger database transaction strategy, and production identity needs authentication.
