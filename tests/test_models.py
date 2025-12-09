"""Tests for Pydantic models."""
import pytest
from datetime import datetime
from pydantic import ValidationError

from models import (
    Workspace,
    Document,
    ChatSession,
    Message,
    MessageRole,
    IngestPdfEventData,
    QueryPdfEventData,
    ChunkWithPage,
    RAGChunkAndSrc,
    RAGUpsertResult,
    SearchResult,
    QueryResult,
    generate_id,
)


class TestGenerateId:
    """Tests for ID generation utility."""
    
    def test_generate_id_without_prefix(self):
        id1 = generate_id()
        id2 = generate_id()
        assert id1 != id2
        assert len(id1) == 12
    
    def test_generate_id_with_prefix(self):
        id1 = generate_id("ws_")
        assert id1.startswith("ws_")
        assert len(id1) == 15  # 3 + 12


class TestWorkspace:
    """Tests for Workspace model."""
    
    def test_create_workspace_minimal(self):
        ws = Workspace()
        assert ws.id.startswith("ws_")
        assert ws.name == "Default Workspace"
        assert isinstance(ws.created_at, datetime)
    
    def test_create_workspace_with_name(self):
        ws = Workspace(name="My Project")
        assert ws.name == "My Project"


class TestDocument:
    """Tests for Document model."""
    
    def test_create_document(self):
        doc = Document(
            workspace_id="ws_abc123",
            filename="test.pdf",
            source_id="test.pdf"
        )
        assert doc.id.startswith("doc_")
        assert doc.workspace_id == "ws_abc123"
        assert doc.filename == "test.pdf"


class TestMessage:
    """Tests for Message model."""
    
    def test_create_user_message(self):
        msg = Message(
            session_id="sess_123",
            role=MessageRole.USER,
            content="Hello"
        )
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
    
    def test_create_assistant_message_with_sources(self):
        msg = Message(
            session_id="sess_123",
            role=MessageRole.ASSISTANT,
            content="Here's the answer",
            sources=["doc1.pdf, page 1", "doc2.pdf, page 3"]
        )
        assert len(msg.sources) == 2


class TestIngestPdfEventData:
    """Tests for IngestPdfEventData validation."""
    
    def test_valid_pdf_path(self):
        data = IngestPdfEventData(
            pdf_path="/path/to/file.pdf",
            source_id="file.pdf"
        )
        assert data.pdf_path == "/path/to/file.pdf"
    
    def test_invalid_pdf_path_extension(self):
        with pytest.raises(ValidationError) as exc_info:
            IngestPdfEventData(
                pdf_path="/path/to/file.txt",
                source_id="file.txt"
            )
        assert "pdf_path must end with .pdf" in str(exc_info.value)
    
    def test_optional_workspace_id(self):
        data = IngestPdfEventData(
            pdf_path="/path/to/file.pdf",
            source_id="file.pdf",
            workspace_id="ws_123"
        )
        assert data.workspace_id == "ws_123"


class TestQueryPdfEventData:
    """Tests for QueryPdfEventData validation."""
    
    def test_valid_question(self):
        data = QueryPdfEventData(question="What is this about?")
        assert data.question == "What is this about?"
        assert data.top_k == 5  # default
    
    def test_question_is_stripped(self):
        data = QueryPdfEventData(question="  Hello world  ")
        assert data.question == "Hello world"
    
    def test_empty_question_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            QueryPdfEventData(question="   ")
        assert "question cannot be empty" in str(exc_info.value)
    
    def test_top_k_validation(self):
        data = QueryPdfEventData(question="test", top_k=10)
        assert data.top_k == 10
    
    def test_top_k_out_of_range(self):
        with pytest.raises(ValidationError):
            QueryPdfEventData(question="test", top_k=100)


class TestChunkWithPage:
    """Tests for ChunkWithPage model."""
    
    def test_create_chunk(self):
        chunk = ChunkWithPage(text="Some content", page=1)
        assert chunk.text == "Some content"
        assert chunk.page == 1
    
    def test_page_must_be_positive(self):
        with pytest.raises(ValidationError):
            ChunkWithPage(text="content", page=0)


class TestSearchResult:
    """Tests for SearchResult model."""
    
    def test_empty_result(self):
        result = SearchResult()
        assert result.contexts == []
        assert result.sources == []
        assert result.scores == []
    
    def test_result_with_data(self):
        result = SearchResult(
            contexts=["ctx1", "ctx2"],
            sources=["src1", "src2"],
            scores=[0.9, 0.8]
        )
        assert len(result.contexts) == 2


class TestQueryResult:
    """Tests for QueryResult model."""
    
    def test_create_query_result(self):
        result = QueryResult(
            answer="The answer is 42",
            sources=["doc.pdf, page 1"],
            num_contexts=1
        )
        assert result.answer == "The answer is 42"
        assert result.avg_confidence == 0.0  # default
    
    def test_confidence_range(self):
        with pytest.raises(ValidationError):
            QueryResult(
                answer="test",
                sources=[],
                num_contexts=0,
                avg_confidence=1.5  # out of range
            )
