"""Data models for the RAG application."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix."""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


class Workspace(BaseModel):
    """A workspace containing documents and chat sessions."""
    id: str = Field(default_factory=lambda: generate_id("ws_"))
    name: str
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
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sources: list[str] = Field(default_factory=list)  # For assistant messages
