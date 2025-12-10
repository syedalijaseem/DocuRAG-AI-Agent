"""Quality tests for M2: Ingestion Pipeline.

Comprehensive tests covering the 9 quality aspects for ingestion.
"""
import pytest
import hashlib
import time
from unittest.mock import patch, MagicMock

from chunk_service import generate_chunk_id, save_chunks, delete_chunks, update_document_status
from chunk_search import get_document_ids_for_scope, search_for_scope
from models import DocumentStatus, ScopeType, IngestPdfEventData


class TestSecurityIngestion:
    """Security-related tests for ingestion."""
    
    def test_pdf_path_rejects_null_bytes(self):
        """Test pdf_path validation rejects null bytes."""
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            IngestPdfEventData(
                pdf_path="documents/\x00malicious.pdf",
                filename="test.pdf",
                scope_type=ScopeType.CHAT,
                scope_id="chat_123",
                document_id="doc_123"
            )
    
    def test_pdf_path_rejects_path_traversal(self):
        """Test pdf_path validation rejects path traversal."""
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            IngestPdfEventData(
                pdf_path="../../../etc/passwd.pdf",
                filename="test.pdf",
                scope_type=ScopeType.CHAT,
                scope_id="chat_123",
                document_id="doc_123"
            )
    
    def test_document_id_is_required(self):
        """Test document_id is required for chunk linking."""
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            IngestPdfEventData(
                pdf_path="documents/test.pdf",
                filename="test.pdf",
                scope_type=ScopeType.CHAT,
                scope_id="chat_123"
                # Missing document_id
            )


class TestRobustnessIngestion:
    """Robustness tests for ingestion."""
    
    def test_chunk_id_generation_handles_special_characters(self):
        """Test chunk ID generation with special chars in document_id."""
        doc_id = "doc_special!@#$%^&*()"
        chunk_id = generate_chunk_id(doc_id, 0)
        
        # Should produce valid UUID
        import uuid
        uuid.UUID(chunk_id)  # Should not raise
    
    def test_save_chunks_handles_empty_list(self):
        """Test save_chunks gracefully handles empty list."""
        result = save_chunks("doc_123", [], [])
        assert result == 0
    
    @patch("chunk_search.get_db")
    def test_search_handles_no_document_ids(self, mock_get_db):
        """Test search returns empty when no documents in scope."""
        mock_db = MagicMock()
        mock_db.document_scopes.find.return_value = []
        mock_get_db.return_value = mock_db
        
        doc_ids = get_document_ids_for_scope("chat", "nonexistent")
        assert doc_ids == []


class TestScalabilityIngestion:
    """Scalability tests for ingestion."""
    
    def test_chunk_id_generation_is_fast(self):
        """Test chunk ID generation is performant."""
        start = time.time()
        for i in range(1000):
            generate_chunk_id("doc_123", i)
        elapsed = time.time() - start
        
        assert elapsed < 0.5, f"1000 chunk IDs took {elapsed:.2f}s, expected < 0.5s"
    
    @patch("chunk_service.get_db")
    def test_save_chunks_uses_bulk_operations(self, mock_get_db):
        """Test save_chunks uses bulk write for efficiency."""
        mock_db = MagicMock()
        mock_bulk_result = MagicMock()
        mock_bulk_result.upserted_count = 10
        mock_bulk_result.modified_count = 0
        mock_db.chunks.bulk_write.return_value = mock_bulk_result
        mock_get_db.return_value = mock_db
        
        chunks_data = [
            {"text": f"Chunk {i}", "page_number": 1, "chunk_index": i}
            for i in range(10)
        ]
        embeddings = [[0.1] * 1536 for _ in range(10)]
        
        save_chunks("doc_123", chunks_data, embeddings)
        
        # Should call bulk_write once, not 10 individual inserts
        mock_db.chunks.bulk_write.assert_called_once()


class TestReliabilityIngestion:
    """Reliability tests for ingestion."""
    
    def test_chunk_id_is_deterministic(self):
        """Test same inputs always produce same chunk ID."""
        id1 = generate_chunk_id("doc_abc", 5)
        id2 = generate_chunk_id("doc_abc", 5)
        
        assert id1 == id2
    
    def test_chunk_id_varies_with_inputs(self):
        """Test different inputs produce different IDs."""
        ids = set()
        for doc in ["doc_1", "doc_2", "doc_3"]:
            for idx in range(10):
                ids.add(generate_chunk_id(doc, idx))
        
        assert len(ids) == 30, "Should have 30 unique IDs"


class TestEfficiencyIngestion:
    """Efficiency tests for ingestion."""
    
    def test_embedding_dimension_is_1536(self):
        """Test embeddings use optimal 1536 dimensions."""
        # This is validated by Chunk model
        from models import Chunk
        from pydantic import ValidationError
        
        # Valid 1536 dims
        chunk = Chunk(
            document_id="doc_1",
            chunk_index=0,
            page_number=1,
            text="Test",
            embedding=[0.1] * 1536
        )
        assert len(chunk.embedding) == 1536
    
    def test_document_status_enum_is_string_based(self):
        """Test status enum serializes to strings for MongoDB."""
        assert DocumentStatus.PENDING.value == "pending"
        assert DocumentStatus.READY.value == "ready"
        assert DocumentStatus.DELETING.value == "deleting"


class TestOptimizationIngestion:
    """Optimization tests for ingestion."""
    
    @patch("chunk_service.get_db")
    def test_update_status_uses_atomic_update(self, mock_get_db):
        """Test status update uses atomic MongoDB update."""
        mock_db = MagicMock()
        mock_db.documents.update_one.return_value = MagicMock(modified_count=1)
        mock_get_db.return_value = mock_db
        
        update_document_status("doc_123", DocumentStatus.READY)
        
        mock_db.documents.update_one.assert_called_once_with(
            {"id": "doc_123"},
            {"$set": {"status": "ready"}}
        )


class TestBestPracticesIngestion:
    """Best practices tests for ingestion."""
    
    def test_chunk_service_has_docstrings(self):
        """Test chunk_service functions have docstrings."""
        assert generate_chunk_id.__doc__ is not None
        assert save_chunks.__doc__ is not None
        assert delete_chunks.__doc__ is not None
    
    def test_chunk_search_has_docstrings(self):
        """Test chunk_search functions have docstrings."""
        assert get_document_ids_for_scope.__doc__ is not None
        assert search_for_scope.__doc__ is not None
    
    def test_ingest_event_data_uses_pydantic(self):
        """Test IngestPdfEventData is Pydantic model."""
        from pydantic import BaseModel
        assert issubclass(IngestPdfEventData, BaseModel)
