"""Tests for MongoDBStorage vector database."""
import pytest
from unittest.mock import patch, MagicMock


class TestMongoDBStorage:
    """Tests for MongoDBStorage class."""
    
    @pytest.fixture
    def mock_mongo_client(self):
        """Mock the MongoDB client."""
        with patch("vector_db.MongoClient") as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            yield mock_client, mock_collection
    
    @pytest.fixture
    def mock_env(self):
        """Mock environment variables."""
        with patch.dict("os.environ", {"MONGODB_URI": "mongodb://test:27017"}):
            yield
    
    def test_storage_init_without_uri_raises(self):
        """Should raise ValueError if MONGODB_URI not set."""
        import importlib
        import vector_db
        
        # Reload module with empty environment
        with patch.dict("os.environ", {"MONGODB_URI": ""}, clear=False):
            with pytest.raises(ValueError, match="MONGODB_URI"):
                # Need to instantiate with environment check
                from vector_db import MongoDBStorage
                # Force the __init__ check by clearing existing env
                original_env = vector_db.os.environ.get("MONGODB_URI")
                vector_db.os.environ["MONGODB_URI"] = ""
                try:
                    MongoDBStorage()
                finally:
                    if original_env:
                        vector_db.os.environ["MONGODB_URI"] = original_env
    
    def test_storage_init_with_uri(self, mock_mongo_client, mock_env):
        """Should initialize properly with valid URI."""
        from vector_db import MongoDBStorage
        storage = MongoDBStorage()
        assert storage is not None
    
    def test_upsert_creates_documents(self, mock_mongo_client, mock_env):
        """Should bulk upsert documents with embeddings."""
        mock_client, mock_collection = mock_mongo_client
        from vector_db import MongoDBStorage
        
        storage = MongoDBStorage()
        storage.upsert(
            ids=["id1", "id2"],
            vectors=[[0.1, 0.2], [0.3, 0.4]],
            payloads=[{"text": "chunk1"}, {"text": "chunk2"}]
        )
        
        mock_collection.bulk_write.assert_called_once()
    
    def test_upsert_with_scope(self, mock_mongo_client, mock_env):
        """Should include scope_type and scope_id in documents."""
        mock_client, mock_collection = mock_mongo_client
        from vector_db import MongoDBStorage
        
        storage = MongoDBStorage()
        storage.upsert(
            ids=["id1"],
            vectors=[[0.1, 0.2]],
            payloads=[{"text": "chunk1"}],
            scope_type="chat",
            scope_id="chat_123"
        )
        
        bulk_write_call = mock_collection.bulk_write.call_args
        operations = bulk_write_call[0][0]
        
        # Verify the update operation includes scope fields
        update_doc = operations[0]._doc
        assert update_doc["$set"]["scope_type"] == "chat"
        assert update_doc["$set"]["scope_id"] == "chat_123"
    
    def test_search_returns_structured_result(self, mock_mongo_client, mock_env):
        """Should return contexts, sources, and scores."""
        mock_client, mock_collection = mock_mongo_client
        from vector_db import MongoDBStorage
        
        mock_collection.aggregate.return_value = iter([
            {"text": "result1", "source": "doc1.pdf", "page": 1, "score": 0.9},
            {"text": "result2", "source": "doc2.pdf", "page": 2, "score": 0.8}
        ])
        
        storage = MongoDBStorage()
        result = storage.search([0.1, 0.2], top_k=5)
        
        assert len(result["contexts"]) == 2
        assert "doc1.pdf, page 1" in result["sources"][0]
        assert result["scores"][0] == 0.9
    
    def test_search_with_scope_filter(self, mock_mongo_client, mock_env):
        """Should add filter when scope params provided."""
        mock_client, mock_collection = mock_mongo_client
        from vector_db import MongoDBStorage
        
        mock_collection.aggregate.return_value = iter([])
        
        storage = MongoDBStorage()
        storage.search([0.1, 0.2], top_k=5, scope_type="chat", scope_id="chat_123")
        
        # Verify aggregate was called with filter
        call_args = mock_collection.aggregate.call_args
        pipeline = call_args[0][0]
        vector_search = pipeline[0]["$vectorSearch"]
        
        assert "filter" in vector_search
        assert vector_search["filter"]["scope_type"] == "chat"
    
    def test_search_without_filter(self, mock_mongo_client, mock_env):
        """Should not add filter when scope params are None."""
        mock_client, mock_collection = mock_mongo_client
        from vector_db import MongoDBStorage
        
        mock_collection.aggregate.return_value = iter([])
        
        storage = MongoDBStorage()
        storage.search([0.1, 0.2], top_k=5)
        
        call_args = mock_collection.aggregate.call_args
        pipeline = call_args[0][0]
        vector_search = pipeline[0]["$vectorSearch"]
        
        assert "filter" not in vector_search
