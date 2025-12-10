"""Pydantic models for the RAG application.

This module provides type-safe models for:
- Domain entities (Workspace, Document, ChatSession, Message)
- Inngest event payloads (IngestPdfEvent, QueryPdfEvent)
- API responses (SearchResult, QueryResult)
- Internal chunking/embedding data
"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from typing import Optional
from enum import Enum
import uuid


# --- Utilities ---

def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix."""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


# --- Enums ---

class MessageRole(str, Enum):
    """Valid roles for chat messages."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ScopeType(str, Enum):
    """Scope types for document ownership."""
    CHAT = "chat"        # Document belongs to a specific chat
    PROJECT = "project"  # Document belongs to a project (shared across chats)


class DocumentStatus(str, Enum):
    """Document lifecycle status."""
    PENDING = "pending"    # Uploaded, ingestion in progress
    READY = "ready"        # Fully ingested, searchable
    DELETING = "deleting"  # Marked for deletion, hidden from queries


class AuthProvider(str, Enum):
    """Supported authentication providers."""
    EMAIL = "email"
    GOOGLE = "google"


class UserStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    PENDING = "pending"    # Email not verified
    LOCKED = "locked"      # Temporarily locked
    DELETED = "deleted"    # Soft deleted


# --- Authentication Entities ---

class User(BaseModel):
    """User account for authentication."""
    id: str = Field(default_factory=lambda: generate_id("user_"))
    email: str
    password_hash: Optional[str] = None  # Nullable for OAuth-only users
    name: str
    avatar_url: Optional[str] = None
    email_verified: bool = False
    verification_token_hash: Optional[str] = None
    verification_expires_at: Optional[datetime] = None
    reset_token_hash: Optional[str] = None
    reset_expires_at: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Basic email format validation."""
        v = v.strip().lower()
        if not v or '@' not in v or '.' not in v.split('@')[-1]:
            raise ValueError('Invalid email format')
        if len(v) > 255:
            raise ValueError('Email too long')
        return v
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name is not empty."""
        v = v.strip()
        if not v:
            raise ValueError('Name cannot be empty')
        if len(v) > 100:
            raise ValueError('Name too long')
        return v


class UserProvider(BaseModel):
    """OAuth provider linked to a user account."""
    id: str = Field(default_factory=lambda: generate_id("prov_"))
    user_id: str
    provider: AuthProvider
    provider_user_id: str  # The user's ID from the OAuth provider
    linked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RefreshToken(BaseModel):
    """Refresh token for session management."""
    id: str = Field(default_factory=lambda: generate_id("rt_"))
    user_id: str
    token_hash: str  # SHA-256 hash of the actual token
    device_info: Optional[str] = None  # User agent or device name
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    revoked: bool = False


# --- Auth Request/Response Models ---

class RegisterRequest(BaseModel):
    """Request body for user registration."""
    email: str
    password: str
    name: str
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Basic email format validation."""
        v = v.strip().lower()
        if not v or '@' not in v or '.' not in v.split('@')[-1]:
            raise ValueError('Invalid email format')
        if len(v) > 255:
            raise ValueError('Email too long')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v


class LoginRequest(BaseModel):
    """Request body for login."""
    email: str
    password: str


class GoogleAuthRequest(BaseModel):
    """Request body for Google OAuth."""
    id_token: str


class PasswordResetRequest(BaseModel):
    """Request body for password reset initiation."""
    email: str


class PasswordResetComplete(BaseModel):
    """Request body for completing password reset."""
    token: str
    new_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password meets security requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v


class EmailChangeRequest(BaseModel):
    """Request body for email change."""
    new_email: str
    password: str


class PasswordChangeRequest(BaseModel):
    """Request body for password change."""
    current_password: str
    new_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password meets security requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v


class UserResponse(BaseModel):
    """Response body for user data (excludes sensitive fields)."""
    id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    email_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None


class AuthResponse(BaseModel):
    """Response after successful authentication."""
    user: UserResponse
    is_new: bool = False


class SessionInfo(BaseModel):
    """Information about an active session."""
    id: str
    device_info: Optional[str] = None
    created_at: datetime
    expires_at: datetime
    is_current: bool = False


# --- Domain Entities ---

class Project(BaseModel):
    """A project containing documents and chats."""
    id: str = Field(default_factory=lambda: generate_id("proj_"))
    name: str = "New Project"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Chat(BaseModel):
    """A chat session, either standalone or within a project."""
    id: str = Field(default_factory=lambda: generate_id("chat_"))
    project_id: Optional[str] = None  # None = standalone chat
    title: str = "New Chat"
    is_pinned: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Document(BaseModel):
    """A document in the global document store.
    
    Documents are stored once and linked to scopes via DocumentScope.
    Deduplication is achieved via checksum - same file = same document.
    """
    id: str = Field(default_factory=lambda: generate_id("doc_"))
    filename: str
    s3_key: str  # S3 object key (unique)
    checksum: str  # SHA-256 hash for deduplication (unique)
    size_bytes: int = Field(ge=0)  # File size in bytes
    status: DocumentStatus = DocumentStatus.PENDING
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @field_validator('checksum')
    @classmethod
    def validate_checksum(cls, v: str) -> str:
        """Validate SHA-256 checksum format."""
        v = v.strip().lower()
        if not v.startswith('sha256:'):
            raise ValueError('Checksum must be prefixed with sha256:')
        hex_part = v[7:]  # Remove 'sha256:' prefix
        if len(hex_part) != 64:
            raise ValueError('SHA-256 hash must be 64 hex characters')
        if not all(c in '0123456789abcdef' for c in hex_part):
            raise ValueError('Checksum must contain only hex characters')
        return v
    
    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Sanitize filename."""
        v = v.strip()
        if not v:
            raise ValueError('Filename cannot be empty')
        # Remove dangerous characters
        v = v.replace('..', '').replace('/', '').replace('\\', '')
        if len(v) > 255:
            raise ValueError('Filename too long')
        return v


class DocumentScope(BaseModel):
    """Links a document to a scope (chat or project).
    
    This junction table enables:
    - One document linked to multiple scopes (reuse)
    - Clean deletion (remove link, orphan cleanup handles doc)
    - Scope isolation (queries filter by scope)
    """
    id: str = Field(default_factory=lambda: generate_id("ds_"))
    document_id: str
    scope_type: ScopeType
    scope_id: str  # chat_id or project_id
    linked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Chunk(BaseModel):
    """A chunk of document text with its embedding.
    
    Chunks reference document by ID only - no metadata duplication.
    """
    id: str = Field(default_factory=lambda: generate_id("chunk_"))
    document_id: str
    chunk_index: int = Field(ge=0)  # Position in document (0-indexed)
    page_number: int = Field(ge=1)  # Source page (1-indexed)
    text: str
    embedding: list[float] = Field(default_factory=list)  # 1536-dim vector
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate chunk text is not empty."""
        if not v.strip():
            raise ValueError('Chunk text cannot be empty')
        return v
    
    @field_validator('embedding')
    @classmethod
    def validate_embedding(cls, v: list[float]) -> list[float]:
        """Validate embedding dimensions (if provided)."""
        if v and len(v) != 1536:
            raise ValueError('Embedding must have 1536 dimensions')
        return v


class Message(BaseModel):
    """A message in a chat."""
    id: str = Field(default_factory=lambda: generate_id("msg_"))
    chat_id: str  # Changed from session_id
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sources: list[str] = Field(default_factory=list)


# --- Legacy/Backward Compatibility ---

class Workspace(BaseModel):
    """DEPRECATED: Use Project instead. Kept for migration."""
    id: str = Field(default_factory=lambda: generate_id("ws_"))
    name: str = "Default Workspace"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatSession(BaseModel):
    """DEPRECATED: Use Chat instead. Kept for migration."""
    id: str = Field(default_factory=lambda: generate_id("sess_"))
    workspace_id: str
    title: str = "New Chat"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --- Inngest Event Payloads ---

class IngestPdfEventData(BaseModel):
    """Payload for rag/ingest_pdf event."""
    pdf_path: str  # S3 key
    filename: str  # Original filename
    scope_type: ScopeType
    scope_id: str  # chat_id or project_id
    document_id: str  # Document ID for chunk linking (M2)
    
    @field_validator('pdf_path')
    @classmethod
    def validate_pdf_path(cls, v: str) -> str:
        # Security: Reject null bytes (path manipulation attack)
        if '\x00' in v:
            raise ValueError('pdf_path cannot contain null bytes')
        # Security: Reject path traversal attempts
        if '..' in v:
            raise ValueError('pdf_path cannot contain path traversal sequences')
        if not v.endswith('.pdf'):
            raise ValueError('pdf_path must end with .pdf')
        return v


class QueryPdfEventData(BaseModel):
    """Payload for rag/query_pdf_ai event."""
    question: str
    chat_id: str  # Which chat is asking (for context/history)
    scope_type: ScopeType
    scope_id: str  # For project chats, this is project_id
    top_k: int = Field(default=5, ge=1, le=50)
    history: list[dict] = Field(default_factory=list)
    
    @field_validator('question')
    @classmethod
    def validate_question(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('question cannot be empty')
        return v.strip()


# --- Internal Data Structures ---

class ChunkWithPage(BaseModel):
    """A text chunk with its page number."""
    text: str
    page: int = Field(ge=1)


class RAGChunkAndSrc(BaseModel):
    """Chunks from a document with source info."""
    chunks: list[ChunkWithPage]
    source_id: str


class RAGUpsertResult(BaseModel):
    """Result of upserting document chunks."""
    ingested: int = Field(ge=0)
    workspace_id: Optional[str] = None


# --- Search & Query Results ---

class SearchResult(BaseModel):
    """Result from vector search."""
    contexts: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    scores: list[float] = Field(default_factory=list)


class QueryResult(BaseModel):
    """Full result from RAG query."""
    answer: str
    sources: list[str] = Field(default_factory=list)
    num_contexts: int = Field(ge=0)
    history: list[dict] = Field(default_factory=list)
    avg_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


# --- Backward Compatibility Aliases ---
# These can be removed once all code is migrated

RAGSearchResult = SearchResult
RAGQueryResult = QueryResult
