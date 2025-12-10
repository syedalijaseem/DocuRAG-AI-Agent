"""Chunk search service for M2+ architecture.

Searches chunks collection using document_id filtering.
Gets document_ids from DocumentScope for user's scopes.
"""
import os
from typing import Optional
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()


def get_db():
    """Get MongoDB database connection."""
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        raise RuntimeError("MONGODB_URI not configured")
    client = MongoClient(mongodb_uri)
    db_name = os.getenv("MONGODB_DATABASE", "docurag")
    return client[db_name]


def get_document_ids_for_scope(
    scope_type: str, 
    scope_id: str,
    include_project: bool = True,
    project_id: str = None
) -> list[str]:
    """Get document IDs linked to the specified scope.
    
    Args:
        scope_type: 'chat' or 'project'
        scope_id: The scope ID
        include_project: If True and scope is chat, also include project docs
        project_id: The project ID for a chat that belongs to a project
    
    Returns:
        List of document IDs
    """
    db = get_db()
    
    # Build query for DocumentScope
    if scope_type == "project":
        query = {"scope_type": "project", "scope_id": scope_id}
    elif scope_type == "chat":
        if include_project and project_id:
            # Include both chat and project docs
            query = {
                "$or": [
                    {"scope_type": "chat", "scope_id": scope_id},
                    {"scope_type": "project", "scope_id": project_id}
                ]
            }
        else:
            query = {"scope_type": "chat", "scope_id": scope_id}
    else:
        return []
    
    # Get document_ids from document_scopes
    scopes = list(db.document_scopes.find(query, {"document_id": 1}))
    document_ids = list(set(s["document_id"] for s in scopes))
    
    return document_ids


def search_chunks(
    query_vector: list[float],
    document_ids: list[str],
    top_k: int = 5
) -> dict:
    """Search for similar chunks using MongoDB Atlas Vector Search.
    
    Args:
        query_vector: The embedding vector to search with
        document_ids: List of document IDs to filter by
        top_k: Number of results to return
    
    Returns:
        Dict with contexts, sources, scores
    """
    if not document_ids:
        return {"contexts": [], "sources": [], "scores": []}
    
    db = get_db()
    
    # Build vector search pipeline
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": query_vector,
                "numCandidates": top_k * 10,
                "limit": top_k,
                "filter": {
                    "document_id": {"$in": document_ids}
                }
            }
        },
        {
            "$project": {
                "_id": 0,
                "text": 1,
                "page_number": 1,
                "document_id": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        },
        # Join to get document filename
        {
            "$lookup": {
                "from": "documents",
                "localField": "document_id",
                "foreignField": "id",
                "as": "doc_info"
            }
        },
        {
            "$unwind": {
                "path": "$doc_info",
                "preserveNullAndEmptyArrays": True
            }
        },
        {
            "$project": {
                "text": 1,
                "page_number": 1,
                "score": 1,
                "filename": "$doc_info.filename"
            }
        }
    ]
    
    results = list(db.chunks.aggregate(pipeline))
    
    contexts = []
    sources = []
    scores = []
    
    for r in results:
        text = r.get("text", "")
        filename = r.get("filename", "Unknown")
        page = r.get("page_number", "?")
        score = r.get("score", 0)
        
        if text:
            contexts.append(text)
            sources.append(f"{filename}, page {page}")
            scores.append(score)
    
    return {"contexts": contexts, "sources": sources, "scores": scores}


def search_for_scope(
    query_vector: list[float],
    scope_type: str,
    scope_id: str,
    top_k: int = 5,
    include_project: bool = True,
    project_id: str = None
) -> dict:
    """High-level search function for a scope.
    
    This is the main entry point for RAG queries.
    
    Args:
        query_vector: The embedding vector
        scope_type: 'chat' or 'project'
        scope_id: The scope ID
        top_k: Number of results
        include_project: Include project docs for chat searches
        project_id: Project ID if chat belongs to project
    
    Returns:
        Dict with contexts, sources, scores
    """
    document_ids = get_document_ids_for_scope(
        scope_type, 
        scope_id,
        include_project,
        project_id
    )
    
    return search_chunks(query_vector, document_ids, top_k)
