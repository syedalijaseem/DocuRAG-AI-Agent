"""Database setup and indexes for authentication.

Run this script to create necessary MongoDB indexes for the auth system.
"""
import os
from pymongo import MongoClient, ASCENDING
from pymongo.errors import CollectionInvalid
from dotenv import load_dotenv

load_dotenv()


def setup_auth_indexes():
    """Create all necessary indexes for authentication collections."""
    uri = os.getenv("MONGODB_URI")
    if not uri:
        print("ERROR: MONGODB_URI not set")
        return False
    
    client = MongoClient(uri)
    db = client["rag_db"]
    
    print("Setting up authentication indexes...")
    
    # --- Users Collection ---
    print("\n1. Users collection:")
    
    # Unique email index
    db.users.create_index(
        [("email", ASCENDING)],
        unique=True,
        name="users_email_unique"
    )
    print("   ✓ Created unique index on email")
    
    # Index for user ID lookups
    db.users.create_index(
        [("id", ASCENDING)],
        unique=True,
        name="users_id_unique"
    )
    print("   ✓ Created unique index on id")
    
    # Sparse index for verification token (only index if exists)
    db.users.create_index(
        [("verification_token_hash", ASCENDING)],
        sparse=True,
        name="users_verification_token"
    )
    print("   ✓ Created sparse index on verification_token_hash")
    
    # Sparse index for reset token
    db.users.create_index(
        [("reset_token_hash", ASCENDING)],
        sparse=True,
        name="users_reset_token"
    )
    print("   ✓ Created sparse index on reset_token_hash")
    
    # --- User Providers Collection ---
    print("\n2. User Providers collection:")
    
    # Index for user lookups
    db.user_providers.create_index(
        [("user_id", ASCENDING)],
        name="providers_user_id"
    )
    print("   ✓ Created index on user_id")
    
    # Unique compound index for provider + provider_user_id
    db.user_providers.create_index(
        [("provider", ASCENDING), ("provider_user_id", ASCENDING)],
        unique=True,
        name="providers_unique"
    )
    print("   ✓ Created unique compound index on (provider, provider_user_id)")
    
    # --- Refresh Tokens Collection ---
    print("\n3. Refresh Tokens collection:")
    
    # Index for user lookups
    db.refresh_tokens.create_index(
        [("user_id", ASCENDING)],
        name="tokens_user_id"
    )
    print("   ✓ Created index on user_id")
    
    # Unique index for token hash
    db.refresh_tokens.create_index(
        [("token_hash", ASCENDING)],
        unique=True,
        name="tokens_hash_unique"
    )
    print("   ✓ Created unique index on token_hash")
    
    # TTL index for automatic expiration (optional cleanup)
    # Note: MongoDB will automatically delete documents when expires_at passes
    # We're not using TTL here since we want to keep revoked tokens for audit
    # Instead, we'll use a cleanup job
    
    db.refresh_tokens.create_index(
        [("expires_at", ASCENDING)],
        name="tokens_expires_at"
    )
    print("   ✓ Created index on expires_at")
    
    print("\n✅ All auth indexes created successfully!")
    
    # Print existing indexes for verification
    print("\n--- Current Indexes ---")
    for collection_name in ["users", "user_providers", "refresh_tokens"]:
        collection = db[collection_name]
        indexes = list(collection.list_indexes())
        print(f"\n{collection_name}:")
        for idx in indexes:
            print(f"   - {idx['name']}: {idx['key']}")
    
    return True


if __name__ == "__main__":
    setup_auth_indexes()
