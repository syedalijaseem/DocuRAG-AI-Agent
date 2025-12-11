
import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

def debug_rag(chat_id):
    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        print("Error: MONGODB_URI not set")
        return

    client = MongoClient(mongo_uri)
    db = client[os.getenv("MONGODB_DATABASE", "docurag")]
    
    print(f"--- Debugging RAG for Chat ID: {chat_id} ---")

    # 1. Get Chat Info & Project ID
    print("\n1. Fetching Chat Details...")
    chat = db.chats.find_one({"id": chat_id})
    if not chat:
        print(f"ERROR: Chat {chat_id} not found in DB!")
        return
    
    print(f"  Chat Title: {chat.get('title')}")
    project_id = chat.get("project_id")
    print(f"  Project ID: {project_id}")

    # 2. Check Document Scopes (Chat + Project)
    print("\n2. Checking Document Scopes...")
    query = {"scope_type": "chat", "scope_id": chat_id}
    if project_id:
        query = {
            "$or": [
                {"scope_type": "chat", "scope_id": chat_id},
                {"scope_type": "project", "scope_id": project_id}
            ]
        }
    
    scopes = list(db.document_scopes.find(query))
    print(f"Found {len(scopes)} linked scopes (Chat + Project).")
    
    doc_ids = []
    for scope in scopes:
        print(f"  - Scope: {scope['scope_type']} {scope['scope_id']}")
        print(f"    Document ID: {scope['document_id']}")
        doc_ids.append(scope['document_id'])

    # Deduplicate
    doc_ids = list(set(doc_ids))
    print(f"Unique Document IDs: {len(doc_ids)}")

    if not doc_ids:
        print("No documents found. System has empty context.")
        return

    # 3. Check Documents status
    print("\n3. Checking Document Status & Chunks...")
    docs = list(db.documents.find({"id": {"$in": doc_ids}}))
    
    for doc in docs:
        doc_id = doc["id"]
        status = doc.get('status', 'unknown')
        s3_key = doc.get('s3_key')
        
        # Count chunks
        chunk_count = db.chunks.count_documents({"document_id": doc_id})
        
        print(f"  [Doc] {doc.get('filename')} ({doc_id})")
        print(f"    Status: {status}")
        print(f"    Chunks: {chunk_count}")
        print(f"    S3 Key: {s3_key}")
        
        if status == 'pending':
            print("    ⚠️  WARNING: Document is still PENDING. Ingestion invalid or stuck?")
        elif status == 'ready' and chunk_count == 0:
            print("    ❌  CRITICAL: Document is READY but has 0 CHUNKS. Ingestion passed but saved nothing?")

    # 4. vector search check
    print("\n4. Testing Vector Search Aggregation...")
    if doc_ids:
        # Dummy vector 
        dummy_vector = [0.0] * 1536 
        
        # We need to filter by document_ids we found
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": dummy_vector,
                    "numCandidates": 10,
                    "limit": 1,
                    "filter": {
                        "document_id": {"$in": doc_ids}
                    }
                }
            },
             {
                "$project": {
                    "text": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]
        
        try:
            results = list(db.chunks.aggregate(pipeline))
            print(f"  Vector Search returned {len(results)} results (with dummy vector).")
            if len(results) == 0:
                 print("  Search returned 0 results. Either no chunks exist or Index is broken.")
        except Exception as e:
            print(f"  SEARCH FAILED: {e}")

if __name__ == "__main__":
    target_chat_id = "chat_acb0cea7eb31" 
    if len(sys.argv) > 1:
        target_chat_id = sys.argv[1]
    
    debug_rag(target_chat_id)
