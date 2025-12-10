"""Security tests for input validation and edge cases.

These tests ensure the application handles malicious or unexpected inputs safely.
"""
import pytest
from pydantic import ValidationError

from models import (
    IngestPdfEventData,
    QueryPdfEventData,
    ChunkWithPage,
    RAGChunkAndSrc,
    SearchResult,
    QueryResult,
    ScopeType,
)


class TestInputSanitization:
    """Tests for input sanitization and injection prevention."""
    
    def test_pdf_path_traversal_attack(self):
        """Path traversal attempts should be caught by filename validation."""
        with pytest.raises(ValidationError):
            IngestPdfEventData(
                pdf_path="../../../etc/passwd",  # No .pdf extension
                filename="passwd",
                scope_type=ScopeType.CHAT,
                scope_id="chat_123",
                document_id="doc_abc123"
            )
    
    def test_pdf_path_traversal_with_pdf_extension(self):
        """Path traversal with .pdf extension should still be rejected."""
        with pytest.raises(ValidationError, match="path traversal"):
            IngestPdfEventData(
                pdf_path="../../../uploads/malicious.pdf",
                filename="malicious.pdf",
                scope_type=ScopeType.CHAT,
                scope_id="chat_123",
                document_id="doc_abc123"
            )
    
    def test_pdf_path_with_null_bytes(self):
        """Null bytes in paths should be rejected (path manipulation attack)."""
        with pytest.raises(ValidationError, match="null bytes"):
            IngestPdfEventData(
                pdf_path="/path/to/file\x00.pdf",
                filename="file.pdf",
                scope_type=ScopeType.CHAT,
                scope_id="chat_123",
                document_id="doc_abc123"
            )
    
    def test_question_with_script_injection(self):
        """Script tags in questions should be passed through (output escaping is UI responsibility)."""
        data = QueryPdfEventData(
            question="<script>alert('xss')</script>What is this about?",
            chat_id="chat_123",
            scope_type=ScopeType.CHAT,
            scope_id="chat_123"
        )
        assert "<script>" in data.question
    
    def test_question_sql_injection_like_input(self):
        """SQL-like injection in questions should be handled safely."""
        data = QueryPdfEventData(
            question="'; DROP TABLE documents; --",
            chat_id="chat_123",
            scope_type=ScopeType.CHAT,
            scope_id="chat_123"
        )
        assert data.question == "'; DROP TABLE documents; --"
    
    def test_extremely_long_question(self):
        """Very long questions should be handled."""
        long_question = "What is this? " * 10000
        data = QueryPdfEventData(
            question=long_question,
            chat_id="chat_123",
            scope_type=ScopeType.CHAT,
            scope_id="chat_123"
        )
        assert len(data.question) > 100000
    
    def test_unicode_in_question(self):
        """Unicode characters should be handled properly."""
        data = QueryPdfEventData(
            question="这是什么？ Что это? مرحبا 🎉",
            chat_id="chat_123",
            scope_type=ScopeType.CHAT,
            scope_id="chat_123"
        )
        assert "这是什么" in data.question
        assert "🎉" in data.question


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_top_k_minimum(self):
        """top_k must be at least 1."""
        with pytest.raises(ValidationError):
            QueryPdfEventData(
                question="test",
                chat_id="chat_123",
                scope_type=ScopeType.CHAT,
                scope_id="chat_123",
                top_k=0
            )
    
    def test_top_k_maximum(self):
        """top_k should have a reasonable maximum."""
        with pytest.raises(ValidationError):
            QueryPdfEventData(
                question="test",
                chat_id="chat_123",
                scope_type=ScopeType.CHAT,
                scope_id="chat_123",
                top_k=51
            )
    
    def test_chunk_page_zero(self):
        """Page 0 should be invalid (1-indexed)."""
        with pytest.raises(ValidationError):
            ChunkWithPage(text="content", page=0)
    
    def test_chunk_negative_page(self):
        """Negative page numbers should be invalid."""
        with pytest.raises(ValidationError):
            ChunkWithPage(text="content", page=-1)
    
    def test_search_result_empty_arrays(self):
        """Empty search results should be valid."""
        result = SearchResult(contexts=[], sources=[], scores=[])
        assert len(result.contexts) == 0
    
    def test_query_result_negative_num_contexts(self):
        """Negative num_contexts should be invalid."""
        with pytest.raises(ValidationError):
            QueryResult(
                answer="test",
                sources=[],
                num_contexts=-1
            )
    
    def test_confidence_exactly_zero(self):
        """Confidence of 0.0 should be valid."""
        result = QueryResult(
            answer="test",
            sources=[],
            num_contexts=0,
            avg_confidence=0.0
        )
        assert result.avg_confidence == 0.0
    
    def test_confidence_exactly_one(self):
        """Confidence of 1.0 should be valid."""
        result = QueryResult(
            answer="test",
            sources=[],
            num_contexts=0,
            avg_confidence=1.0
        )
        assert result.avg_confidence == 1.0


class TestMalformedData:
    """Tests for handling malformed or unexpected data types."""
    
    def test_question_as_none(self):
        """None as question should fail validation."""
        with pytest.raises(ValidationError):
            QueryPdfEventData(
                question=None,
                chat_id="chat_123",
                scope_type=ScopeType.CHAT,
                scope_id="chat_123"
            )
    
    def test_question_as_number(self):
        """Number as question should fail."""
        with pytest.raises(ValidationError):
            QueryPdfEventData(
                question=123,
                chat_id="chat_123",
                scope_type=ScopeType.CHAT,
                scope_id="chat_123"
            )
    
    def test_top_k_as_string(self):
        """String number as top_k should be coerced."""
        data = QueryPdfEventData(
            question="test",
            chat_id="chat_123",
            scope_type=ScopeType.CHAT,
            scope_id="chat_123",
            top_k="5"
        )
        assert data.top_k == 5
    
    def test_top_k_as_float(self):
        """Float as top_k should fail validation."""
        with pytest.raises(ValidationError):
            QueryPdfEventData(
                question="test",
                chat_id="chat_123",
                scope_type=ScopeType.CHAT,
                scope_id="chat_123",
                top_k=5.9
            )
    
    def test_history_as_non_list(self):
        """Non-list history should fail validation."""
        with pytest.raises(ValidationError):
            QueryPdfEventData(
                question="test",
                chat_id="chat_123",
                scope_type=ScopeType.CHAT,
                scope_id="chat_123",
                history="not a list"
            )
    
    def test_scores_as_strings(self):
        """String scores should be coerced to floats."""
        result = SearchResult(
            contexts=["ctx"],
            sources=["src"],
            scores=["0.95", "0.85"]
        )
        assert all(isinstance(s, float) for s in result.scores)
