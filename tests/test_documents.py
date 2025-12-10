"""Unit tests for M1: Core Data Model.

Tests for Document, DocumentScope, and Chunk models.
"""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from models import (
    Document, DocumentScope, Chunk,
    DocumentStatus, ScopeType,
    generate_id
)


class TestDocumentModel:
    """Tests for the Document model."""
    
    def test_document_creation_valid(self):
        """Test creating a valid document."""
        doc = Document(
            filename="test.pdf",
            s3_key="documents/chat/123/test.pdf",
            checksum="sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            size_bytes=1024
        )
        
        assert doc.id.startswith("doc_")
        assert doc.filename == "test.pdf"
        assert doc.status == DocumentStatus.PENDING
        assert doc.size_bytes == 1024
        assert doc.uploaded_at is not None
    
    def test_document_status_default(self):
        """Test that default status is PENDING."""
        doc = Document(
            filename="test.pdf",
            s3_key="key",
            checksum="sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            size_bytes=100
        )
        assert doc.status == DocumentStatus.PENDING
    
    def test_document_status_values(self):
        """Test all valid status values."""
        for status in [DocumentStatus.PENDING, DocumentStatus.READY, DocumentStatus.DELETING]:
            doc = Document(
                filename="test.pdf",
                s3_key=f"key_{status.value}",
                checksum=f"sha256:{'a' * 64}",
                size_bytes=100,
                status=status
            )
            assert doc.status == status
    
    def test_checksum_validation_valid(self):
        """Test valid checksum format."""
        doc = Document(
            filename="test.pdf",
            s3_key="key",
            checksum="sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            size_bytes=100
        )
        assert doc.checksum.startswith("sha256:")
    
    def test_checksum_validation_missing_prefix(self):
        """Test checksum without sha256: prefix."""
        with pytest.raises(ValidationError) as exc_info:
            Document(
                filename="test.pdf",
                s3_key="key",
                checksum="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
                size_bytes=100
            )
        assert "Checksum must be prefixed with sha256:" in str(exc_info.value)
    
    def test_checksum_validation_wrong_length(self):
        """Test checksum with wrong length."""
        with pytest.raises(ValidationError) as exc_info:
            Document(
                filename="test.pdf",
                s3_key="key",
                checksum="sha256:abc123",  # Too short
                size_bytes=100
            )
        assert "64 hex characters" in str(exc_info.value)
    
    def test_checksum_validation_non_hex(self):
        """Test checksum with non-hex characters."""
        with pytest.raises(ValidationError) as exc_info:
            Document(
                filename="test.pdf",
                s3_key="key",
                checksum="sha256:xyz123" + "0" * 58,  # Contains xyz
                size_bytes=100
            )
        assert "hex characters" in str(exc_info.value)
    
    def test_filename_sanitization(self):
        """Test filename sanitization."""
        doc = Document(
            filename="  test.pdf  ",
            s3_key="key",
            checksum=f"sha256:{'a' * 64}",
            size_bytes=100
        )
        assert doc.filename == "test.pdf"
    
    def test_filename_path_traversal_blocked(self):
        """Test that path traversal is blocked."""
        doc = Document(
            filename="../../../etc/passwd.pdf",
            s3_key="key",
            checksum=f"sha256:{'a' * 64}",
            size_bytes=100
        )
        # Path traversal characters should be removed
        assert ".." not in doc.filename
        assert "/" not in doc.filename
    
    def test_filename_empty_rejected(self):
        """Test empty filename is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Document(
                filename="",
                s3_key="key",
                checksum=f"sha256:{'a' * 64}",
                size_bytes=100
            )
        assert "Filename cannot be empty" in str(exc_info.value)
    
    def test_size_bytes_non_negative(self):
        """Test size_bytes must be non-negative."""
        with pytest.raises(ValidationError):
            Document(
                filename="test.pdf",
                s3_key="key",
                checksum=f"sha256:{'a' * 64}",
                size_bytes=-1
            )


class TestDocumentScopeModel:
    """Tests for the DocumentScope model."""
    
    def test_document_scope_creation(self):
        """Test creating a valid document scope link."""
        scope = DocumentScope(
            document_id="doc_123",
            scope_type=ScopeType.CHAT,
            scope_id="chat_456"
        )
        
        assert scope.id.startswith("ds_")
        assert scope.document_id == "doc_123"
        assert scope.scope_type == ScopeType.CHAT
        assert scope.scope_id == "chat_456"
        assert scope.linked_at is not None
    
    def test_scope_type_chat(self):
        """Test chat scope type."""
        scope = DocumentScope(
            document_id="doc_1",
            scope_type=ScopeType.CHAT,
            scope_id="chat_1"
        )
        assert scope.scope_type == ScopeType.CHAT
        assert scope.scope_type.value == "chat"
    
    def test_scope_type_project(self):
        """Test project scope type."""
        scope = DocumentScope(
            document_id="doc_1",
            scope_type=ScopeType.PROJECT,
            scope_id="proj_1"
        )
        assert scope.scope_type == ScopeType.PROJECT
        assert scope.scope_type.value == "project"


class TestChunkModel:
    """Tests for the Chunk model."""
    
    def test_chunk_creation_valid(self):
        """Test creating a valid chunk."""
        chunk = Chunk(
            document_id="doc_123",
            chunk_index=0,
            page_number=1,
            text="This is chunk content."
        )
        
        assert chunk.id.startswith("chunk_")
        assert chunk.document_id == "doc_123"
        assert chunk.chunk_index == 0
        assert chunk.page_number == 1
        assert chunk.text == "This is chunk content."
        assert chunk.embedding == []
    
    def test_chunk_with_embedding(self):
        """Test chunk with valid embedding."""
        embedding = [0.1] * 1536
        chunk = Chunk(
            document_id="doc_123",
            chunk_index=0,
            page_number=1,
            text="Content",
            embedding=embedding
        )
        assert len(chunk.embedding) == 1536
    
    def test_chunk_embedding_wrong_dimensions(self):
        """Test chunk with wrong embedding dimensions."""
        with pytest.raises(ValidationError) as exc_info:
            Chunk(
                document_id="doc_123",
                chunk_index=0,
                page_number=1,
                text="Content",
                embedding=[0.1] * 100  # Wrong size
            )
        assert "1536 dimensions" in str(exc_info.value)
    
    def test_chunk_index_non_negative(self):
        """Test chunk_index must be >= 0."""
        chunk = Chunk(
            document_id="doc_123",
            chunk_index=0,
            page_number=1,
            text="Content"
        )
        assert chunk.chunk_index == 0
        
        with pytest.raises(ValidationError):
            Chunk(
                document_id="doc_123",
                chunk_index=-1,
                page_number=1,
                text="Content"
            )
    
    def test_chunk_page_number_positive(self):
        """Test page_number must be >= 1."""
        chunk = Chunk(
            document_id="doc_123",
            chunk_index=0,
            page_number=1,
            text="Content"
        )
        assert chunk.page_number == 1
        
        with pytest.raises(ValidationError):
            Chunk(
                document_id="doc_123",
                chunk_index=0,
                page_number=0,
                text="Content"
            )
    
    def test_chunk_text_not_empty(self):
        """Test chunk text cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            Chunk(
                document_id="doc_123",
                chunk_index=0,
                page_number=1,
                text=""
            )
        assert "Chunk text cannot be empty" in str(exc_info.value)
    
    def test_chunk_text_whitespace_only_rejected(self):
        """Test chunk with only whitespace is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Chunk(
                document_id="doc_123",
                chunk_index=0,
                page_number=1,
                text="   \n\t   "
            )
        assert "Chunk text cannot be empty" in str(exc_info.value)


class TestDocumentStatus:
    """Tests for DocumentStatus enum."""
    
    def test_status_values(self):
        """Test all status values exist."""
        assert DocumentStatus.PENDING.value == "pending"
        assert DocumentStatus.READY.value == "ready"
        assert DocumentStatus.DELETING.value == "deleting"
    
    def test_status_is_string_enum(self):
        """Test status can be used as string."""
        assert str(DocumentStatus.PENDING) == "DocumentStatus.PENDING"
        assert DocumentStatus.PENDING.value == "pending"


class TestGenerateId:
    """Tests for ID generation utility."""
    
    def test_generate_id_with_prefix(self):
        """Test ID generation with prefix."""
        id1 = generate_id("test_")
        id2 = generate_id("test_")
        
        assert id1.startswith("test_")
        assert id2.startswith("test_")
        assert id1 != id2  # Should be unique
    
    def test_generate_id_without_prefix(self):
        """Test ID generation without prefix."""
        id1 = generate_id()
        assert len(id1) == 12  # Just the hex part
