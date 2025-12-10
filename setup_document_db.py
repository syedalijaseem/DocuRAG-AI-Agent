"""Setup MongoDB indexes for document system.

Creates indexes on:
- documents: checksum (unique), s3_key (unique), status
- document_scopes: document_id, (scope_type, scope_id), unique compound
- chunks: document_id
"""
import os
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv

load_dotenv()


def setup_document_indexes():
    """Create all indexes for the document system."""
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        raise RuntimeError("MONGODB_URI environment variable not set")
    
    client = MongoClient(mongodb_uri)
    # Get database name from URI or use default
    db_name = os.getenv("MONGODB_DATABASE", "docurag")
    db = client[db_name]
    
    print("Setting up document system indexes...")
    
    # --- Documents Collection ---
    print("\n📄 documents collection:")
    
    # Unique index on checksum for deduplication
    db.documents.create_index(
        [("checksum", ASCENDING)],
        unique=True,
        name="idx_documents_checksum_unique"
    )
    print("  ✅ Created unique index on checksum")
    
    # Unique index on s3_key
    db.documents.create_index(
        [("s3_key", ASCENDING)],
        unique=True,
        name="idx_documents_s3_key_unique"
    )
    print("  ✅ Created unique index on s3_key")
    
    # Index on status for filtering
    db.documents.create_index(
        [("status", ASCENDING)],
        name="idx_documents_status"
    )
    print("  ✅ Created index on status")
    
    # --- Document Scopes Collection ---
    print("\n🔗 document_scopes collection:")
    
    # Index on document_id for cascade deletes
    db.document_scopes.create_index(
        [("document_id", ASCENDING)],
        name="idx_document_scopes_document_id"
    )
    print("  ✅ Created index on document_id")
    
    # Compound index on scope for efficient queries
    db.document_scopes.create_index(
        [("scope_type", ASCENDING), ("scope_id", ASCENDING)],
        name="idx_document_scopes_scope"
    )
    print("  ✅ Created compound index on (scope_type, scope_id)")
    
    # Unique compound to prevent duplicate links
    db.document_scopes.create_index(
        [("document_id", ASCENDING), ("scope_type", ASCENDING), ("scope_id", ASCENDING)],
        unique=True,
        name="idx_document_scopes_unique_link"
    )
    print("  ✅ Created unique compound index for document-scope uniqueness")
    
    # --- Chunks Collection ---
    print("\n📦 chunks collection:")
    
    # Index on document_id for batch operations
    db.chunks.create_index(
        [("document_id", ASCENDING)],
        name="idx_chunks_document_id"
    )
    print("  ✅ Created index on document_id")
    
    # Compound index for ordered retrieval
    db.chunks.create_index(
        [("document_id", ASCENDING), ("chunk_index", ASCENDING)],
        name="idx_chunks_document_order"
    )
    print("  ✅ Created compound index for ordered chunk retrieval")
    
    print("\n✅ All document system indexes created successfully!")
    print("\n⚠️  REMINDER: Create vector search index in MongoDB Atlas UI:")
    print("   Collection: chunks")
    print("   Field: embedding")
    print("   Dimensions: 1536")
    print("   Similarity: cosine")
    
    client.close()


if __name__ == "__main__":
    setup_document_indexes()
