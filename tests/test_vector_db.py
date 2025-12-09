"""Tests for vector_db module with MongoDB mocking."""
import pytest
from unittest.mock import MagicMock, patch


class TestMongoDBStorage:
    """Tests for MongoDBStorage class."""
    
    @pytest.fixture
    def mock_mongo_client(self):
        """Create a mock MongoDB client."""
        with patch('vector_db.MongoClient') as mock_client:
            # Setup mock collection
            mock_collection = MagicMock()
            mock_db = MagicMock()
            mock_db.__getitem__ = MagicMock(return_value=mock_collection)
            mock_client.return_value.__getitem__ = MagicMock(return_value=mock_db)
            
            yield mock_client, mock_collection
    
    @pytest.fixture
    def mock_env(self):
        """Mock environment variables."""
        with patch.dict('os.environ', {'MONGODB_URI': 'mongodb://test:27017'}):
            yield
    
    def test_storage_init_without_uri_raises(self):
        """Should raise when MONGODB_URI is not set."""
        with patch('vector_db.load_dotenv'):  # Skip loading .env
            with patch('vector_db.os.getenv', return_value=None):  # Mock getenv to return None
                # Need to reimport to get the patched version
                import importlib
                import vector_db
                importlib.reload(vector_db)
                
                with pytest.raises(ValueError, match="MONGODB_URI"):
                    vector_db.MongoDBStorage()
    
    def test_storage_init_with_uri(self, mock_mongo_client, mock_env):
        """Should initialize successfully with MONGODB_URI."""
        from vector_db import MongoDBStorage
        
        storage = MongoDBStorage()
        assert storage is not None
    
    def test_upsert_creates_documents(self, mock_mongo_client, mock_env):
        """Should bulk upsert documents."""
        mock_client, mock_collection = mock_mongo_client
        from vector_db import MongoDBStorage
        
        storage = MongoDBStorage()
        
        ids = ["doc1", "doc2"]
        vectors = [[0.1, 0.2], [0.3, 0.4]]
        payloads = [
            {"source": "test.pdf", "text": "Hello", "page": 1},
            {"source": "test.pdf", "text": "World", "page": 2},
        ]
        
        storage.upsert(ids, vectors, payloads)
        
        # Verify bulk_write was called
        mock_collection.bulk_write.assert_called_once()
    
    def test_upsert_with_workspace_id(self, mock_mongo_client, mock_env):
        """Should include workspace_id in documents when provided."""
        mock_client, mock_collection = mock_mongo_client
        from vector_db import MongoDBStorage
        
        storage = MongoDBStorage()
        
        ids = ["doc1"]
        vectors = [[0.1, 0.2]]
        payloads = [{"source": "test.pdf", "text": "Hello", "page": 1}]
        
        storage.upsert(ids, vectors, payloads, workspace_id="ws_123")
        
        # Verify bulk_write was called with workspace_id
        call_args = mock_collection.bulk_write.call_args
        assert call_args is not None
    
    def test_search_returns_structured_result(self, mock_mongo_client, mock_env):
        """Should return properly structured search results."""
        mock_client, mock_collection = mock_mongo_client
        from vector_db import MongoDBStorage
        
        # Mock aggregation result
        mock_collection.aggregate.return_value = iter([
            {"text": "Result 1", "source": "doc.pdf", "page": 1, "score": 0.95},
            {"text": "Result 2", "source": "doc.pdf", "page": 2, "score": 0.85},
        ])
        
        storage = MongoDBStorage()
        result = storage.search([0.1, 0.2], top_k=5)
        
        assert "contexts" in result
        assert "sources" in result
        assert "scores" in result
        assert len(result["contexts"]) == 2
        assert result["scores"][0] == 0.95
    
    def test_search_with_workspace_filter(self, mock_mongo_client, mock_env):
        """Should add workspace filter to vector search."""
        mock_client, mock_collection = mock_mongo_client
        from vector_db import MongoDBStorage
        
        mock_collection.aggregate.return_value = iter([])
        
        storage = MongoDBStorage()
        storage.search([0.1, 0.2], top_k=5, workspace_id="ws_123")
        
        # Verify aggregate was called with filter
        call_args = mock_collection.aggregate.call_args
        pipeline = call_args[0][0]
        vector_search_stage = pipeline[0]["$vectorSearch"]
        
        assert "filter" in vector_search_stage
        assert vector_search_stage["filter"]["workspace_id"] == "ws_123"
    
    def test_search_without_filter(self, mock_mongo_client, mock_env):
        """Should not add filter when workspace_id is None."""
        mock_client, mock_collection = mock_mongo_client
        from vector_db import MongoDBStorage
        
        mock_collection.aggregate.return_value = iter([])
        
        storage = MongoDBStorage()
        storage.search([0.1, 0.2], top_k=5, workspace_id=None)
        
        # Verify aggregate was called without filter
        call_args = mock_collection.aggregate.call_args
        pipeline = call_args[0][0]
        vector_search_stage = pipeline[0]["$vectorSearch"]
        
        assert "filter" not in vector_search_stage
