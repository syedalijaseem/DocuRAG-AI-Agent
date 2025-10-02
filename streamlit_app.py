import asyncio
import time
import streamlit as st
import inngest
from dotenv import load_dotenv
import os
import requests
from pathlib import Path

load_dotenv()
st.set_page_config(page_title="RAG Chatbot", page_icon="💬", layout="centered")

# --- Inngest helpers ---
@st.cache_resource
def get_inngest_client() -> inngest.Inngest:
    return inngest.Inngest(app_id="rag_app", is_production=False)

async def send_rag_ingest_event(pdf_path: Path) -> str:
    client = get_inngest_client()
    result = await client.send(
        inngest.Event(
            name="rag/ingest_pdf",
            data={"pdf_path": str(pdf_path.resolve()), "source_id": pdf_path.name},
        )
    )
    return result[0]

async def send_rag_query_event(question: str, top_k: int, history: list) -> str:
    client = get_inngest_client()
    result = await client.send(
        inngest.Event(
            name="rag/query_pdf_ai",
            data={
                "question": question,
                "top_k": top_k,
                "history": history
            },
        )
    )
    return result[0]

def _inngest_api_base() -> str:
    return os.getenv("INNGEST_API_BASE", "http://127.0.0.1:8288/v1")

def fetch_runs(event_id: str) -> list[dict]:
    url = f"{_inngest_api_base()}/events/{event_id}/runs"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])

def wait_for_run_output(event_id: str, timeout_s: float = 120.0, poll_interval_s: float = 0.5) -> dict:
    start = time.time()
    last_status = None
    while True:
        runs = fetch_runs(event_id)
        if runs:
            run = runs[0]
            status = run.get("status")
            last_status = status or last_status
            if status in ("Completed", "Succeeded", "Success", "Finished"):
                return run.get("output") or {}
            if status in ("Failed", "Cancelled"):
                raise RuntimeError(f"Function run {status}")
        if time.time() - start > timeout_s:
            raise TimeoutError(f"Timed out waiting for run output (last status: {last_status})")
        time.sleep(poll_interval_s)

def save_uploaded_pdf(file) -> Path:
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / file.name
    file_path.write_bytes(file.getbuffer())
    return file_path

# --- State ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "pdf_ingested" not in st.session_state:
    st.session_state["pdf_ingested"] = False
if "history" not in st.session_state:
    st.session_state["history"] = []

# --- Upload Section ---
st.title("📚 RAG Chatbot over PDFs")

uploaded = st.file_uploader("Upload a PDF", type=["pdf"], accept_multiple_files=False)

if uploaded and not st.session_state["pdf_ingested"]:
    with st.spinner("📄 Uploading & chunking your PDF..."):
        path = save_uploaded_pdf(uploaded)
        event_id = asyncio.run(send_rag_ingest_event(path))
        
        try:
            wait_for_run_output(event_id, timeout_s=300.0)
            st.session_state["pdf_ingested"] = True
            st.success(f"✅ PDF '{path.name}' ingested successfully!")
        except (TimeoutError, RuntimeError) as e:
            st.error(f"❌ Ingestion failed: {e}")

st.divider()

# --- Chunk control ---
top_k = st.number_input("🔍 How many chunks to retrieve", min_value=1, max_value=20, value=5, step=1)

# --- Reset Chat Button ---
if st.button("🔄 Reset Chat"):
    st.session_state["messages"] = []
    st.session_state["history"] = []
    st.success("Chat history cleared.")

# --- Chat history ---
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Chat input ---
if st.session_state["pdf_ingested"]:
    if question := st.chat_input("Ask a question (follow-ups supported)..."):
        # Add user message to display
        st.session_state["messages"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        # Query backend with conversation history
        with st.spinner("🤔 Thinking..."):
            event_id = asyncio.run(send_rag_query_event(question, int(top_k), st.session_state["history"]))
            output = wait_for_run_output(event_id)

            answer = output.get("answer", "(No answer)")
            sources = output.get("sources", [])
            avg_conf = output.get("avg_confidence", 0.0)
            st.session_state["history"] = output.get("history", [])

        # Add assistant message to display
        st.session_state["messages"].append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)

        # Show confidence score
        # st.metric(label="Answer Confidence", value=avg_conf)

        # Show sources (with page numbers)
        if sources:
            st.caption("📌 Sources")
            for s in sources:
                st.write(f"- {s}")
else:
    st.warning("⚠️ Please upload and ingest a PDF before asking questions.")

# --- Transcript Download ---
if st.session_state["messages"]:
    transcript = "\n".join([f"{m['role'].title()}: {m['content']}" for m in st.session_state["messages"]])
    st.download_button("💾 Download Transcript", transcript, file_name="chat_transcript.txt")