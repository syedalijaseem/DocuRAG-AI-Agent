"""Pydantic models for the RAG application.

This module provides type-safe models for:
- Domain entities (Workspace, Document, ChatSession, Message)
- Inngest event payloads (IngestPdfEvent, QueryPdfEvent)
- API responses (SearchResult, QueryResult)
- Internal chunking/embedding data
"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
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


# --- Domain Entities ---

class Workspace(BaseModel):
    """A workspace containing documents and chat sessions."""
    id: str = Field(default_factory=lambda: generate_id("ws_"))
    name: str = "Default Workspace"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Document(BaseModel):
    """A document uploaded to a workspace."""
    id: str = Field(default_factory=lambda: generate_id("doc_"))
    workspace_id: str
    filename: str
    source_id: str  # Used for vector search filtering
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class ChatSession(BaseModel):
    """A chat session within a workspace."""
    id: str = Field(default_factory=lambda: generate_id("sess_"))
    workspace_id: str
    title: str = "New Chat"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Message(BaseModel):
    """A message in a chat session."""
    id: str = Field(default_factory=lambda: generate_id("msg_"))
    session_id: str
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sources: list[str] = Field(default_factory=list)


# --- Inngest Event Payloads ---

class IngestPdfEventData(BaseModel):
    """Payload for rag/ingest_pdf event."""
    pdf_path: str
    source_id: str
    workspace_id: Optional[str] = None
    
    @field_validator('pdf_path')
    @classmethod
    def validate_pdf_path(cls, v: str) -> str:
        # Security: Reject null bytes (path manipulation attack)
        if '\x00' in v:
            raise ValueError('pdf_path cannot contain null bytes')
        if not v.endswith('.pdf'):
            raise ValueError('pdf_path must end with .pdf')
        return v


class QueryPdfEventData(BaseModel):
    """Payload for rag/query_pdf_ai event."""
    question: str
    top_k: int = Field(default=5, ge=1, le=50)
    workspace_id: Optional[str] = None
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
