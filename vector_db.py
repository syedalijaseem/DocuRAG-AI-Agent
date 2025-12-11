import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()


class MongoDBStorage:
    """Vector storage using MongoDB Atlas with vector search capabilities."""
    
    def __init__(self, collection_name: str = "documents", db_name: str = None):
        uri = os.getenv("MONGODB_URI")
        if not uri:
            raise ValueError("MONGODB_URI environment variable is not set")
        
        if db_name is None:
            db_name = os.getenv("MONGODB_DATABASE", "docurag")
        
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        
        # Create index on 'id' field for efficient lookups
        self.collection.create_index("doc_id", unique=True, sparse=True)
    
    def upsert(self, ids: list[str], vectors: list[list[float]], payloads: list[dict], 
               scope_type: str = None, scope_id: str = None):
        """Insert or update documents with their embeddings.
        
        Args:
            ids: Unique document chunk IDs
            vectors: Embedding vectors
            payloads: Document metadata (source, text, page, etc.)
            scope_type: 'chat' or 'project' for document scoping
            scope_id: The ID of the chat or project
        """
        operations = []
        for i, doc_id in enumerate(ids):
            doc = {
                "doc_id": doc_id,
                "embedding": vectors[i],
                **payloads[i]  # Include source, text, page, etc.
            }
            # Add scope info if provided
            if scope_type and scope_id:
                doc["scope_type"] = scope_type
                doc["scope_id"] = scope_id
            operations.append(doc)
        
        # Use bulk upsert
        from pymongo import UpdateOne
        bulk_ops = [
            UpdateOne(
                {"doc_id": doc["doc_id"]},
                {"$set": doc},
                upsert=True
            )
            for doc in operations
        ]
        
        if bulk_ops:
            self.collection.bulk_write(bulk_ops)
    
    def search(self, query_vector: list[float], top_k: int = 5, 
               scope_type: str = None, scope_id: str = None, 
               include_project: bool = True, project_id: str = None) -> dict:
        """
        Search for similar documents using MongoDB Atlas Vector Search.
        
        Args:
            query_vector: The embedding vector to search with
            top_k: Number of results to return
            scope_type: 'chat' or 'project' for filtering
            scope_id: The chat_id or project_id to search within
            include_project: If True and searching a chat, also include project docs
            project_id: The project_id to include (for project chats)
        
        Note: This requires a vector search index with filter field in MongoDB Atlas.
        """
        # Build the $vectorSearch stage with optional pre-filter
        vector_search_stage = {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": query_vector,
                "numCandidates": top_k * 10,
                "limit": top_k
            }
        }
        
        # Build filter for scope-based search
        if scope_type and scope_id:
            if scope_type == "project":
                # Search only project docs
                vector_search_stage["$vectorSearch"]["filter"] = {
                    "scope_type": "project",
                    "scope_id": scope_id
                }
            elif scope_type == "chat":
                if include_project and project_id:
                    # Search both chat docs and project docs
                    vector_search_stage["$vectorSearch"]["filter"] = {
                        "$or": [
                            {"scope_type": "chat", "scope_id": scope_id},
                            {"scope_type": "project", "scope_id": project_id}
                        ]
                    }
                else:
                    # Search only chat docs
                    vector_search_stage["$vectorSearch"]["filter"] = {
                        "scope_type": "chat",
                        "scope_id": scope_id
                    }
        
        pipeline = [
            vector_search_stage,
            {
                "$project": {
                    "_id": 0,
                    "text": 1,
                    "source": 1,
                    "page": 1,
                    "scope_type": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]
        
        results = list(self.collection.aggregate(pipeline))
        
        contexts = []
        sources = []
        scores = []
        
        for r in results:
            text = r.get("text", "")
            source = r.get("source", "")
            page = r.get("page", "?")
            score = r.get("score", 0)
            
            if text:
                contexts.append(text)
                sources.append(f"{source}, page {page}")
                scores.append(score)
        
        return {"contexts": contexts, "sources": sources, "scores": scores}

    def delete_by_scope(self, scope_type: str, scope_id: str) -> int:
        """Delete all embeddings for a scope (chat or project).
        
        Args:
            scope_type: 'chat' or 'project'
            scope_id: The ID of the chat or project
            
        Returns:
            Number of documents deleted
        """
        result = self.collection.delete_many({
            "scope_type": scope_type,
            "scope_id": scope_id
        })
        return result.deleted_count

    def delete_by_source(self, source: str, scope_type: str = None, scope_id: str = None) -> int:
        """Delete all embeddings for a specific source document.
        
        Args:
            source: The source filename/path
            scope_type: Optional scope filter
            scope_id: Optional scope ID filter
            
        Returns:
            Number of documents deleted
        """
        query = {"source": source}
        if scope_type and scope_id:
            query["scope_type"] = scope_type
            query["scope_id"] = scope_id
        result = self.collection.delete_many(query)
        return result.deleted_count


# Alias for backward compatibility
VectorStorage = MongoDBStorage
