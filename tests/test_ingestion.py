"""Unit tests for M2: Ingestion Pipeline.

Tests for chunk_service and chunk_search modules.
"""
import pytest
import uuid
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from models import IngestPdfEventData, DocumentStatus, ScopeType, Chunk
from chunk_service import generate_chunk_id, save_chunks, delete_chunks, update_document_status


class TestChunkIdGeneration:
    """Tests for deterministic chunk ID generation."""
    
    def test_generate_chunk_id_is_deterministic(self):
        """Test same inputs produce same ID."""
        doc_id = "doc_123"
        chunk_index = 0
        
        id1 = generate_chunk_id(doc_id, chunk_index)
        id2 = generate_chunk_id(doc_id, chunk_index)
        
        assert id1 == id2
    
    def test_generate_chunk_id_varies_with_document(self):
        """Test different documents produce different IDs."""
        id1 = generate_chunk_id("doc_123", 0)
        id2 = generate_chunk_id("doc_456", 0)
        
        assert id1 != id2
    
    def test_generate_chunk_id_varies_with_index(self):
        """Test different indexes produce different IDs."""
        id1 = generate_chunk_id("doc_123", 0)
        id2 = generate_chunk_id("doc_123", 1)
        
        assert id1 != id2
    
    def test_generate_chunk_id_is_valid_uuid(self):
        """Test generated ID is valid UUID."""
        chunk_id = generate_chunk_id("doc_123", 0)
        
        # Should not raise
        uuid_obj = uuid.UUID(chunk_id)
        assert str(uuid_obj) == chunk_id


class TestIngestPdfEventDataModel:
    """Tests for IngestPdfEventData model."""
    
    def test_model_includes_document_id(self):
        """Test document_id field exists in model."""
        data = IngestPdfEventData(
            pdf_path="documents/chat/123/test.pdf",
            filename="test.pdf",
            scope_type=ScopeType.CHAT,
            scope_id="chat_123",
            document_id="doc_abc"
        )
        
        assert data.document_id == "doc_abc"
    
    def test_model_requires_document_id(self):
        """Test document_id is required."""
        with pytest.raises(ValidationError):
            IngestPdfEventData(
                pdf_path="documents/chat/123/test.pdf",
                filename="test.pdf",
                scope_type=ScopeType.CHAT,
                scope_id="chat_123"
                # Missing document_id
            )
    
    def test_pdf_path_validation(self):
        """Test pdf_path must end with .pdf."""
        with pytest.raises(ValidationError):
            IngestPdfEventData(
                pdf_path="documents/test.txt",  # Not PDF
                filename="test.txt",
                scope_type=ScopeType.CHAT,
                scope_id="chat_123",
                document_id="doc_abc"
            )


class TestChunkService:
    """Tests for chunk_service functions."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock MongoDB database."""
        with patch("chunk_service.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            
            # Mock bulk_write result
            mock_bulk_result = MagicMock()
            mock_bulk_result.upserted_count = 5
            mock_bulk_result.modified_count = 0
            mock_db.chunks.bulk_write.return_value = mock_bulk_result
            
            yield mock_db
    
    def test_save_chunks_empty_list(self, mock_db):
        """Test save_chunks handles empty list."""
        result = save_chunks("doc_123", [], [])
        assert result == 0
    
    def test_save_chunks_creates_bulk_operations(self, mock_db):
        """Test save_chunks creates bulk upsert operations."""
        chunks_data = [
            {"text": "Chunk 1", "page_number": 1, "chunk_index": 0},
            {"text": "Chunk 2", "page_number": 1, "chunk_index": 1}
        ]
        embeddings = [[0.1] * 1536, [0.2] * 1536]
        
        with patch("chunk_service.get_db", return_value=mock_db):
            save_chunks("doc_123", chunks_data, embeddings)
        
        mock_db.chunks.bulk_write.assert_called_once()
    
    def test_delete_chunks(self, mock_db):
        """Test delete_chunks removes all document chunks."""
        mock_db.chunks.delete_many.return_value = MagicMock(deleted_count=10)
        
        with patch("chunk_service.get_db", return_value=mock_db):
            result = delete_chunks("doc_123")
        
        mock_db.chunks.delete_many.assert_called_once_with({"document_id": "doc_123"})
        assert result == 10
    
    def test_update_document_status(self, mock_db):
        """Test update_document_status updates correct field."""
        mock_db.documents.update_one.return_value = MagicMock(modified_count=1)
        
        with patch("chunk_service.get_db", return_value=mock_db):
            result = update_document_status("doc_123", DocumentStatus.READY)
        
        mock_db.documents.update_one.assert_called_once_with(
            {"id": "doc_123"},
            {"$set": {"status": "ready"}}
        )
        assert result is True


class TestChunkSearch:
    """Tests for chunk_search module."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock MongoDB database."""
        with patch("chunk_search.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            yield mock_db
    
    def test_get_document_ids_for_chat_scope(self, mock_db):
        """Test getting document IDs for a chat scope."""
        from chunk_search import get_document_ids_for_scope
        
        mock_db.document_scopes.find.return_value = [
            {"document_id": "doc_1"},
            {"document_id": "doc_2"}
        ]
        
        with patch("chunk_search.get_db", return_value=mock_db):
            doc_ids = get_document_ids_for_scope("chat", "chat_123")
        
        assert len(doc_ids) == 2
        assert "doc_1" in doc_ids
        assert "doc_2" in doc_ids
    
    def test_get_document_ids_for_project_scope(self, mock_db):
        """Test getting document IDs for a project scope."""
        from chunk_search import get_document_ids_for_scope
        
        mock_db.document_scopes.find.return_value = [
            {"document_id": "doc_project"}
        ]
        
        with patch("chunk_search.get_db", return_value=mock_db):
            doc_ids = get_document_ids_for_scope("project", "proj_123")
        
        assert doc_ids == ["doc_project"]
    
    def test_search_chunks_empty_document_ids(self, mock_db):
        """Test search returns empty when no document IDs."""
        from chunk_search import search_chunks
        
        result = search_chunks([0.1] * 1536, [], top_k=5)
        
        assert result == {"contexts": [], "sources": [], "scores": []}
    
    def test_search_for_scope_integrates_functions(self, mock_db):
        """Test search_for_scope combines ID lookup and search."""
        from chunk_search import search_for_scope
        
        mock_db.document_scopes.find.return_value = [{"document_id": "doc_1"}]
        mock_db.chunks.aggregate.return_value = iter([
            {"text": "Result text", "page_number": 1, "score": 0.9, "filename": "test.pdf"}
        ])
        
        with patch("chunk_search.get_db", return_value=mock_db):
            result = search_for_scope([0.1] * 1536, "chat", "chat_123")
        
        assert len(result["contexts"]) == 1
        assert "Result text" in result["contexts"][0]


class TestDocumentStatusTransitions:
    """Tests for document status lifecycle."""
    
    def test_status_pending_to_ready(self):
        """Test valid status transition."""
        assert DocumentStatus.PENDING.value == "pending"
        assert DocumentStatus.READY.value == "ready"
    
    def test_all_statuses_exist(self):
        """Test all expected statuses exist."""
        assert hasattr(DocumentStatus, "PENDING")
        assert hasattr(DocumentStatus, "READY")
        assert hasattr(DocumentStatus, "DELETING")


class TestChunkModel:
    """Additional tests for Chunk model."""
    
    def test_chunk_with_all_fields(self):
        """Test chunk creation with all fields."""
        chunk = Chunk(
            id="chunk_123",
            document_id="doc_456",
            chunk_index=0,
            page_number=1,
            text="Sample text",
            embedding=[0.1] * 1536
        )
        
        assert chunk.document_id == "doc_456"
        assert chunk.chunk_index == 0
        assert len(chunk.embedding) == 1536
    
    def test_chunk_text_cannot_be_empty(self):
        """Test chunk text validation."""
        with pytest.raises(ValidationError):
            Chunk(
                document_id="doc_123",
                chunk_index=0,
                page_number=1,
                text=""  # Empty
            )
