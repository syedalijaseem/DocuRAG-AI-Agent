"""Integration tests for the RAG application.

These tests are designed to run against real services in a CI/CD environment.
They are skipped by default and should be enabled when:
- INTEGRATION_TESTS=true environment variable is set
- MongoDB test instance is available
- OpenAI API key is available

Run with: INTEGRATION_TESTS=true pytest tests/test_integration.py -v
"""
import pytest
import os
from unittest.mock import patch

# Skip all tests in this module unless INTEGRATION_TESTS is set
pytestmark = pytest.mark.skipif(
    os.getenv("INTEGRATION_TESTS", "").lower() != "true",
    reason="Integration tests disabled. Set INTEGRATION_TESTS=true to enable."
)


@pytest.fixture(scope="module")
def mongodb_client():
    """Create a MongoDB client for testing."""
    from pymongo import MongoClient
    
    uri = os.getenv("MONGODB_URI")
    if not uri:
        pytest.skip("MONGODB_URI not set")
    
    client = MongoClient(uri)
    yield client
    client.close()


@pytest.fixture(scope="module")
def test_collection(mongodb_client):
    """Create a test collection that gets cleaned up."""
    db = mongodb_client["rag_db_test"]
    collection = db["documents_test"]
    
    yield collection
    
    # Cleanup
    collection.drop()


class TestMongoDBIntegration:
    """Integration tests for MongoDB operations."""
    
    def test_mongodb_connection(self, mongodb_client):
        """Should connect to MongoDB successfully."""
        # Ping the server
        result = mongodb_client.admin.command('ping')
        assert result['ok'] == 1.0
    
    def test_upsert_and_retrieve(self, test_collection):
        """Should upsert and retrieve documents."""
        # Insert a test document
        test_collection.insert_one({
            "doc_id": "test_doc_1",
            "text": "This is a test document",
            "source": "test.pdf",
            "page": 1,
            "workspace_id": "ws_test"
        })
        
        # Retrieve it
        doc = test_collection.find_one({"doc_id": "test_doc_1"})
        assert doc is not None
        assert doc["text"] == "This is a test document"
    
    def test_workspace_filtering(self, test_collection):
        """Should filter documents by workspace_id."""
        # Insert documents in different workspaces
        test_collection.insert_many([
            {"doc_id": "ws1_doc", "workspace_id": "ws_1", "text": "Doc in WS1"},
            {"doc_id": "ws2_doc", "workspace_id": "ws_2", "text": "Doc in WS2"},
        ])
        
        # Filter by workspace
        ws1_docs = list(test_collection.find({"workspace_id": "ws_1"}))
        assert len(ws1_docs) >= 1
        assert all(d["workspace_id"] == "ws_1" for d in ws1_docs)


@pytest.fixture(scope="module")
def openai_available():
    """Check if OpenAI API is available."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")
    return True


class TestEmbeddingIntegration:
    """Integration tests for embedding operations."""
    
    def test_embed_single_text(self, openai_available):
        """Should embed a single text successfully."""
        from data_loader import embed_texts
        
        texts = ["Hello, world!"]
        embeddings = embed_texts(texts)
        
        assert len(embeddings) == 1
        assert len(embeddings[0]) == 3072  # text-embedding-3-large
    
    def test_embed_multiple_texts(self, openai_available):
        """Should embed multiple texts efficiently."""
        from data_loader import embed_texts
        
        texts = ["First text", "Second text", "Third text"]
        embeddings = embed_texts(texts)
        
        assert len(embeddings) == 3
        # Each embedding should be different
        assert embeddings[0] != embeddings[1]


class TestVectorSearchIntegration:
    """Integration tests for vector search operations."""
    
    @pytest.fixture
    def storage(self):
        """Create a MongoDBStorage instance for testing."""
        from vector_db import MongoDBStorage
        return MongoDBStorage(
            collection_name="documents_integration_test",
            db_name="rag_db_test"
        )
    
    def test_full_upsert_and_search_flow(self, storage, openai_available):
        """Should upsert documents and search them."""
        from data_loader import embed_texts
        
        # Create test documents
        texts = [
            "Machine learning is a subset of artificial intelligence.",
            "Deep learning uses neural networks with many layers.",
            "Natural language processing deals with text data."
        ]
        
        embeddings = embed_texts(texts)
        ids = ["int_test_1", "int_test_2", "int_test_3"]
        payloads = [
            {"source": "ml.pdf", "text": texts[0], "page": 1},
            {"source": "dl.pdf", "text": texts[1], "page": 1},
            {"source": "nlp.pdf", "text": texts[2], "page": 1},
        ]
        
        # Upsert
        storage.upsert(ids, embeddings, payloads, workspace_id="ws_integration_test")
        
        # Search
        query_embedding = embed_texts(["What is machine learning?"])[0]
        results = storage.search(
            query_embedding, 
            top_k=2,
            workspace_id="ws_integration_test"
        )
        
        assert len(results["contexts"]) <= 2
        # The ML document should be in results
        assert any("machine learning" in ctx.lower() for ctx in results["contexts"])


class TestEndToEndFlow:
    """End-to-end tests for the complete RAG flow."""
    
    @pytest.mark.skip(reason="Requires full Inngest setup - run manually")
    def test_full_rag_pipeline(self):
        """Test the complete RAG pipeline from ingest to query."""
        # This test would:
        # 1. Ingest a test PDF
        # 2. Wait for ingestion to complete
        # 3. Query the document
        # 4. Verify the response
        pass
    
    @pytest.mark.skip(reason="Requires Streamlit test harness - run manually")
    def test_streamlit_upload_and_query(self):
        """Test Streamlit UI flow with browser automation."""
        # This test would use Playwright/Selenium to:
        # 1. Load the Streamlit app
        # 2. Upload a PDF
        # 3. Wait for ingestion
        # 4. Submit a query
        # 5. Verify the response appears
        pass
