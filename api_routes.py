"""REST API routes for the RAG application frontend.

These endpoints are used by the React frontend to:
- Manage projects
- Manage chats (standalone and project chats)
- Upload/list scoped documents
- Send queries (via Inngest events)
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Request, Depends
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
    AIModel,
    User,
    generate_id,
)
from auth_routes import get_current_user

# Router for API endpoints
router = APIRouter(prefix="/api", tags=["api"])

# MongoDB client
def get_db():
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise HTTPException(status_code=500, detail="MONGODB_URI not configured")
    client = MongoClient(uri)
    db_name = os.getenv("MONGODB_DATABASE", "docurag")  # Use env variable, default to docurag
    return client[db_name]


# --- Plan Limits ---
# Resource limits per plan
PLAN_LIMITS = {
    "free": {"projects": 1, "chats": 3, "documents": 3, "docs_per_scope": 1},
    "pro": {"projects": 5, "chats": None, "documents": 25, "docs_per_scope": 5},  # None = unlimited
    "premium": {"projects": None, "chats": None, "documents": None, "docs_per_scope": 10},
}


# --- Request Models ---

class CreateProjectRequest(BaseModel):
    name: str = "New Project"

class CreateChatRequest(BaseModel):
    project_id: Optional[str] = None  # None = standalone chat
    title: str = "New Chat"

class UpdateChatRequest(BaseModel):
    title: Optional[str] = None
    is_pinned: Optional[bool] = None
    model: Optional[str] = None  # AI model selection
    quality_preset: Optional[str] = None  # quick, standard, thorough, deep, max

class SaveMessageRequest(BaseModel):
    chat_id: str
    role: str
    content: str
    sources: list[str] = []


# --- Project Endpoints ---

@router.post("/projects")
async def create_project(request: CreateProjectRequest, user: User = Depends(get_current_user)):
    """Create a new project for the current user."""
    db = get_db()
    
    # Check project limit for user's plan
    plan = user.plan or "free"
    limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])["projects"]
    if limit is not None:
        current_count = db.projects.count_documents({"user_id": user.id})
        if current_count >= limit:
            raise HTTPException(
                status_code=403, 
                detail={"error": "limit_reached", "resource": "projects", "limit": limit}
            )
    
    project = Project(user_id=user.id, name=request.name)
    db.projects.insert_one(project.model_dump())
    return project.model_dump()

@router.get("/projects")
async def list_projects(user: User = Depends(get_current_user)):
    """List all projects for the current user."""
    db = get_db()
    projects = list(db.projects.find({"user_id": user.id}, {"_id": 0}))
    return projects

@router.get("/projects/{project_id}")
async def get_project(project_id: str, user: User = Depends(get_current_user)):
    """Get a specific project owned by the current user."""
    db = get_db()
    project = db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, user: User = Depends(get_current_user)):
    """Delete a project owned by the current user."""
    from vector_db import MongoDBStorage
    
    db = get_db()
    
    # Verify user owns the project
    project = db.projects.find_one({"id": project_id, "user_id": user.id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
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
async def create_chat(request: CreateChatRequest, user: User = Depends(get_current_user)):
    """Create a new chat for the current user."""
    db = get_db()
    
    # Check chat limit for user's plan
    plan = user.plan or "free"
    limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])["chats"]
    if limit is not None:
        current_count = db.chats.count_documents({"user_id": user.id})
        if current_count >= limit:
            raise HTTPException(
                status_code=403, 
                detail={"error": "limit_reached", "resource": "chats", "limit": limit}
            )
    
    # If project_id provided, verify user owns the project
    if request.project_id:
        project = db.projects.find_one({"id": request.project_id, "user_id": user.id})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
    
    chat = Chat(
        user_id=user.id,
        project_id=request.project_id,
        title=request.title
    )
    db.chats.insert_one(chat.model_dump())
    return chat.model_dump()

@router.get("/chats")
async def list_chats(user: User = Depends(get_current_user), project_id: Optional[str] = None, standalone: bool = False):
    """List chats for the current user. Filter by project_id or get standalone chats."""
    db = get_db()
    query = {"user_id": user.id}
    
    if standalone:
        query["project_id"] = None
    elif project_id:
        query["project_id"] = project_id
    
    chats = list(db.chats.find(query, {"_id": 0}))
    return chats

@router.get("/chats/{chat_id}")
async def get_chat(chat_id: str, user: User = Depends(get_current_user)):
    """Get a specific chat owned by the current user."""
    db = get_db()
    chat = db.chats.find_one({"id": chat_id, "user_id": user.id}, {"_id": 0})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@router.patch("/chats/{chat_id}")
async def update_chat(chat_id: str, request: UpdateChatRequest, user: User = Depends(get_current_user)):
    """Update chat title, pinned status, model, or quality preset."""
    db = get_db()
    
    # Verify user owns the chat
    chat = db.chats.find_one({"id": chat_id, "user_id": user.id})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    updates = {}
    if request.title is not None:
        updates["title"] = request.title
    if request.is_pinned is not None:
        updates["is_pinned"] = request.is_pinned
    if request.model is not None:
        # Validate model enum
        try:
            AIModel(request.model)
            updates["model"] = request.model
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid model: {request.model}")
    if request.quality_preset is not None:
        # Validate preset
        valid_presets = ["quick", "standard", "thorough", "deep", "max"]
        if request.quality_preset not in valid_presets:
            raise HTTPException(status_code=400, detail=f"Invalid preset: {request.quality_preset}")
        updates["quality_preset"] = request.quality_preset
    
    if updates:
        db.chats.update_one({"id": chat_id}, {"$set": updates})
    
    # Return updated chat
    updated_chat = db.chats.find_one({"id": chat_id}, {"_id": 0})
    return updated_chat

@router.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str, user: User = Depends(get_current_user)):
    """Delete a chat owned by the current user."""
    from vector_db import MongoDBStorage
    
    db = get_db()
    
    # Verify user owns the chat
    chat = db.chats.find_one({"id": chat_id, "user_id": user.id})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
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


# --- Upload Limits (easily configurable) ---
import file_storage

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB per individual file
MAX_PDFS_PER_SCOPE = 10  # Maximum number of PDFs per chat/project
MAX_TOTAL_SIZE_PER_SCOPE = 50 * 1024 * 1024  # 50 MB total per chat/project

# PDF magic bytes
PDF_MAGIC_BYTES = [b'%PDF', b'\x25\x50\x44\x46']


def validate_pdf_content(content: bytes) -> bool:
    """Validate that file content starts with PDF magic bytes."""
    if len(content) < 4:
        return False
    header = content[:4]
    return any(header.startswith(magic) for magic in PDF_MAGIC_BYTES)


@router.get("/upload-limits")
def get_upload_limits(scope_type: str, scope_id: str, user: User = Depends(get_current_user)):
    """Get upload limits and current usage for a scope.
    
    Returns max files, max total size, and current usage.
    """
    from models import ScopeType
    
    try:
        ScopeType(scope_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="scope_type must be 'chat' or 'project'")
    
    db = get_db()
    
    # Get plan-based document limit per scope
    plan = user.plan or "free"
    max_docs_per_scope = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])["docs_per_scope"]
    
    # Get current usage
    scope_docs = list(db.document_scopes.aggregate([
        {"$match": {"scope_type": scope_type, "scope_id": scope_id}},
        {"$lookup": {
            "from": "documents",
            "localField": "document_id",
            "foreignField": "id",
            "as": "doc"
        }},
        {"$unwind": "$doc"},
        {"$group": {
            "_id": None,
            "count": {"$sum": 1},
            "total_size": {"$sum": "$doc.size_bytes"}
        }}
    ]))
    
    current_count = scope_docs[0]["count"] if scope_docs else 0
    current_size = scope_docs[0]["total_size"] if scope_docs else 0
    
    return {
        "max_files": max_docs_per_scope,
        "max_file_size": MAX_FILE_SIZE,
        "max_total_size": MAX_TOTAL_SIZE_PER_SCOPE,
        "current_count": current_count,
        "current_size": current_size,
        "remaining_count": max_docs_per_scope - current_count,
        "remaining_size": MAX_TOTAL_SIZE_PER_SCOPE - current_size
    }


@router.post("/upload")
async def upload_document(
    request: Request,
    scope_type: str,
    scope_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user)
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
    
    # Validate scope exists and user owns it
    db = get_db()
    if scope_type == "chat":
        chat = db.chats.find_one({"id": scope_id, "user_id": user.id})
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
    elif scope_type == "project":
        project = db.projects.find_one({"id": scope_id, "user_id": user.id})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
    
    # Get plan-based document limit per scope
    plan = user.plan or "free"
    max_docs_per_scope = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])["docs_per_scope"]
    
    # Check scope limits (count and total size)
    scope_docs = list(db.document_scopes.aggregate([
        {"$match": {"scope_type": scope_type, "scope_id": scope_id}},
        {"$lookup": {
            "from": "documents",
            "localField": "document_id",
            "foreignField": "id",
            "as": "doc"
        }},
        {"$unwind": "$doc"},
        {"$group": {
            "_id": None,
            "count": {"$sum": 1},
            "total_size": {"$sum": "$doc.size_bytes"}
        }}
    ]))
    
    current_count = scope_docs[0]["count"] if scope_docs else 0
    current_size = scope_docs[0]["total_size"] if scope_docs else 0
    
    if current_count >= max_docs_per_scope:
        raise HTTPException(
            status_code=403, 
            detail={"error": "limit_reached", "resource": "documents", "limit": max_docs_per_scope}
        )
    
    # Check file extension
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB per file")
    
    # Check total size limit for scope
    if current_size + len(content) > MAX_TOTAL_SIZE_PER_SCOPE:
        remaining = (MAX_TOTAL_SIZE_PER_SCOPE - current_size) // (1024 * 1024)
        raise HTTPException(
            status_code=400, 
            detail=f"Total size limit exceeded. Only {remaining}MB remaining for this {scope_type}"
        )
    
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
        from models import DocumentScope, Document
        
        # Serialize existing doc to handle ObjectId/datetime
        existing_doc_model = Document(**existing_doc)
        
        scope_link = DocumentScope(
            document_id=existing_doc_model.id,
            scope_type=scope,
            scope_id=scope_id
        )
        db.document_scopes.insert_one(scope_link.model_dump())
        
        return {
            "document": existing_doc_model.model_dump(),
            "status": "linked",
            "message": "Document already exists, linked to scope"
        }
    
    # Upload to S3 with scope prefix
    prefix = f"{scope_type}s/{scope_id}/"
    result = file_storage.upload_file(content, safe_filename, prefix)
    
    # Create document record (M1 model)
    from models import Document, DocumentScope, DocumentStatus
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
    document_id: str  # M1: Required for chunk linking


class QueryEventRequest(BaseModel):
    question: str
    chat_id: str
    scope_type: str
    scope_id: str
    model: str = "deepseek"  # AI model to use
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
            "document_id": request.document_id,  # M1: Include for chunk linking
        }
    )
    
    ids = await client.send(event)
    return {"event_ids": ids}


@router.post("/events/query")
async def send_query_event(request: QueryEventRequest, user: User = Depends(get_current_user)):
    """Send a query event to Inngest."""
    # Check token limit
    tokens_used = getattr(user, 'tokens_used', 0) or 0
    token_limit = getattr(user, 'token_limit', 5000) or 5000
    if tokens_used >= token_limit:
        raise HTTPException(
            status_code=403,
            detail={"error": "limit_reached", "resource": "tokens", "limit": token_limit, "used": tokens_used}
        )
    
    # Validate model enum
    try:
        AIModel(request.model)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid model: {request.model}")
    
    client = get_inngest_client()
    
    event = inngest.Event(
        name="rag/query_pdf_ai",
        data={
            "question": request.question,
            "chat_id": request.chat_id,
            "scope_type": request.scope_type,
            "scope_id": request.scope_id,
            "model": request.model,
            "top_k": request.top_k,
            "history": request.history,
            "user_id": user.id,  # For token tracking
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
