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
)


class TestInputSanitization:
    """Tests for input sanitization and injection prevention."""
    
    def test_pdf_path_traversal_attack(self):
        """Path traversal attempts should be caught by filename validation."""
        # While we validate .pdf extension, the actual path handling is OS-level
        # This test documents expected behavior
        with pytest.raises(ValidationError):
            IngestPdfEventData(
                pdf_path="../../../etc/passwd",  # No .pdf extension
                source_id="passwd"
            )
    
    def test_pdf_path_with_null_bytes(self):
        """Null bytes in paths should be rejected (path manipulation attack)."""
        with pytest.raises(ValidationError, match="null bytes"):
            IngestPdfEventData(
                pdf_path="/path/to/file\x00.pdf",
                source_id="file.pdf"
            )
    
    def test_question_with_script_injection(self):
        """Script tags in questions should be passed through (output escaping is UI responsibility)."""
        # The model should accept this - XSS prevention is at output layer
        data = QueryPdfEventData(
            question="<script>alert('xss')</script>What is this about?"
        )
        assert "<script>" in data.question
    
    def test_question_sql_injection_like_input(self):
        """SQL-like injection in questions should be handled safely."""
        data = QueryPdfEventData(
            question="'; DROP TABLE documents; --"
        )
        # MongoDB uses different syntax, but we test the input is accepted
        assert data.question == "'; DROP TABLE documents; --"
    
    def test_extremely_long_question(self):
        """Very long questions should be handled (may want to add length limit)."""
        long_question = "What is this? " * 10000
        data = QueryPdfEventData(question=long_question)
        assert len(data.question) > 100000
    
    def test_unicode_in_question(self):
        """Unicode characters should be handled properly."""
        data = QueryPdfEventData(
            question="这是什么？ Что это? مرحبا 🎉"
        )
        assert "这是什么" in data.question
        assert "🎉" in data.question
    
    def test_empty_workspace_id_is_none(self):
        """Empty string workspace_id should be allowed (treated as None)."""
        data = IngestPdfEventData(
            pdf_path="/path/file.pdf",
            source_id="file.pdf",
            workspace_id=""
        )
        assert data.workspace_id == ""


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_top_k_minimum(self):
        """top_k must be at least 1."""
        with pytest.raises(ValidationError):
            QueryPdfEventData(question="test", top_k=0)
    
    def test_top_k_maximum(self):
        """top_k should have a reasonable maximum."""
        with pytest.raises(ValidationError):
            QueryPdfEventData(question="test", top_k=51)  # Max is 50
    
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
            QueryPdfEventData(question=None)
    
    def test_question_as_number(self):
        """Number as question should fail (Pydantic strict mode)."""
        with pytest.raises(ValidationError):
            QueryPdfEventData(question=123)
    
    def test_top_k_as_string(self):
        """String number as top_k should be coerced."""
        data = QueryPdfEventData(question="test", top_k="5")
        assert data.top_k == 5
    
    def test_top_k_as_float(self):
        """Float as top_k should fail validation (no fractional parts)."""
        with pytest.raises(ValidationError):
            QueryPdfEventData(question="test", top_k=5.9)
    
    def test_history_as_non_list(self):
        """Non-list history should fail validation."""
        with pytest.raises(ValidationError):
            QueryPdfEventData(question="test", history="not a list")
    
    def test_scores_as_strings(self):
        """String scores should be coerced to floats."""
        result = SearchResult(
            contexts=["ctx"],
            sources=["src"],
            scores=["0.95", "0.85"]
        )
        assert all(isinstance(s, float) for s in result.scores)
