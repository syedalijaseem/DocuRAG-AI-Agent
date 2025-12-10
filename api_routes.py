"""REST API routes for the RAG application frontend.

These endpoints are used by the React frontend to:
- Manage projects
- Manage chats (standalone and project chats)
- Upload/list scoped documents
- Send queries (via Inngest events)
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import inngest

load_dotenv()

from models import (
    Project,
    Chat,
    Document,
    Message,
    MessageRole,
    ScopeType,
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


# --- Request Models ---

class CreateProjectRequest(BaseModel):
    name: str = "New Project"

class CreateChatRequest(BaseModel):
    project_id: Optional[str] = None  # None = standalone chat
    title: str = "New Chat"

class UpdateChatRequest(BaseModel):
    title: Optional[str] = None
    is_pinned: Optional[bool] = None

class SaveMessageRequest(BaseModel):
    chat_id: str
    role: str
    content: str
    sources: list[str] = []


# --- Project Endpoints ---

@router.post("/projects")
def create_project(request: CreateProjectRequest):
    """Create a new project."""
    db = get_db()
    project = Project(name=request.name)
    db.projects.insert_one(project.model_dump())
    return project.model_dump()

@router.get("/projects")
def list_projects():
    """List all projects."""
    db = get_db()
    projects = list(db.projects.find({}, {"_id": 0}))
    return projects

@router.get("/projects/{project_id}")
def get_project(project_id: str):
    """Get a specific project."""
    db = get_db()
    project = db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.delete("/projects/{project_id}")
def delete_project(project_id: str):
    """Delete a project and all its chats/documents from DB, S3, and vector store."""
    from vector_db import MongoDBStorage
    
    db = get_db()
    vector_store = MongoDBStorage()
    
    # Get project documents for S3 cleanup
    project_docs = list(db.documents.find({"scope_type": "project", "scope_id": project_id}))
    
    # Delete from S3
    for doc in project_docs:
        if doc.get("s3_key"):
            try:
                file_storage.delete_file(doc["s3_key"])
            except Exception as e:
                print(f"Warning: Failed to delete S3 file {doc.get('s3_key')}: {e}")
    
    # Delete from vector store
    vector_store.delete_by_scope("project", project_id)
    
    # Delete project documents from DB
    db.documents.delete_many({"scope_type": "project", "scope_id": project_id})
    
    # Delete project chats and their content
    chats = list(db.chats.find({"project_id": project_id}))
    for chat in chats:
        # Get chat documents for S3 cleanup
        chat_docs = list(db.documents.find({"scope_type": "chat", "scope_id": chat["id"]}))
        for doc in chat_docs:
            if doc.get("s3_key"):
                try:
                    file_storage.delete_file(doc["s3_key"])
                except Exception as e:
                    print(f"Warning: Failed to delete S3 file {doc.get('s3_key')}: {e}")
        
        # Delete from vector store
        vector_store.delete_by_scope("chat", chat["id"])
        
        # Delete chat documents and messages from DB
        db.documents.delete_many({"scope_type": "chat", "scope_id": chat["id"]})
        db.messages.delete_many({"chat_id": chat["id"]})
    
    db.chats.delete_many({"project_id": project_id})
    db.projects.delete_one({"id": project_id})
    return {"status": "deleted"}


# --- Chat Endpoints ---

@router.post("/chats")
def create_chat(request: CreateChatRequest):
    """Create a new chat (standalone or within a project)."""
    db = get_db()
    chat = Chat(
        project_id=request.project_id,
        title=request.title
    )
    db.chats.insert_one(chat.model_dump())
    return chat.model_dump()

@router.get("/chats")
def list_chats(project_id: Optional[str] = None, standalone: bool = False):
    """List chats. Filter by project_id or get standalone chats."""
    db = get_db()
    if standalone:
        chats = list(db.chats.find({"project_id": None}, {"_id": 0}))
    elif project_id:
        chats = list(db.chats.find({"project_id": project_id}, {"_id": 0}))
    else:
        chats = list(db.chats.find({}, {"_id": 0}))
    return chats

@router.get("/chats/{chat_id}")
def get_chat(chat_id: str):
    """Get a specific chat."""
    db = get_db()
    chat = db.chats.find_one({"id": chat_id}, {"_id": 0})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@router.patch("/chats/{chat_id}")
def update_chat(chat_id: str, request: UpdateChatRequest):
    """Update chat title or pinned status."""
    db = get_db()
    updates = {}
    if request.title is not None:
        updates["title"] = request.title
    if request.is_pinned is not None:
        updates["is_pinned"] = request.is_pinned
    
    if updates:
        db.chats.update_one({"id": chat_id}, {"$set": updates})
    
    return get_chat(chat_id)

@router.delete("/chats/{chat_id}")
def delete_chat(chat_id: str):
    """Delete a chat and its messages/documents from DB, S3, and vector store."""
    from vector_db import MongoDBStorage
    
    db = get_db()
    vector_store = MongoDBStorage()
    
    # Get chat documents for S3 cleanup
    chat_docs = list(db.documents.find({"scope_type": "chat", "scope_id": chat_id}))
    
    # Delete from S3
    for doc in chat_docs:
        if doc.get("s3_key"):
            try:
                file_storage.delete_file(doc["s3_key"])
            except Exception as e:
                print(f"Warning: Failed to delete S3 file {doc.get('s3_key')}: {e}")
    
    # Delete from vector store
    vector_store.delete_by_scope("chat", chat_id)
    
    # Delete from DB
    db.messages.delete_many({"chat_id": chat_id})
    db.documents.delete_many({"scope_type": "chat", "scope_id": chat_id})
    db.chats.delete_one({"id": chat_id})
    return {"status": "deleted"}


# --- Message Endpoints ---

@router.get("/chats/{chat_id}/messages")
def get_messages(chat_id: str):
    """Get messages for a chat."""
    db = get_db()
    messages = list(db.messages.find({"chat_id": chat_id}, {"_id": 0}).sort("timestamp", 1))
    return messages

@router.post("/messages")
def save_message(request: SaveMessageRequest):
    """Save a message to a chat."""
    db = get_db()
    
    # Validate role
    try:
        role = MessageRole(request.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {request.role}")
    
    message = Message(
        chat_id=request.chat_id,
        role=role,
        content=request.content,
        sources=request.sources
    )
    db.messages.insert_one(message.model_dump())
    
    # Auto-update chat title on first user message
    chat = db.chats.find_one({"id": request.chat_id})
    if chat and chat.get("title") == "New Chat" and role == MessageRole.USER:
        new_title = request.content[:50] + ("..." if len(request.content) > 50 else "")
        db.chats.update_one({"id": request.chat_id}, {"$set": {"title": new_title}})
    
    return message.model_dump()


# --- Document Endpoints ---

@router.get("/documents")
def list_documents(scope_type: str, scope_id: str):
    """List documents for a scope (chat or project) via DocumentScope."""
    db = get_db()
    
    # Get document_ids linked to this scope (M1 architecture)
    scope_links = list(db.document_scopes.find(
        {"scope_type": scope_type, "scope_id": scope_id},
        {"document_id": 1}
    ))
    doc_ids = [s["document_id"] for s in scope_links]
    
    if not doc_ids:
        return []
    
    # Get document details
    docs = list(db.documents.find(
        {"id": {"$in": doc_ids}},
        {"_id": 0}
    ))
    return docs

@router.get("/chats/{chat_id}/documents")
def get_chat_documents(chat_id: str, include_project: bool = True):
    """Get documents for a chat, optionally including project docs."""
    db = get_db()
    
    # Get chat document_ids via DocumentScope
    chat_links = list(db.document_scopes.find(
        {"scope_type": "chat", "scope_id": chat_id},
        {"document_id": 1}
    ))
    doc_ids = [s["document_id"] for s in chat_links]
    
    # If chat belongs to a project, include project docs
    if include_project:
        chat = db.chats.find_one({"id": chat_id})
        if chat and chat.get("project_id"):
            project_links = list(db.document_scopes.find(
                {"scope_type": "project", "scope_id": chat["project_id"]},
                {"document_id": 1}
            ))
            doc_ids.extend([s["document_id"] for s in project_links])
    
    if not doc_ids:
        return []
    
    # Get unique document details
    docs = list(db.documents.find(
        {"id": {"$in": list(set(doc_ids))}},
        {"_id": 0}
    ))
    return docs


# --- File Upload Endpoint ---

import file_storage

# PDF magic bytes
PDF_MAGIC_BYTES = [b'%PDF', b'\x25\x50\x44\x46']
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def validate_pdf_content(content: bytes) -> bool:
    """Validate that file content starts with PDF magic bytes."""
    if len(content) < 4:
        return False
    header = content[:4]
    return any(header.startswith(magic) for magic in PDF_MAGIC_BYTES)


@router.post("/upload")
async def upload_document(
    request: Request,
    scope_type: str,
    scope_id: str,
    file: UploadFile = File(...)
):
    """Upload a PDF document to a scope (chat or project).
    
    scope_type: 'chat' or 'project'
    scope_id: The ID of the chat or project
    """
    # Validate scope_type
    try:
        scope = ScopeType(scope_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="scope_type must be 'chat' or 'project'")
    
    # Validate scope exists (security: prevent orphaned documents)
    db = get_db()
    if scope_type == "chat":
        if not db.chats.find_one({"id": scope_id}):
            raise HTTPException(status_code=404, detail="Chat not found")
    elif scope_type == "project":
        if not db.projects.find_one({"id": scope_id}):
            raise HTTPException(status_code=404, detail="Project not found")
    
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
    import hashlib
    safe_filename = re.sub(r'[^\w\s\-\.]', '', file.filename)
    if not safe_filename or safe_filename != file.filename:
        safe_filename = re.sub(r'[^\w\-\.]', '_', file.filename)
    
    # Calculate checksum for deduplication
    checksum = "sha256:" + hashlib.sha256(content).hexdigest()
    
    # Check for existing document with same checksum (M1 deduplication)
    db = get_db()
    existing_doc = db.documents.find_one({"checksum": checksum})
    
    if existing_doc:
        # Document exists, just add scope link
        from models import DocumentScope
        scope_link = DocumentScope(
            document_id=existing_doc["id"],
            scope_type=scope,
            scope_id=scope_id
        )
        db.document_scopes.insert_one(scope_link.model_dump())
        
        return {
            "document": existing_doc,
            "status": "linked",
            "message": "Document already exists, linked to scope"
        }
    
    # Upload to S3 with scope prefix
    prefix = f"{scope_type}s/{scope_id}/"
    result = file_storage.upload_file(content, safe_filename, prefix)
    
    # Create document record (M1 model)
    from models import DocumentScope, DocumentStatus
    doc = Document(
        filename=safe_filename,
        s3_key=result["s3_key"],
        checksum=checksum,
        size_bytes=len(content),
        status=DocumentStatus.PENDING
    )
    db.documents.insert_one(doc.model_dump())
    
    # Create scope link (M1 DocumentScope)
    scope_link = DocumentScope(
        document_id=doc.id,
        scope_type=scope,
        scope_id=scope_id
    )
    db.document_scopes.insert_one(scope_link.model_dump())
    
    return {
        "document": doc.model_dump(),
        "s3_url": result["url"],
        "status": "uploaded"
    }


# --- Inngest Event Endpoints ---

def get_inngest_client():
    return inngest.Inngest(app_id="rag-app", is_production=False)


class IngestEventRequest(BaseModel):
    pdf_path: str
    filename: str
    scope_type: str
    scope_id: str


class QueryEventRequest(BaseModel):
    question: str
    chat_id: str
    scope_type: str
    scope_id: str
    top_k: int = 5
    history: list[dict] = []


@router.post("/events/ingest")
async def send_ingest_event(request: IngestEventRequest):
    """Send an ingestion event to Inngest."""
    client = get_inngest_client()
    
    event = inngest.Event(
        name="rag/ingest_pdf",
        data={
            "pdf_path": request.pdf_path,
            "filename": request.filename,
            "scope_type": request.scope_type,
            "scope_id": request.scope_id,
        }
    )
    
    ids = await client.send(event)
    return {"event_ids": ids}


@router.post("/events/query")
async def send_query_event(request: QueryEventRequest):
    """Send a query event to Inngest."""
    client = get_inngest_client()
    
    event = inngest.Event(
        name="rag/query_pdf_ai",
        data={
            "question": request.question,
            "chat_id": request.chat_id,
            "scope_type": request.scope_type,
            "scope_id": request.scope_id,
            "top_k": request.top_k,
            "history": request.history,
        }
    )
    
    ids = await client.send(event)
    return {"event_ids": ids}


# --- Legacy Endpoints (for backward compatibility during migration) ---

# Keep workspace endpoints for existing data
@router.get("/workspaces")
def list_workspaces():
    """DEPRECATED: List workspaces. Use /projects instead."""
    db = get_db()
    workspaces = list(db.workspaces.find({}, {"_id": 0}))
    return workspaces

@router.get("/workspaces/{workspace_id}")
def get_workspace(workspace_id: str):
    """DEPRECATED: Get workspace. Use /projects/{id} instead."""
    db = get_db()
    workspace = db.workspaces.find_one({"id": workspace_id}, {"_id": 0})
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace

@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    """DEPRECATED: Get session. Use /chats/{id} instead."""
    db = get_db()
    session = db.chat_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """DEPRECATED: Delete session. Use /chats/{id} instead."""
    db = get_db()
    db.chat_sessions.delete_one({"id": session_id})
    db.messages.delete_many({"session_id": session_id})
    return {"status": "deleted"}
