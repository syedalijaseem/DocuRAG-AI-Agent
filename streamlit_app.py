import asyncio
import nest_asyncio
nest_asyncio.apply()

import time
import streamlit as st
import inngest
from dotenv import load_dotenv
import os
import requests
from pathlib import Path
import uuid

load_dotenv()
st.set_page_config(page_title="RAG Chatbot", page_icon="💬", layout="wide")

# --- Workspace ID Generation ---
def generate_workspace_id() -> str:
    """Generate a unique workspace ID for this session."""
    return f"ws_{uuid.uuid4().hex[:12]}"

# --- Inngest helpers ---
@st.cache_resource
def get_inngest_client() -> inngest.Inngest:
    return inngest.Inngest(app_id="rag-app", is_production=False)

async def send_rag_ingest_event(pdf_path: Path, workspace_id: str) -> str:
    client = get_inngest_client()
    result = await client.send(
        inngest.Event(
            name="rag/ingest_pdf",
            data={
                "pdf_path": str(pdf_path.resolve()), 
                "source_id": pdf_path.name,
                "workspace_id": workspace_id
            },
        )
    )
    return result[0]

async def send_rag_query_event(question: str, top_k: int, history: list, workspace_id: str) -> str:
    client = get_inngest_client()
    result = await client.send(
        inngest.Event(
            name="rag/query_pdf_ai",
            data={
                "question": question,
                "top_k": top_k,
                "history": history,
                "workspace_id": workspace_id
            },
        )
    )
    return result[0]

def _inngest_api_base() -> str:
    return os.getenv("INNGEST_API_BASE", "http://127.0.0.1:8288/v1")

def fetch_runs(event_id: str) -> list[dict]:
    url = f"{_inngest_api_base()}/events/{event_id}/runs"
    resp = requests.get(url)
    if resp.status_code == 200:
        data = resp.json()
        return data.get("data", [])
    return []

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

# --- Session State Initialization ---
if "workspace_id" not in st.session_state:
    st.session_state["workspace_id"] = generate_workspace_id()
if "uploaded_docs" not in st.session_state:
    st.session_state["uploaded_docs"] = []  # List of uploaded document names
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "history" not in st.session_state:
    st.session_state["history"] = []
if "session_id" not in st.session_state:
    st.session_state["session_id"] = f"sess_{uuid.uuid4().hex[:8]}"
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0  # Increment to reset file_uploader

# --- Sidebar: Workspace & Documents ---
with st.sidebar:
    st.header("📁 Workspace")
    
    st.divider()
    
    # Document upload
    st.subheader("📄 Documents")
    uploaded_files = st.file_uploader(
        "Upload PDFs", 
        type=["pdf"], 
        accept_multiple_files=True,
        key=f"file_uploader_{st.session_state['uploader_key']}"  # Dynamic key to allow reset
    )
    
    # Process new uploads
    if uploaded_files:
        for uploaded_file in uploaded_files:
            if uploaded_file.name not in st.session_state["uploaded_docs"]:
                with st.spinner(f"Ingesting {uploaded_file.name}..."):
                    path = save_uploaded_pdf(uploaded_file)
                    event_id = asyncio.run(send_rag_ingest_event(path, st.session_state["workspace_id"]))
                    try:
                        wait_for_run_output(event_id, timeout_s=300.0)
                        st.session_state["uploaded_docs"].append(uploaded_file.name)
                        st.success(f"✅ {uploaded_file.name}")
                    except (TimeoutError, RuntimeError) as e:
                        st.error(f"❌ {uploaded_file.name}: {e}")
    
    # Show uploaded documents
    if st.session_state["uploaded_docs"]:
        st.write("**Uploaded:**")
        for doc in st.session_state["uploaded_docs"]:
            st.write(f"• {doc}")
    else:
        st.info("No documents uploaded yet")
    
    st.divider()
    
    # Chat controls
    st.subheader("💬 Chat")
    if st.button("🆕 New Chat", use_container_width=True):
        st.session_state["messages"] = []
        st.session_state["history"] = []
        st.session_state["session_id"] = f"sess_{uuid.uuid4().hex[:8]}"
        st.rerun()
    
    if st.button("🗑️ Clear Workspace", use_container_width=True):
        st.session_state["workspace_id"] = generate_workspace_id()
        st.session_state["uploaded_docs"] = []
        st.session_state["messages"] = []
        st.session_state["history"] = []
        st.session_state["session_id"] = f"sess_{uuid.uuid4().hex[:8]}"
        st.session_state["uploader_key"] += 1  # Reset file uploader
        st.rerun()
    
    st.divider()
    top_k = st.slider("🔍 Chunks to retrieve", min_value=1, max_value=20, value=5)

# --- Main Chat Area ---
st.title("📚 RAG Chatbot")

if not st.session_state["uploaded_docs"]:
    st.info("👈 Upload PDFs in the sidebar to get started!")
else:
    # Display chat history
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("📚 Sources"):
                    for src in msg["sources"]:
                        st.write(f"• {src}")

    # Chat input
    if question := st.chat_input("Ask a question about your documents..."):
        st.session_state["messages"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.spinner("🤔 Thinking..."):
            event_id = asyncio.run(send_rag_query_event(
                question, 
                top_k, 
                st.session_state["history"],
                st.session_state["workspace_id"]
            ))
            output = wait_for_run_output(event_id)

            answer = output.get("answer", "(No answer)")
            sources = output.get("sources", [])
            st.session_state["history"] = output.get("history", [])

        st.session_state["messages"].append({
            "role": "assistant", 
            "content": answer,
            "sources": sources
        })
        with st.chat_message("assistant"):
            st.markdown(answer)
            if sources:
                with st.expander("📚 Sources"):
                    for src in sources:
                        st.write(f"• {src}")