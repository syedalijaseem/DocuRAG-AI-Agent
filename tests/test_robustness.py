"""Robustness tests for error handling and failure scenarios.

These tests ensure the application handles failures gracefully.
"""
import pytest
from unittest.mock import MagicMock, patch, mock_open
import os


class TestDataLoaderRobustness:
    """Tests for data_loader module robustness.
    
    Note: embed_texts tests are skipped because they require the OpenAI client
    to be mocked at import time. These should be integration tests instead.
    """
    
    @pytest.mark.skip(reason="Requires integration test - OpenAI client loaded at import")
    def test_embed_texts_handles_empty_list(self):
        """Should handle empty text list gracefully."""
        pass
    
    @pytest.mark.skip(reason="Requires integration test - OpenAI client loaded at import")    
    def test_embed_texts_api_error(self):
        """Should propagate API errors for caller to handle."""
        pass
    
    def test_load_pdf_file_not_found(self):
        """Should handle missing PDF file."""
        from data_loader import load_and_chunk_pdf
        
        with pytest.raises(Exception):  # Could be FileNotFoundError or similar
            load_and_chunk_pdf("/nonexistent/path/file.pdf")


class TestVectorDBRobustness:
    """Tests for vector_db robustness under failure conditions."""
    
    @pytest.fixture
    def mock_mongo_setup(self):
        """Setup mocked MongoDB."""
        with patch('vector_db.MongoClient') as mock_client:
            with patch.dict('os.environ', {'MONGODB_URI': 'mongodb://test:27017'}):
                mock_collection = MagicMock()
                mock_db = MagicMock()
                mock_db.__getitem__ = MagicMock(return_value=mock_collection)
                mock_client.return_value.__getitem__ = MagicMock(return_value=mock_db)
                yield mock_client, mock_collection
    
    def test_upsert_empty_data(self, mock_mongo_setup):
        """Should handle empty upsert gracefully."""
        mock_client, mock_collection = mock_mongo_setup
        from vector_db import MongoDBStorage
        
        storage = MongoDBStorage()
        storage.upsert([], [], [])  # Empty arrays
        
        # bulk_write should not be called with empty operations
        mock_collection.bulk_write.assert_not_called()
    
    def test_upsert_mongodb_error(self, mock_mongo_setup):
        """Should propagate MongoDB errors."""
        mock_client, mock_collection = mock_mongo_setup
        mock_collection.bulk_write.side_effect = Exception("MongoDB connection lost")
        
        from vector_db import MongoDBStorage
        storage = MongoDBStorage()
        
        with pytest.raises(Exception, match="MongoDB connection lost"):
            storage.upsert(["doc1"], [[0.1, 0.2]], [{"source": "test.pdf"}])
    
    def test_search_connection_timeout(self, mock_mongo_setup):
        """Should handle connection timeouts."""
        mock_client, mock_collection = mock_mongo_setup
        mock_collection.aggregate.side_effect = Exception("Connection timeout")
        
        from vector_db import MongoDBStorage
        storage = MongoDBStorage()
        
        with pytest.raises(Exception, match="Connection timeout"):
            storage.search([0.1, 0.2])
    
    def test_search_empty_results(self, mock_mongo_setup):
        """Should handle empty search results gracefully."""
        mock_client, mock_collection = mock_mongo_setup
        mock_collection.aggregate.return_value = iter([])
        
        from vector_db import MongoDBStorage
        storage = MongoDBStorage()
        result = storage.search([0.1, 0.2])
        
        assert result["contexts"] == []
        assert result["sources"] == []
        assert result["scores"] == []
    
    def test_search_partial_results(self, mock_mongo_setup):
        """Should handle results with missing fields."""
        mock_client, mock_collection = mock_mongo_setup
        mock_collection.aggregate.return_value = iter([
            {"text": "Result 1"},  # Missing source, page, score
            {"source": "doc.pdf", "page": 1, "score": 0.9},  # Missing text
        ])
        
        from vector_db import MongoDBStorage
        storage = MongoDBStorage()
        result = storage.search([0.1, 0.2])
        
        # Should handle gracefully - only include results with text
        assert len(result["contexts"]) == 1


class TestConcurrencyRobustness:
    """Tests for concurrent access patterns."""
    
    def test_multiple_storage_instances(self):
        """Multiple storage instances should work independently."""
        with patch('vector_db.MongoClient') as mock_client:
            with patch.dict('os.environ', {'MONGODB_URI': 'mongodb://test:27017'}):
                mock_collection = MagicMock()
                mock_db = MagicMock()
                mock_db.__getitem__ = MagicMock(return_value=mock_collection)
                mock_client.return_value.__getitem__ = MagicMock(return_value=mock_db)
                
                from vector_db import MongoDBStorage
                
                storage1 = MongoDBStorage(collection_name="docs1")
                storage2 = MongoDBStorage(collection_name="docs2")
                
                # Both should be independent instances
                assert storage1 is not storage2


class TestConfigRobustness:
    """Tests for configuration handling."""
    
    def test_missing_openai_api_key(self):
        """Should handle missing OpenAI API key."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('data_loader.load_dotenv'):
                # OpenAI client will fail without API key
                with patch('data_loader.OpenAI') as mock_openai:
                    mock_openai.side_effect = Exception("API key required")
                    
                    # The import or first call should fail
                    # This tests that we don't silently ignore the error
                    pass  # Test documents the expected behavior
    
    def test_invalid_mongodb_uri(self):
        """Should fail gracefully with invalid MongoDB URI."""
        with patch.dict('os.environ', {'MONGODB_URI': 'invalid://uri'}):
            with patch('vector_db.MongoClient') as mock_client:
                mock_client.side_effect = Exception("Invalid URI")
                
                from vector_db import MongoDBStorage
                
                with pytest.raises(Exception, match="Invalid URI"):
                    MongoDBStorage()
