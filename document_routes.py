"""Document management API routes.

Provides endpoints for:
- Upload documents to scopes (chat or project)
- Get documents by scope
- Delete documents (unlink or full delete)
"""
import os
import hashlib
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from dotenv import load_dotenv
load_dotenv()

from models import (
    Document, DocumentScope, DocumentStatus, ScopeType,
    Chat, Project
)
from auth_routes import get_current_user

router = APIRouter(prefix="/api", tags=["documents"])

# Constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {".pdf"}
PDF_MAGIC_BYTES = b"%PDF-"


# --- Database Setup ---

def get_db():
    """Get MongoDB database connection."""
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        raise RuntimeError("MONGODB_URI not configured")
    client = MongoClient(mongodb_uri)
    db_name = os.getenv("MONGODB_DATABASE", "docurag")
    return client[db_name]


# --- Helper Functions ---

def calculate_checksum(content: bytes) -> str:
    """Calculate SHA-256 checksum of file content."""
    hash_hex = hashlib.sha256(content).hexdigest()
    return f"sha256:{hash_hex}"


def validate_file_type(content: bytes, filename: str) -> None:
    """Validate file is a PDF by checking magic bytes and extension."""
    # Check extension
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Only PDF files are allowed."
        )
    
    # Check magic bytes
    if not content.startswith(PDF_MAGIC_BYTES):
        raise HTTPException(
            status_code=400,
            detail="File does not appear to be a valid PDF."
        )


def validate_scope_ownership(db, scope_type: ScopeType, scope_id: str, user_id: str) -> None:
    """Validate that the user owns the specified scope."""
    if scope_type == ScopeType.CHAT:
        chat = db.chats.find_one({"id": scope_id})
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        if chat.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this chat")
    elif scope_type == ScopeType.PROJECT:
        project = db.projects.find_one({"id": scope_id})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this project")


def get_s3_client():
    """Get S3 client for file storage."""
    import boto3
    return boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-2")
    )


def upload_to_s3(content: bytes, s3_key: str) -> None:
    """Upload file content to S3."""
    s3 = get_s3_client()
    bucket = os.getenv("AWS_S3_BUCKET")
    if not bucket:
        raise RuntimeError("AWS_S3_BUCKET not configured")
    
    s3.put_object(
        Bucket=bucket,
        Key=s3_key,
        Body=content,
        ContentType="application/pdf"
    )


def delete_from_s3(s3_key: str) -> None:
    """Delete file from S3."""
    s3 = get_s3_client()
    bucket = os.getenv("AWS_S3_BUCKET")
    if not bucket:
        return
    
    try:
        s3.delete_object(Bucket=bucket, Key=s3_key)
    except Exception:
        pass  # Ignore S3 delete errors


# --- API Endpoints ---

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    scope_type: ScopeType = Query(..., description="Scope type: chat or project"),
    scope_id: str = Query(..., description="ID of the chat or project"),
    user = Depends(get_current_user)
):
    """Upload a document to a scope.
    
    - Validates file type (PDF only)
    - Validates file size (< 50MB)
    - Calculates checksum for deduplication
    - Reuses existing document if checksum matches
    - Creates DocumentScope link
    - Queues ingestion job for new documents
    """
    db = get_db()
    
    # Validate scope ownership
    validate_scope_ownership(db, scope_type, scope_id, user.id)
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB."
        )
    
    # Validate file type
    validate_file_type(content, file.filename or "unknown.pdf")
    
    # Calculate checksum
    checksum = calculate_checksum(content)
    
    # Check for existing document with same checksum
    existing_doc = db.documents.find_one({"checksum": checksum})
    
    if existing_doc:
        # Reuse existing document
        del existing_doc["_id"]
        doc = Document(**existing_doc)
        is_new = False
    else:
        # Create new document
        s3_key = f"documents/{scope_type.value}/{scope_id}/{file.filename or 'document.pdf'}"
        
        # Upload to S3
        try:
            upload_to_s3(content, s3_key)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file: {str(e)}"
            )
        
        # Create document record
        doc = Document(
            filename=file.filename or "document.pdf",
            s3_key=s3_key,
            checksum=checksum,
            size_bytes=len(content),
            status=DocumentStatus.PENDING
        )
        
        try:
            db.documents.insert_one(doc.model_dump())
        except DuplicateKeyError:
            # Race condition: another request created the doc
            existing_doc = db.documents.find_one({"checksum": checksum})
            if existing_doc:
                del existing_doc["_id"]
                doc = Document(**existing_doc)
            else:
                raise HTTPException(status_code=500, detail="Failed to create document")
        
        is_new = True
    
    # Create scope link
    scope_link = DocumentScope(
        document_id=doc.id,
        scope_type=scope_type,
        scope_id=scope_id
    )
    
    try:
        db.document_scopes.insert_one(scope_link.model_dump())
    except DuplicateKeyError:
        # Link already exists, ignore
        pass
    
    # Queue ingestion job for new documents
    if is_new:
        # Import here to avoid circular dependency
        from inngest import inngest_client
        inngest_client.send_sync({
            "name": "rag/ingest_pdf",
            "data": {
                "pdf_path": doc.s3_key,
                "filename": doc.filename,
                "scope_type": scope_type.value,
                "scope_id": scope_id,
                "document_id": doc.id
            }
        })
    
    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "size_bytes": doc.size_bytes,
        "status": doc.status.value,
        "checksum": doc.checksum,
        "is_new": is_new
    }


@router.get("/chats/{chat_id}/documents")
async def get_chat_documents(
    chat_id: str,
    include_project: bool = Query(False, description="Include project-level documents"),
    user = Depends(get_current_user)
):
    """Get documents for a chat.
    
    Optionally includes project-level documents if the chat belongs to a project.
    """
    db = get_db()
    
    # Validate chat ownership
    chat = db.chats.find_one({"id": chat_id})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if chat.get("user_id") != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this chat")
    
    # Get chat documents
    chat_scope_docs = list(db.document_scopes.find({
        "scope_type": ScopeType.CHAT.value,
        "scope_id": chat_id
    }))
    
    chat_doc_ids = [ds["document_id"] for ds in chat_scope_docs]
    chat_documents = list(db.documents.find({
        "id": {"$in": chat_doc_ids},
        "status": {"$ne": DocumentStatus.DELETING.value}
    }))
    
    # Clean MongoDB _id
    for doc in chat_documents:
        doc.pop("_id", None)
    
    result = {"documents": chat_documents}
    
    # Include project documents if requested
    if include_project and chat.get("project_id"):
        project_scope_docs = list(db.document_scopes.find({
            "scope_type": ScopeType.PROJECT.value,
            "scope_id": chat["project_id"]
        }))
        
        project_doc_ids = [ds["document_id"] for ds in project_scope_docs]
        project_documents = list(db.documents.find({
            "id": {"$in": project_doc_ids},
            "status": {"$ne": DocumentStatus.DELETING.value}
        }))
        
        for doc in project_documents:
            doc.pop("_id", None)
        
        result["project_documents"] = project_documents
    
    return result


@router.get("/projects/{project_id}/documents")
async def get_project_documents(
    project_id: str,
    user = Depends(get_current_user)
):
    """Get documents for a project."""
    db = get_db()
    
    # Validate project ownership
    project = db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.get("user_id") != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this project")
    
    # Get project documents
    scope_docs = list(db.document_scopes.find({
        "scope_type": ScopeType.PROJECT.value,
        "scope_id": project_id
    }))
    
    doc_ids = [ds["document_id"] for ds in scope_docs]
    documents = list(db.documents.find({
        "id": {"$in": doc_ids},
        "status": {"$ne": DocumentStatus.DELETING.value}
    }))
    
    for doc in documents:
        doc.pop("_id", None)
    
    return {"documents": documents}


@router.get("/documents/{document_id}/status")
async def get_document_status(
    document_id: str,
    user = Depends(get_current_user)
):
    """Get the status of a document.
    
    Returns the document status (pending, ready, deleting) for tracking ingestion progress.
    """
    db = get_db()
    
    # Get document
    doc = db.documents.find_one({"id": document_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check user has access via any scope
    user_chats = [c["id"] for c in db.chats.find({"user_id": user.id}, {"id": 1})]
    user_projects = [p["id"] for p in db.projects.find({"user_id": user.id}, {"id": 1})]
    
    scope_link = db.document_scopes.find_one({
        "document_id": document_id,
        "$or": [
            {"scope_type": "chat", "scope_id": {"$in": user_chats}},
            {"scope_type": "project", "scope_id": {"$in": user_projects}}
        ]
    })
    
    if not scope_link:
        raise HTTPException(status_code=403, detail="Not authorized to access this document")
    
    return {
        "document_id": doc["id"],
        "filename": doc["filename"],
        "status": doc["status"],
        "size_bytes": doc["size_bytes"],
        "uploaded_at": doc.get("uploaded_at")
    }


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    scope_type: Optional[ScopeType] = Query(None, description="Scope type to unlink from"),
    scope_id: Optional[str] = Query(None, description="Scope ID to unlink from"),
    user = Depends(get_current_user)
):
    """Delete or unlink a document.
    
    If scope_type and scope_id are provided:
    - Unlinks document from that specific scope
    - If no links remain, marks document for deletion
    
    If no scope params:
    - Unlinks from ALL scopes owned by the user
    - If document becomes orphaned, marks for deletion
    """
    db = get_db()
    
    # Get document
    doc = db.documents.find_one({"id": document_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if scope_type and scope_id:
        # Unlink from specific scope
        validate_scope_ownership(db, scope_type, scope_id, user.id)
        
        # Remove the scope link
        result = db.document_scopes.delete_one({
            "document_id": document_id,
            "scope_type": scope_type.value,
            "scope_id": scope_id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Document not linked to this scope")
    else:
        # Unlink from all user's scopes
        # Get all user's chats and projects
        user_chats = [c["id"] for c in db.chats.find({"user_id": user.id})]
        user_projects = [p["id"] for p in db.projects.find({"user_id": user.id})]
        
        # Remove all links to user's scopes
        db.document_scopes.delete_many({
            "document_id": document_id,
            "$or": [
                {"scope_type": ScopeType.CHAT.value, "scope_id": {"$in": user_chats}},
                {"scope_type": ScopeType.PROJECT.value, "scope_id": {"$in": user_projects}}
            ]
        })
    
    # Check if document is now orphaned
    remaining_links = db.document_scopes.count_documents({"document_id": document_id})
    
    if remaining_links == 0:
        # Mark for deletion
        db.documents.update_one(
            {"id": document_id},
            {"$set": {"status": DocumentStatus.DELETING.value}}
        )
        
        # Queue cleanup job
        # In M6 we'll implement the actual cleanup background job
        # For now, we'll do immediate cleanup in a simple way
        try:
            # Delete chunks
            db.chunks.delete_many({"document_id": document_id})
            
            # Delete from S3
            delete_from_s3(doc["s3_key"])
            
            # Delete document record
            db.documents.delete_one({"id": document_id})
            
            return {"status": "deleted", "message": "Document deleted completely"}
        except Exception as e:
            # If cleanup fails, document stays in "deleting" status
            # Background job will retry
            return {"status": "deleting", "message": "Document marked for deletion"}
    
    return {"status": "unlinked", "message": "Document unlinked from scope"}
