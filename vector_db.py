import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()


class MongoDBStorage:
    """Vector storage using MongoDB Atlas with vector search capabilities."""
    
    def __init__(self, collection_name: str = "documents", db_name: str = "rag_db"):
        uri = os.getenv("MONGODB_URI")
        if not uri:
            raise ValueError("MONGODB_URI environment variable is not set")
        
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        
        # Create index on 'id' field for efficient lookups
        self.collection.create_index("doc_id", unique=True, sparse=True)
    
    def upsert(self, ids: list[str], vectors: list[list[float]], payloads: list[dict], workspace_id: str = None):
        """Insert or update documents with their embeddings.
        
        Args:
            ids: Unique document chunk IDs
            vectors: Embedding vectors
            payloads: Document metadata (source, text, page, etc.)
            workspace_id: If provided, associates documents with a workspace for scoped queries
        """
        operations = []
        for i, doc_id in enumerate(ids):
            doc = {
                "doc_id": doc_id,
                "embedding": vectors[i],
                **payloads[i]  # Include source, text, page, etc.
            }
            # Add workspace_id if provided
            if workspace_id:
                doc["workspace_id"] = workspace_id
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
    
    def search(self, query_vector: list[float], top_k: int = 5, workspace_id: str = None) -> dict:
        """
        Search for similar documents using MongoDB Atlas Vector Search.
        
        Args:
            query_vector: The embedding vector to search with
            top_k: Number of results to return
            workspace_id: If provided, only search within this workspace (O(1) pre-filtering)
        
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
        
        # Add filter if workspace_id is specified (efficient O(1) pre-filtering)
        if workspace_id:
            vector_search_stage["$vectorSearch"]["filter"] = {"workspace_id": workspace_id}
        
        pipeline = [
            vector_search_stage,
            {
                "$project": {
                    "_id": 0,
                    "text": 1,
                    "source": 1,
                    "page": 1,
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


# Alias for backward compatibility
VectorStorage = MongoDBStorage
