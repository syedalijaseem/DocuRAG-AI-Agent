"""
Clean database reset script.
Drops all collections and sets up fresh indexes.
"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

def reset_database():
    client = MongoClient(os.getenv("MONGODB_URI"))
    db_name = os.getenv("MONGODB_DATABASE", "docurag")
    db = client[db_name]
    
    print(f"=== Resetting database: {db_name} ===")
    
    # Drop all collections
    collections = ["chunks", "documents", "document_scopes", "chats", "projects", "messages"]
    for coll in collections:
        db[coll].drop()
        print(f"Dropped: {coll}")
    
    # Create indexes
    print("\n=== Creating indexes ===")
    
    # Documents
    db.documents.create_index("id", unique=True)
    db.documents.create_index("checksum")
    print("Created indexes on documents")
    
    # Chunks
    db.chunks.create_index("id", unique=True)
    db.chunks.create_index("document_id")
    print("Created indexes on chunks")
    
    # Document scopes
    db.document_scopes.create_index("id", unique=True)
    db.document_scopes.create_index([("scope_type", 1), ("scope_id", 1)])
    db.document_scopes.create_index(
        [("document_id", 1), ("scope_type", 1), ("scope_id", 1)],
        name="idx_document_scopes_unique_link",
        unique=True
    )
    print("Created indexes on document_scopes")
    
    # Chats
    db.chats.create_index("id", unique=True)
    db.chats.create_index("project_id")
    print("Created indexes on chats")
    
    # Projects
    db.projects.create_index("id", unique=True)
    print("Created indexes on projects")
    
    print("\n=== Database reset complete ===")
    print()
    print("NEXT STEP: Create vector search index in MongoDB Atlas:")
    print("  Collection: docurag.chunks")
    print("  Index name: vector_index")
    print("  Definition:")
    print('''
{
  "fields": [
    {
      "numDimensions": 3072,
      "path": "embedding",
      "similarity": "cosine",
      "type": "vector"
    },
    {
      "path": "document_id",
      "type": "filter"
    }
  ]
}
''')

if __name__ == "__main__":
    confirm = input("This will DELETE ALL DATA. Type 'yes' to confirm: ")
    if confirm.lower() == "yes":
        reset_database()
    else:
        print("Cancelled.")
