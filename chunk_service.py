"""Chunk storage service for document ingestion.

Provides functions for managing chunks in the chunks collection:
- save_chunks: Bulk insert/upsert chunks
- delete_chunks: Cascade delete for a document
- get_chunks: Retrieve chunks for debugging
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv

load_dotenv()

from models import Chunk, Document, DocumentStatus


def get_db():
    """Get MongoDB database connection."""
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        raise RuntimeError("MONGODB_URI not configured")
    client = MongoClient(mongodb_uri)
    db_name = os.getenv("MONGODB_DATABASE", "docurag")
    return client[db_name]


def generate_chunk_id(document_id: str, chunk_index: int) -> str:
    """Generate deterministic chunk ID for idempotent ingestion.
    
    Same document + same chunk index = same chunk ID.
    This allows re-ingest without duplicates.
    """
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document_id}:{chunk_index}"))


def save_chunks(
    document_id: str,
    chunks_data: list[dict],
    embeddings: list[list[float]]
) -> int:
    """Save chunks to the chunks collection.
    
    Args:
        document_id: The document these chunks belong to
        chunks_data: List of dicts with keys: text, page_number, chunk_index
        embeddings: List of embedding vectors (1536 dims)
    
    Returns:
        Number of chunks saved
    """
    if not chunks_data:
        return 0
    
    db = get_db()
    
    # Build chunk documents for upsert
    bulk_ops = []
    for i, (chunk_data, embedding) in enumerate(zip(chunks_data, embeddings)):
        chunk_id = generate_chunk_id(document_id, chunk_data["chunk_index"])
        
        chunk_doc = {
            "id": chunk_id,
            "document_id": document_id,
            "chunk_index": chunk_data["chunk_index"],
            "page_number": chunk_data["page_number"],
            "text": chunk_data["text"],
            "embedding": embedding
        }
        
        # Upsert by chunk ID
        bulk_ops.append(
            UpdateOne(
                {"id": chunk_id},
                {"$set": chunk_doc},
                upsert=True
            )
        )
    
    if bulk_ops:
        result = db.chunks.bulk_write(bulk_ops)
        return result.upserted_count + result.modified_count
    
    return 0


def delete_chunks(document_id: str) -> int:
    """Delete all chunks for a document.
    
    Args:
        document_id: The document whose chunks to delete
    
    Returns:
        Number of chunks deleted
    """
    db = get_db()
    result = db.chunks.delete_many({"document_id": document_id})
    return result.deleted_count


def get_chunks(document_id: str) -> list[dict]:
    """Get all chunks for a document.
    
    Args:
        document_id: The document ID
    
    Returns:
        List of chunk documents (without embeddings for readability)
    """
    db = get_db()
    chunks = list(db.chunks.find(
        {"document_id": document_id},
        {"embedding": 0, "_id": 0}  # Exclude embedding and _id
    ).sort("chunk_index", 1))
    return chunks


def update_document_status(document_id: str, status: DocumentStatus) -> bool:
    """Update a document's status.
    
    Args:
        document_id: The document ID
        status: The new status
    
    Returns:
        True if document was updated, False otherwise
    """
    db = get_db()
    result = db.documents.update_one(
        {"id": document_id},
        {"$set": {"status": status.value}}
    )
    return result.modified_count > 0


def get_document(document_id: str) -> Optional[dict]:
    """Get a document by ID.
    
    Args:
        document_id: The document ID
    
    Returns:
        Document dict or None
    """
    db = get_db()
    doc = db.documents.find_one({"id": document_id}, {"_id": 0})
    return doc
