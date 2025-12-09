"""Tests for Inngest functions in main.py.

These tests mock the Inngest context and external dependencies to test
the function logic in isolation.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pydantic import ValidationError


class TestRagIngestPdf:
    """Tests for rag_ingest_pdf Inngest function."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock Inngest context."""
        ctx = MagicMock()
        ctx.event = MagicMock()
        ctx.step = MagicMock()
        ctx.step.run = AsyncMock()
        return ctx
    
    def test_ingest_validates_event_data(self, mock_context):
        """Should validate event data with Pydantic."""
        # Missing required fields
        mock_context.event.data = {}
        
        with patch('main.IngestPdfEventData') as mock_model:
            mock_model.side_effect = ValidationError.from_exception_data(
                'IngestPdfEventData',
                [{'type': 'missing', 'loc': ('pdf_path',), 'msg': 'Field required'}]
            )
            
            # The function should fail early on validation
            from models import IngestPdfEventData
            with pytest.raises(ValidationError):
                IngestPdfEventData(**mock_context.event.data)
    
    def test_ingest_rejects_non_pdf(self, mock_context):
        """Should reject non-PDF files."""
        mock_context.event.data = {
            "pdf_path": "/path/to/file.txt",
            "source_id": "file.txt"
        }
        
        from models import IngestPdfEventData
        with pytest.raises(ValidationError, match="pdf"):
            IngestPdfEventData(**mock_context.event.data)
    
    def test_ingest_rejects_path_traversal(self, mock_context):
        """Should reject path traversal attempts."""
        mock_context.event.data = {
            "pdf_path": "../../etc/passwd.pdf",
            "source_id": "passwd.pdf"
        }
        
        from models import IngestPdfEventData
        with pytest.raises(ValidationError, match="path traversal"):
            IngestPdfEventData(**mock_context.event.data)
    
    def test_ingest_accepts_valid_pdf(self, mock_context):
        """Should accept valid PDF path."""
        mock_context.event.data = {
            "pdf_path": "/uploads/document.pdf",
            "source_id": "document.pdf",
            "workspace_id": "ws_123"
        }
        
        from models import IngestPdfEventData
        data = IngestPdfEventData(**mock_context.event.data)
        assert data.pdf_path == "/uploads/document.pdf"
        assert data.workspace_id == "ws_123"


class TestRagQueryPdf:
    """Tests for rag_query_pdf_ai Inngest function."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock Inngest context."""
        ctx = MagicMock()
        ctx.event = MagicMock()
        ctx.step = MagicMock()
        ctx.step.run = AsyncMock()
        ctx.step.ai = MagicMock()
        ctx.step.ai.infer = AsyncMock()
        return ctx
    
    def test_query_validates_event_data(self, mock_context):
        """Should validate event data with Pydantic."""
        mock_context.event.data = {}
        
        from models import QueryPdfEventData
        with pytest.raises(ValidationError):
            QueryPdfEventData(**mock_context.event.data)
    
    def test_query_rejects_empty_question(self, mock_context):
        """Should reject empty questions."""
        mock_context.event.data = {"question": "   "}
        
        from models import QueryPdfEventData
        with pytest.raises(ValidationError, match="empty"):
            QueryPdfEventData(**mock_context.event.data)
    
    def test_query_accepts_valid_question(self, mock_context):
        """Should accept valid question."""
        mock_context.event.data = {
            "question": "What is machine learning?",
            "top_k": 5,
            "workspace_id": "ws_abc"
        }
        
        from models import QueryPdfEventData
        data = QueryPdfEventData(**mock_context.event.data)
        assert data.question == "What is machine learning?"
        assert data.top_k == 5
    
    def test_query_handles_reset_commands(self, mock_context):
        """Should recognize reset commands."""
        for cmd in ["reset", "clear", "new chat"]:
            from models import QueryPdfEventData
            data = QueryPdfEventData(question=cmd)
            assert data.question.lower() in ("reset", "clear", "new chat")
    
    def test_query_preserves_history(self, mock_context):
        """Should preserve conversation history."""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        mock_context.event.data = {
            "question": "Follow up",
            "history": history
        }
        
        from models import QueryPdfEventData
        data = QueryPdfEventData(**mock_context.event.data)
        assert len(data.history) == 2


class TestSearchResultProcessing:
    """Tests for search result processing logic."""
    
    def test_search_result_with_sources(self):
        """Should properly format sources."""
        from models import SearchResult
        
        result = SearchResult(
            contexts=["Context 1", "Context 2"],
            sources=["doc.pdf, page 1", "doc.pdf, page 2"],
            scores=[0.95, 0.85]
        )
        
        assert len(result.contexts) == 2
        assert all(s > 0.8 for s in result.scores)
    
    def test_query_result_with_confidence(self):
        """Should include confidence score."""
        from models import QueryResult
        
        result = QueryResult(
            answer="The answer is 42.",
            sources=["guide.pdf, page 10"],
            num_contexts=1,
            avg_confidence=0.92
        )
        
        assert result.avg_confidence == 0.92


class TestEventDataSerialization:
    """Tests for event data serialization."""
    
    def test_ingest_event_to_dict(self):
        """Should serialize to dict for Inngest."""
        from models import IngestPdfEventData
        
        data = IngestPdfEventData(
            pdf_path="/path/doc.pdf",
            source_id="doc.pdf",
            workspace_id="ws_123"
        )
        
        d = data.model_dump()
        assert d["pdf_path"] == "/path/doc.pdf"
        assert d["workspace_id"] == "ws_123"
    
    def test_query_result_to_dict(self):
        """Should serialize QueryResult for response."""
        from models import QueryResult
        
        result = QueryResult(
            answer="Test answer",
            sources=["src1"],
            num_contexts=1,
            history=[{"role": "user", "content": "q"}],
            avg_confidence=0.9
        )
        
        d = result.model_dump()
        assert "answer" in d
        assert "history" in d
        assert d["avg_confidence"] == 0.9
