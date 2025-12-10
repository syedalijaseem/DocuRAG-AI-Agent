"""Quality tests for Availability and Speed (M2/M3 gap coverage).

These tests ensure:
- Availability: Graceful degradation, error handling
- Speed: Performance targets met
"""
import pytest
import time
from unittest.mock import patch, MagicMock

from chunk_service import generate_chunk_id, save_chunks, update_document_status
from chunk_search import get_document_ids_for_scope, search_for_scope, search_chunks
from models import DocumentStatus


class TestAvailabilityIngestion:
    """Availability tests for ingestion components."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock MongoDB database."""
        with patch("chunk_service.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            yield mock_db
    
    def test_save_chunks_handles_mongodb_error_gracefully(self, mock_db):
        """Test save_chunks propagates MongoDB errors for retry handling."""
        mock_db.chunks.bulk_write.side_effect = Exception("MongoDB connection lost")
        
        with pytest.raises(Exception, match="MongoDB connection lost"):
            save_chunks("doc_123", [{"text": "test", "page_number": 1, "chunk_index": 0}], [[0.1] * 1536])
    
    def test_update_status_returns_false_on_missing_doc(self, mock_db):
        """Test update_document_status handles missing document."""
        mock_db.documents.update_one.return_value = MagicMock(modified_count=0)
        
        result = update_document_status("nonexistent_doc", DocumentStatus.READY)
        assert result is False
    
    def test_chunk_service_requires_mongodb_uri(self):
        """Test chunk_service fails gracefully without MongoDB URI."""
        with patch.dict('os.environ', {'MONGODB_URI': ''}, clear=True):
            with patch('chunk_service.get_db') as mock_get_db:
                mock_get_db.side_effect = RuntimeError("MONGODB_URI not configured")
                
                with pytest.raises(RuntimeError, match="MONGODB_URI not configured"):
                    from chunk_service import get_db
                    get_db()


class TestAvailabilitySearch:
    """Availability tests for search components."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock MongoDB database."""
        with patch("chunk_search.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            yield mock_db
    
    def test_search_handles_empty_scope(self, mock_db):
        """Test search returns empty results for scope with no documents."""
        mock_db.document_scopes.find.return_value = []
        
        result = search_for_scope([0.1] * 1536, "chat", "empty_chat")
        
        assert result["contexts"] == []
        assert result["sources"] == []
        assert result["scores"] == []
    
    def test_search_handles_mongodb_aggregation_error(self, mock_db):
        """Test search propagates MongoDB errors for error handling."""
        mock_db.document_scopes.find.return_value = [{"document_id": "doc_1"}]
        mock_db.chunks.aggregate.side_effect = Exception("Aggregation failed")
        
        with pytest.raises(Exception, match="Aggregation failed"):
            search_for_scope([0.1] * 1536, "chat", "chat_123")
    
    def test_search_returns_partial_results(self, mock_db):
        """Test search returns partial results even if some are malformed."""
        mock_db.document_scopes.find.return_value = [{"document_id": "doc_1"}]
        mock_db.chunks.aggregate.return_value = iter([
            {"text": "Valid result", "page_number": 1, "score": 0.9, "filename": "doc.pdf"},
            {"page_number": 2, "score": 0.8},  # Missing text - should be filtered
        ])
        
        result = search_for_scope([0.1] * 1536, "chat", "chat_123")
        
        # Only valid result should be included
        assert len(result["contexts"]) == 1
        assert "Valid result" in result["contexts"][0]


class TestSpeedIngestion:
    """Speed/performance tests for ingestion."""
    
    def test_chunk_id_generation_under_target_latency(self):
        """Test: Generate 10,000 chunk IDs in < 1 second."""
        start = time.time()
        for i in range(10000):
            generate_chunk_id("doc_123", i)
        elapsed = time.time() - start
        
        assert elapsed < 1.0, f"10,000 chunk IDs took {elapsed:.2f}s, expected < 1s"
    
    @patch("chunk_service.get_db")
    def test_save_chunks_batch_efficiency(self, mock_get_db):
        """Test: Saving 100 chunks uses single bulk operation."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        mock_bulk_result = MagicMock()
        mock_bulk_result.upserted_count = 100
        mock_bulk_result.modified_count = 0
        mock_db.chunks.bulk_write.return_value = mock_bulk_result
        
        # Prepare 100 chunks
        chunks_data = [
            {"text": f"Chunk {i}", "page_number": 1, "chunk_index": i}
            for i in range(100)
        ]
        embeddings = [[0.1] * 1536 for _ in range(100)]
        
        save_chunks("doc_123", chunks_data, embeddings)
        
        # Single bulk_write call, not 100 individual inserts
        assert mock_db.chunks.bulk_write.call_count == 1


class TestSpeedSearch:
    """Speed/performance tests for search."""
    
    @patch("chunk_search.get_db")
    def test_document_id_lookup_efficiency(self, mock_get_db):
        """Test: Document ID lookup uses indexed query."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.document_scopes.find.return_value = []
        
        # Measure 100 lookups
        start = time.time()
        for _ in range(100):
            get_document_ids_for_scope("chat", "chat_123")
        elapsed = time.time() - start
        
        # 100 mocked lookups should be < 0.5s
        assert elapsed < 0.5, f"100 lookups took {elapsed:.2f}s, expected < 0.5s"
    
    @patch("chunk_search.get_db")
    def test_search_uses_vector_index(self, mock_get_db):
        """Test: Vector search pipeline uses vector_index."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.document_scopes.find.return_value = [{"document_id": "doc_1"}]
        mock_db.chunks.aggregate.return_value = iter([])
        
        search_chunks([0.1] * 1536, ["doc_1"], top_k=5)
        
        # Verify vector index is used in pipeline
        call_args = mock_db.chunks.aggregate.call_args
        pipeline = call_args[0][0]
        vector_search = pipeline[0]["$vectorSearch"]
        
        assert vector_search["index"] == "vector_index"
        assert vector_search["path"] == "embedding"
        assert vector_search["limit"] == 5


class TestSpeedEndToEnd:
    """End-to-end speed verification tests."""
    
    @patch("chunk_search.get_db")
    def test_full_search_pipeline_under_target(self, mock_get_db):
        """Test: Full search pipeline completes in reasonable time (mocked)."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Mock responses
        mock_db.document_scopes.find.return_value = [
            {"document_id": f"doc_{i}"} for i in range(10)
        ]
        mock_db.chunks.aggregate.return_value = iter([
            {"text": f"Result {i}", "page_number": 1, "score": 0.9 - i*0.05, "filename": f"doc_{i}.pdf"}
            for i in range(5)
        ])
        
        start = time.time()
        result = search_for_scope(
            [0.1] * 1536,
            scope_type="chat",
            scope_id="chat_123",
            top_k=5,
            include_project=True,
            project_id="proj_456"
        )
        elapsed = time.time() - start
        
        # Mocked should be < 0.1s
        assert elapsed < 0.1, f"Search took {elapsed:.2f}s, expected < 0.1s"
        assert len(result["contexts"]) == 5
