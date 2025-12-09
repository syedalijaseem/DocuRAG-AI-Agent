"""REST API routes for the RAG application frontend.

These endpoints are used by the React frontend to:
- Manage workspaces
- Upload/list documents
- Manage chat sessions
- Send queries (via Inngest events)
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from pymongo import MongoClient
import os
import asyncio
import inngest

from models import (
    Workspace,
    Document,
    ChatSession,
    Message,
    MessageRole,
    generate_id,
)

# Router for API endpoints
router = APIRouter(prefix="/api", tags=["api"])

# MongoDB client
def get_db():
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise HTTPException(status_code=500, detail="MONGODB_URI not configured")
    client = MongoClient(uri)
    return client["rag_db"]


# --- Request/Response Models ---

class CreateWorkspaceRequest(BaseModel):
    name: str = "New Workspace"

class CreateSessionRequest(BaseModel):
    workspace_id: str
    title: str = "New Chat"

class SendMessageRequest(BaseModel):
    session_id: str
    workspace_id: str
    content: str
    top_k: int = 5

class SaveMessageRequest(BaseModel):
    session_id: str
    role: str
    content: str
    sources: list[str] = []


# --- Workspace Endpoints ---

@router.post("/workspaces")
def create_workspace(request: CreateWorkspaceRequest):
    """Create a new workspace."""
    db = get_db()
    workspace = Workspace(name=request.name)
    db.workspaces.insert_one(workspace.model_dump())
    return workspace.model_dump()

@router.get("/workspaces")
def list_workspaces():
    """List all workspaces."""
    db = get_db()
    workspaces = list(db.workspaces.find({}, {"_id": 0}))
    return workspaces

@router.get("/workspaces/{workspace_id}")
def get_workspace(workspace_id: str):
    """Get a specific workspace."""
    db = get_db()
    workspace = db.workspaces.find_one({"id": workspace_id}, {"_id": 0})
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


# --- Document Endpoints ---

@router.get("/workspaces/{workspace_id}/documents")
def list_documents(workspace_id: str):
    """List documents in a workspace."""
    db = get_db()
    # Get unique sources from the documents collection
    pipeline = [
        {"$match": {"workspace_id": workspace_id}},
        {"$group": {"_id": "$source", "count": {"$sum": 1}}},
    ]
    docs = list(db.documents.aggregate(pipeline))
    return [{"source": d["_id"], "chunks": d["count"]} for d in docs]


# --- Chat Session Endpoints ---

@router.post("/sessions")
def create_session(request: CreateSessionRequest):
    """Create a new chat session."""
    db = get_db()
    session = ChatSession(
        workspace_id=request.workspace_id,
        title=request.title
    )
    db.chat_sessions.insert_one(session.model_dump())
    return session.model_dump()

@router.get("/workspaces/{workspace_id}/sessions")
def list_sessions(workspace_id: str):
    """List chat sessions in a workspace."""
    db = get_db()
    sessions = list(db.chat_sessions.find(
        {"workspace_id": workspace_id},
        {"_id": 0}
    ).sort("created_at", -1))
    return sessions

@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    """Get a specific session with its messages."""
    db = get_db()
    session = db.chat_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = list(db.messages.find(
        {"session_id": session_id},
        {"_id": 0}
    ).sort("timestamp", 1))
    
    return {**session, "messages": messages}

@router.patch("/sessions/{session_id}")
def update_session(session_id: str, title: str):
    """Update session title."""
    db = get_db()
    result = db.chat_sessions.update_one(
        {"id": session_id},
        {"$set": {"title": title}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True}

@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """Delete a session and its messages."""
    db = get_db()
    db.chat_sessions.delete_one({"id": session_id})
    db.messages.delete_many({"session_id": session_id})
    return {"success": True}


# --- Message Endpoints ---

@router.post("/messages")
def save_message(request: SaveMessageRequest):
    """Save a message to a session."""
    db = get_db()
    message = Message(
        session_id=request.session_id,
        role=request.role,
        content=request.content,
        sources=request.sources
    )
    db.messages.insert_one(message.model_dump())
    
    # Update session title if it's the first user message
    if request.role == "user":
        session = db.chat_sessions.find_one({"id": request.session_id})
        if session and session.get("title") == "New Chat":
            # Use first 50 chars of message as title
            new_title = request.content[:50] + ("..." if len(request.content) > 50 else "")
            db.chat_sessions.update_one(
                {"id": request.session_id},
                {"$set": {"title": new_title}}
            )
    
    return message.model_dump()

@router.get("/sessions/{session_id}/messages")
def get_messages(session_id: str):
    """Get all messages in a session."""
    db = get_db()
    messages = list(db.messages.find(
        {"session_id": session_id},
        {"_id": 0}
    ).sort("timestamp", 1))
    return messages


# --- File Upload Endpoint ---

import file_storage
from fastapi import Request

# PDF magic bytes (common variants)
PDF_MAGIC_BYTES = [b'%PDF', b'\x25\x50\x44\x46']
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def validate_pdf_content(content: bytes) -> bool:
    """Validate that file content starts with PDF magic bytes."""
    if len(content) < 4:
        return False
    header = content[:4]
    return any(header.startswith(magic) for magic in PDF_MAGIC_BYTES)


@router.post("/workspaces/{workspace_id}/upload")
async def upload_document(
    request: Request,
    workspace_id: str,
    file: UploadFile = File(...)
):
    """Upload a PDF document to a workspace (stored in S3).
    
    Rate limited to 10 uploads per minute per IP.
    """
    # Check file extension
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB")
    
    # Validate PDF magic bytes
    if not validate_pdf_content(content):
        raise HTTPException(status_code=400, detail="Invalid PDF file content")
    
    # Sanitize filename
    import re
    safe_filename = re.sub(r'[^\w\s\-\.]', '', file.filename)
    if not safe_filename or safe_filename != file.filename:
        # Use a safe version
        safe_filename = re.sub(r'[^\w\-\.]', '_', file.filename)
    
    # Upload to S3 with workspace prefix
    prefix = f"workspaces/{workspace_id}/"
    result = file_storage.upload_file(content, safe_filename, prefix)
    
    return {
        "filename": safe_filename,
        "path": result["s3_key"],  # S3 key for ingestion
        "s3_url": result["url"],
        "workspace_id": workspace_id,
        "status": "uploaded"
    }


# --- Inngest Event Endpoints ---

# Inngest client for sending events
def get_inngest_client():
    return inngest.Inngest(app_id="rag-app", is_production=False)


class IngestEventRequest(BaseModel):
    pdf_path: str
    source_id: str
    workspace_id: str


class QueryEventRequest(BaseModel):
    question: str
    workspace_id: str
    top_k: int = 5
    history: list[dict] = []


@router.post("/events/ingest")
async def send_ingest_event(request: IngestEventRequest):
    """Send an ingest PDF event to Inngest."""
    client = get_inngest_client()
    result = await client.send(
        inngest.Event(
            name="rag/ingest_pdf",
            data={
                "pdf_path": request.pdf_path,
                "source_id": request.source_id,
                "workspace_id": request.workspace_id,
            }
        )
    )
    return {"event_ids": result}


@router.post("/events/query")
async def send_query_event(request: QueryEventRequest):
    """Send a query event to Inngest."""
    client = get_inngest_client()
    result = await client.send(
        inngest.Event(
            name="rag/query_pdf_ai",
            data={
                "question": request.question,
                "workspace_id": request.workspace_id,
                "top_k": request.top_k,
                "history": request.history,
            }
        )
    )
    return {"event_ids": result}

