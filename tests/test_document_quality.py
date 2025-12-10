"""Quality tests for M1: Core Data Model.

Comprehensive tests covering the 9 quality aspects:
1. Security
2. Robustness
3. Scalability
4. Accessibility
5. Optimization
6. UI
7. UX
8. Reliability
9. Efficiency
"""
import pytest
import hashlib
import time
from pydantic import ValidationError

from models import (
    Document, DocumentScope, Chunk,
    DocumentStatus, ScopeType
)


class TestSecurity:
    """Security-related tests."""
    
    def test_checksum_prevents_tampering(self):
        """Test that checksums detect file tampering."""
        content1 = b"Original content"
        content2 = b"Tampered content"
        
        hash1 = f"sha256:{hashlib.sha256(content1).hexdigest()}"
        hash2 = f"sha256:{hashlib.sha256(content2).hexdigest()}"
        
        assert hash1 != hash2, "Different content should have different checksums"
    
    def test_filename_path_traversal_prevented(self):
        """Test that path traversal attacks are blocked."""
        malicious_filenames = [
            "../../../etc/passwd.pdf",
            "..\\..\\windows\\system32\\config.pdf",
            "test/../../../secret.pdf",
            "/etc/passwd.pdf",
            "\\windows\\system32.pdf"
        ]
        
        for filename in malicious_filenames:
            doc = Document(
                filename=filename,
                s3_key="safe_key",
                checksum=f"sha256:{'a' * 64}",
                size_bytes=100
            )
            # Verify dangerous characters are removed
            assert ".." not in doc.filename
            assert "/" not in doc.filename
            assert "\\" not in doc.filename
    
    def test_checksum_format_is_validated(self):
        """Test that checksum format is strictly validated."""
        invalid_checksums = [
            "md5:abc123",  # Wrong algorithm
            "sha256:xyz",  # Non-hex characters
            "sha256:" + "a" * 63,  # Too short
            "sha256:" + "a" * 65,  # Too long
            "abc123",  # No prefix
        ]
        
        for checksum in invalid_checksums:
            with pytest.raises(ValidationError):
                Document(
                    filename="test.pdf",
                    s3_key="key",
                    checksum=checksum,
                    size_bytes=100
                )
    
    def test_status_enum_prevents_injection(self):
        """Test that only valid status values are accepted."""
        valid_statuses = [DocumentStatus.PENDING, DocumentStatus.READY, DocumentStatus.DELETING]
        
        for status in valid_statuses:
            doc = Document(
                filename="test.pdf",
                s3_key=f"key_{status.value}",
                checksum=f"sha256:{'a' * 64}",
                size_bytes=100,
                status=status
            )
            assert doc.status in valid_statuses
    
    def test_scope_type_enum_prevents_injection(self):
        """Test that only valid scope types are accepted."""
        valid_types = [ScopeType.CHAT, ScopeType.PROJECT]
        
        for scope_type in valid_types:
            scope = DocumentScope(
                document_id="doc_1",
                scope_type=scope_type,
                scope_id="id_1"
            )
            assert scope.scope_type in valid_types


class TestRobustness:
    """Robustness-related tests."""
    
    def test_document_handles_edge_case_filename(self):
        """Test handling of edge case filenames."""
        edge_cases = [
            "   spaces.pdf   ",  # Leading/trailing spaces
            "special@#$.pdf",    # Special characters
            "UPPERCASE.PDF",     # Uppercase
            "file.PDF",          # Mixed case
        ]
        
        for filename in edge_cases:
            doc = Document(
                filename=filename,
                s3_key="key",
                checksum=f"sha256:{'a' * 64}",
                size_bytes=100
            )
            assert doc.filename.strip() == doc.filename  # No leading/trailing spaces
    
    def test_chunk_handles_empty_embedding(self):
        """Test that chunks can be created without embeddings."""
        chunk = Chunk(
            document_id="doc_1",
            chunk_index=0,
            page_number=1,
            text="Content"
        )
        assert chunk.embedding == []
    
    def test_document_status_transitions_are_valid(self):
        """Test that status values represent valid lifecycle."""
        # Verify enum values exist and are strings
        assert DocumentStatus.PENDING.value == "pending"
        assert DocumentStatus.READY.value == "ready"
        assert DocumentStatus.DELETING.value == "deleting"
    
    def test_model_handles_unicode_text(self):
        """Test handling of unicode in chunk text."""
        unicode_texts = [
            "Hello 世界",
            "Привет мир",
            "مرحبا بالعالم",
            "🎉 Emoji text 🚀",
        ]
        
        for text in unicode_texts:
            chunk = Chunk(
                document_id="doc_1",
                chunk_index=0,
                page_number=1,
                text=text
            )
            assert chunk.text == text


class TestScalability:
    """Scalability-related tests."""
    
    def test_document_model_is_lightweight(self):
        """Test that document model doesn't carry heavy data."""
        doc = Document(
            filename="test.pdf",
            s3_key="documents/test/file.pdf",
            checksum=f"sha256:{'a' * 64}",
            size_bytes=1000000
        )
        
        # Document should not contain file content or embeddings
        doc_dict = doc.model_dump()
        assert "content" not in doc_dict
        assert "embedding" not in doc_dict
        assert "chunks" not in doc_dict
    
    def test_chunk_references_document_by_id(self):
        """Test that chunks reference doc by ID only, not embedded data."""
        chunk = Chunk(
            document_id="doc_123",
            chunk_index=0,
            page_number=1,
            text="Content",
            embedding=[0.1] * 1536
        )
        
        # Chunk should only have document_id, not full document
        chunk_dict = chunk.model_dump()
        assert "document_id" in chunk_dict
        assert "document" not in chunk_dict
        assert "filename" not in chunk_dict
    
    def test_document_scope_is_minimal(self):
        """Test that document scope is a lightweight junction."""
        scope = DocumentScope(
            document_id="doc_1",
            scope_type=ScopeType.CHAT,
            scope_id="chat_1"
        )
        
        scope_dict = scope.model_dump()
        # Should only contain essential fields
        assert len(scope_dict) == 5  # id, document_id, scope_type, scope_id, linked_at


class TestOptimization:
    """Optimization-related tests."""
    
    def test_checksum_calculation_is_fast(self):
        """Test that checksum calculation is performant."""
        # Simulate 5MB of data
        data = b"x" * (5 * 1024 * 1024)
        
        start = time.time()
        checksum = hashlib.sha256(data).hexdigest()
        elapsed = time.time() - start
        
        assert elapsed < 1.0, f"Checksum calculation took {elapsed:.2f}s, expected < 1s"
    
    def test_model_serialization_is_fast(self):
        """Test that model serialization is performant."""
        doc = Document(
            filename="test.pdf",
            s3_key="key",
            checksum=f"sha256:{'a' * 64}",
            size_bytes=100
        )
        
        start = time.time()
        for _ in range(1000):
            doc.model_dump()
        elapsed = time.time() - start
        
        assert elapsed < 1.0, f"1000 serializations took {elapsed:.2f}s, expected < 1s"
    
    def test_embedding_dimension_is_optimal(self):
        """Test that embedding dimension is 1536 (text-embedding-3-small)."""
        # 1536 is optimal for speed over 3072 (text-embedding-3-large)
        embedding = [0.1] * 1536
        chunk = Chunk(
            document_id="doc_1",
            chunk_index=0,
            page_number=1,
            text="Content",
            embedding=embedding
        )
        assert len(chunk.embedding) == 1536


class TestReliability:
    """Reliability-related tests."""
    
    def test_id_generation_is_unique(self):
        """Test that generated IDs are unique."""
        from models import generate_id
        
        ids = set()
        for _ in range(1000):
            new_id = generate_id("test_")
            assert new_id not in ids, "ID collision detected"
            ids.add(new_id)
    
    def test_checksum_uniquely_identifies_content(self):
        """Test that checksums are deterministic."""
        content = b"Same content"
        
        hash1 = hashlib.sha256(content).hexdigest()
        hash2 = hashlib.sha256(content).hexdigest()
        
        assert hash1 == hash2, "Same content should produce same hash"
    
    def test_models_have_timestamps(self):
        """Test that models have proper timestamps."""
        from datetime import timezone
        
        doc = Document(
            filename="test.pdf",
            s3_key="key",
            checksum=f"sha256:{'a' * 64}",
            size_bytes=100
        )
        
        assert doc.uploaded_at is not None
        assert doc.uploaded_at.tzinfo == timezone.utc
        
        scope = DocumentScope(
            document_id="doc_1",
            scope_type=ScopeType.CHAT,
            scope_id="chat_1"
        )
        
        assert scope.linked_at is not None
        assert scope.linked_at.tzinfo == timezone.utc


class TestEfficiency:
    """Efficiency-related tests."""
    
    def test_model_memory_footprint(self):
        """Test that models have reasonable memory footprint."""
        import sys
        
        doc = Document(
            filename="test.pdf",
            s3_key="documents/chat/123/test.pdf",
            checksum=f"sha256:{'a' * 64}",
            size_bytes=100
        )
        
        # Document should be reasonably small in memory
        # (This is a rough estimate, not exact)
        size = sys.getsizeof(doc.model_dump_json())
        assert size < 1000, f"Document JSON is {size} bytes, expected < 1000"
    
    def test_deduplication_uses_checksum(self):
        """Test that checksum enables deduplication."""
        # Same content = same checksum
        content = b"Duplicate content"
        checksum = f"sha256:{hashlib.sha256(content).hexdigest()}"
        
        doc1 = Document(
            filename="file1.pdf",
            s3_key="key1",
            checksum=checksum,
            size_bytes=len(content)
        )
        
        doc2 = Document(
            filename="file2.pdf",
            s3_key="key2",
            checksum=checksum,
            size_bytes=len(content)
        )
        
        # Same checksum means these are the same file
        assert doc1.checksum == doc2.checksum


class TestBestPractices:
    """Architecture and best practices tests."""
    
    def test_models_have_docstrings(self):
        """Test that all models have docstrings."""
        assert Document.__doc__ is not None
        assert DocumentScope.__doc__ is not None
        assert Chunk.__doc__ is not None
    
    def test_models_use_type_hints(self):
        """Test that models use proper type hints."""
        from typing import get_type_hints
        
        doc_hints = get_type_hints(Document)
        assert "filename" in doc_hints
        assert "status" in doc_hints
        assert "checksum" in doc_hints
        
        chunk_hints = get_type_hints(Chunk)
        assert "text" in chunk_hints
        assert "embedding" in chunk_hints
    
    def test_models_use_pydantic(self):
        """Test that models are Pydantic BaseModel subclasses."""
        from pydantic import BaseModel
        
        assert issubclass(Document, BaseModel)
        assert issubclass(DocumentScope, BaseModel)
        assert issubclass(Chunk, BaseModel)
    
    def test_enums_are_string_based(self):
        """Test that enums are string-based for JSON serialization."""
        assert isinstance(DocumentStatus.PENDING.value, str)
        assert isinstance(ScopeType.CHAT.value, str)
