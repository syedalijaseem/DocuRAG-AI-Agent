"""Simplified integration tests for M1: Document API endpoints.

Tests validation logic without requiring full database mocking.
"""
import pytest
import io
import hashlib
from pydantic import ValidationError

from models import Document, DocumentScope, Chunk, DocumentStatus, ScopeType
from document_routes import (
    calculate_checksum,
    validate_file_type,
    MAX_FILE_SIZE,
    PDF_MAGIC_BYTES
)
from fastapi import HTTPException


class TestChecksumCalculation:
    """Tests for checksum calculation helper."""
    
    def test_calculate_checksum_correct_format(self):
        """Test checksum has correct format."""
        content = b"test content"
        checksum = calculate_checksum(content)
        
        assert checksum.startswith("sha256:")
        assert len(checksum) == 7 + 64  # sha256: + 64 hex chars
    
    def test_calculate_checksum_deterministic(self):
        """Test same content produces same checksum."""
        content = b"identical content"
        
        checksum1 = calculate_checksum(content)
        checksum2 = calculate_checksum(content)
        
        assert checksum1 == checksum2
    
    def test_calculate_checksum_different_content(self):
        """Test different content produces different checksums."""
        checksum1 = calculate_checksum(b"content 1")
        checksum2 = calculate_checksum(b"content 2")
        
        assert checksum1 != checksum2
    
    def test_checksum_matches_model_validation(self):
        """Test calculated checksum passes model validation."""
        content = b"test pdf content"
        checksum = calculate_checksum(content)
        
        # Should not raise
        doc = Document(
            filename="test.pdf",
            s3_key="key",
            checksum=checksum,
            size_bytes=len(content)
        )
        assert doc.checksum == checksum


class TestFileTypeValidation:
    """Tests for file type validation helper."""
    
    def test_validate_pdf_with_magic_bytes(self):
        """Test valid PDF is accepted."""
        content = b"%PDF-1.4 rest of file"
        
        # Should not raise
        validate_file_type(content, "document.pdf")
    
    def test_reject_non_pdf_extension(self):
        """Test non-PDF extension is rejected."""
        content = b"%PDF-1.4 rest of file"  # Valid PDF content but wrong extension
        
        with pytest.raises(HTTPException) as exc_info:
            validate_file_type(content, "document.txt")
        
        assert exc_info.value.status_code == 400
        assert "PDF" in exc_info.value.detail
    
    def test_reject_fake_pdf_with_wrong_magic(self):
        """Test file with PDF extension but wrong content is rejected."""
        content = b"This is not a PDF"
        
        with pytest.raises(HTTPException) as exc_info:
            validate_file_type(content, "fake.pdf")
        
        assert exc_info.value.status_code == 400
        assert "valid PDF" in exc_info.value.detail
    
    def test_reject_empty_file(self):
        """Test empty file is rejected."""
        content = b""
        
        with pytest.raises(HTTPException) as exc_info:
            validate_file_type(content, "empty.pdf")
        
        assert exc_info.value.status_code == 400


class TestFileSizeValidation:
    """Tests for file size limits."""
    
    def test_max_file_size_is_50mb(self):
        """Test max file size constant is 50MB."""
        assert MAX_FILE_SIZE == 50 * 1024 * 1024
    
    def test_pdf_magic_bytes_constant(self):
        """Test PDF magic bytes are correct."""
        assert PDF_MAGIC_BYTES == b"%PDF-"


class TestDocumentCreationFlow:
    """Tests for document creation flow."""
    
    def test_document_status_is_pending_on_creation(self):
        """Test new documents have pending status."""
        doc = Document(
            filename="new.pdf",
            s3_key="path/new.pdf",
            checksum=f"sha256:{'a' * 64}",
            size_bytes=1000
        )
        
        assert doc.status == DocumentStatus.PENDING
    
    def test_document_scope_links_correctly(self):
        """Test document scope links document to chat."""
        scope = DocumentScope(
            document_id="doc_123",
            scope_type=ScopeType.CHAT,
            scope_id="chat_456"
        )
        
        assert scope.document_id == "doc_123"
        assert scope.scope_type == ScopeType.CHAT
        assert scope.scope_id == "chat_456"
    
    def test_document_scope_can_link_to_project(self):
        """Test document scope can link to project."""
        scope = DocumentScope(
            document_id="doc_123",
            scope_type=ScopeType.PROJECT,
            scope_id="proj_456"
        )
        
        assert scope.scope_type == ScopeType.PROJECT


class TestDocumentDeduplication:
    """Tests for checksum-based deduplication logic."""
    
    def test_same_file_produces_same_checksum(self):
        """Test identical files produce identical checksums."""
        file_content = b"%PDF-1.4 fake pdf content here"
        
        checksum1 = calculate_checksum(file_content)
        checksum2 = calculate_checksum(file_content)
        
        assert checksum1 == checksum2
    
    def test_checksum_is_sha256(self):
        """Test checksum uses SHA-256."""
        content = b"test"
        expected = f"sha256:{hashlib.sha256(content).hexdigest()}"
        actual = calculate_checksum(content)
        
        assert actual == expected


class TestScopeTypeValidation:
    """Tests for scope type enum validation."""
    
    def test_valid_scope_types(self):
        """Test valid scope type values."""
        assert ScopeType.CHAT.value == "chat"
        assert ScopeType.PROJECT.value == "project"
    
    def test_scope_type_is_string_enum(self):
        """Test scope type is string-based for serialization."""
        scope = DocumentScope(
            document_id="doc_1",
            scope_type=ScopeType.CHAT,
            scope_id="chat_1"
        )
        
        serialized = scope.model_dump()
        assert serialized["scope_type"] == "chat"


class TestAPIConstants:
    """Tests for API configuration constants."""
    
    def test_allowed_extensions_includes_pdf(self):
        """Test PDF is in allowed extensions."""
        from document_routes import ALLOWED_EXTENSIONS
        assert ".pdf" in ALLOWED_EXTENSIONS
    
    def test_max_size_is_reasonable(self):
        """Test max file size is reasonable (10-100MB range)."""
        assert 10 * 1024 * 1024 <= MAX_FILE_SIZE <= 100 * 1024 * 1024


class TestDeleteFlowLogic:
    """Tests for deletion logic."""
    
    def test_document_can_transition_to_deleting(self):
        """Test document can be set to deleting status."""
        doc = Document(
            filename="test.pdf",
            s3_key="key",
            checksum=f"sha256:{'a' * 64}",
            size_bytes=100,
            status=DocumentStatus.DELETING
        )
        
        assert doc.status == DocumentStatus.DELETING
    
    def test_all_status_values_exist(self):
        """Test all status values are defined."""
        assert hasattr(DocumentStatus, "PENDING")
        assert hasattr(DocumentStatus, "READY")
        assert hasattr(DocumentStatus, "DELETING")
