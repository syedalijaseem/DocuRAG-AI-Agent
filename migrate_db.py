"""
Migration script to copy data from rag_db to docurag database.
"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

def migrate():
    client = MongoClient(os.getenv("MONGODB_URI"))
    
    source_db = client["rag_db"]
    target_db = client[os.getenv("MONGODB_DATABASE", "docurag")]
    
    collections = ["chats", "projects", "documents", "document_scopes", "messages", "users", "refresh_tokens"]
    
    for coll_name in collections:
        source_coll = source_db[coll_name]
        target_coll = target_db[coll_name]
        
        docs = list(source_coll.find({}))
        if docs:
            # Use upsert to avoid duplicates
            from pymongo import UpdateOne
            ops = [
                UpdateOne({"id": doc.get("id") or doc.get("_id")}, {"$set": doc}, upsert=True)
                for doc in docs
            ]
            result = target_coll.bulk_write(ops)
            print(f"[{coll_name}] Migrated {result.upserted_count} new, {result.modified_count} updated from {len(docs)} total")
        else:
            print(f"[{coll_name}] No documents to migrate")

if __name__ == "__main__":
    print("Migrating data from rag_db to docurag...")
    migrate()
    print("Migration complete!")
