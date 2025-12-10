"""Tests for Pydantic models."""
import pytest
from datetime import datetime
from pydantic import ValidationError

from models import (
    Project,
    Chat,
    Document,
    Message,
    MessageRole,
    ScopeType,
    IngestPdfEventData,
    QueryPdfEventData,
    ChunkWithPage,
    RAGChunkAndSrc,
    RAGUpsertResult,
    SearchResult,
    QueryResult,
    generate_id,
    # Legacy models
    Workspace,
    ChatSession,
)


class TestGenerateId:
    """Tests for ID generation utility."""
    
    def test_generate_id_without_prefix(self):
        id1 = generate_id()
        id2 = generate_id()
        assert id1 != id2
        assert len(id1) == 12
    
    def test_generate_id_with_prefix(self):
        id1 = generate_id("proj_")
        assert id1.startswith("proj_")
        assert len(id1) == 17  # 5 + 12


class TestProject:
    """Tests for Project model."""
    
    def test_create_project_minimal(self):
        proj = Project()
        assert proj.id.startswith("proj_")
        assert proj.name == "New Project"
        assert isinstance(proj.created_at, datetime)
    
    def test_create_project_with_name(self):
        proj = Project(name="Research Paper")
        assert proj.name == "Research Paper"


class TestChat:
    """Tests for Chat model."""
    
    def test_create_standalone_chat(self):
        chat = Chat()
        assert chat.id.startswith("chat_")
        assert chat.project_id is None
        assert chat.title == "New Chat"
        assert chat.is_pinned is False
    
    def test_create_project_chat(self):
        chat = Chat(project_id="proj_abc123", title="Project Notes")
        assert chat.project_id == "proj_abc123"
        assert chat.title == "Project Notes"
    
    def test_pinned_chat(self):
        chat = Chat(is_pinned=True)
        assert chat.is_pinned is True


class TestDocument:
    """Tests for Document model."""
    
    def test_create_document(self):
        doc = Document(
            filename="test.pdf",
            s3_key="chats/chat_123/test.pdf",
            scope_type=ScopeType.CHAT,
            scope_id="chat_123"
        )
        assert doc.id.startswith("doc_")
        assert doc.filename == "test.pdf"
        assert doc.scope_type == ScopeType.CHAT
        assert doc.scope_id == "chat_123"
    
    def test_create_project_document(self):
        doc = Document(
            filename="report.pdf",
            s3_key="projects/proj_456/report.pdf",
            scope_type=ScopeType.PROJECT,
            scope_id="proj_456"
        )
        assert doc.scope_type == ScopeType.PROJECT


class TestMessage:
    """Tests for Message model."""
    
    def test_create_user_message(self):
        msg = Message(
            chat_id="chat_123",
            role=MessageRole.USER,
            content="Hello"
        )
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
    
    def test_create_assistant_message_with_sources(self):
        msg = Message(
            chat_id="chat_123",
            role=MessageRole.ASSISTANT,
            content="Here's the answer",
            sources=["doc1.pdf, page 1", "doc2.pdf, page 3"]
        )
        assert len(msg.sources) == 2


class TestIngestPdfEventData:
    """Tests for IngestPdfEventData validation."""
    
    def test_valid_pdf_path(self):
        data = IngestPdfEventData(
            pdf_path="chats/chat_123/file.pdf",
            filename="file.pdf",
            scope_type=ScopeType.CHAT,
            scope_id="chat_123"
        )
        assert data.pdf_path == "chats/chat_123/file.pdf"
        assert data.scope_type == ScopeType.CHAT
    
    def test_invalid_pdf_path_extension(self):
        with pytest.raises(ValidationError) as exc_info:
            IngestPdfEventData(
                pdf_path="chats/chat_123/file.txt",
                filename="file.txt",
                scope_type=ScopeType.CHAT,
                scope_id="chat_123"
            )
        assert "pdf_path must end with .pdf" in str(exc_info.value)
    
    def test_project_scope(self):
        data = IngestPdfEventData(
            pdf_path="projects/proj_456/file.pdf",
            filename="file.pdf",
            scope_type=ScopeType.PROJECT,
            scope_id="proj_456"
        )
        assert data.scope_type == ScopeType.PROJECT
        assert data.scope_id == "proj_456"


class TestQueryPdfEventData:
    """Tests for QueryPdfEventData validation."""
    
    def test_valid_question(self):
        data = QueryPdfEventData(
            question="What is this about?",
            chat_id="chat_123",
            scope_type=ScopeType.CHAT,
            scope_id="chat_123"
        )
        assert data.question == "What is this about?"
        assert data.top_k == 5  # default
    
    def test_question_is_stripped(self):
        data = QueryPdfEventData(
            question="  Hello world  ",
            chat_id="chat_123",
            scope_type=ScopeType.CHAT,
            scope_id="chat_123"
        )
        assert data.question == "Hello world"
    
    def test_empty_question_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            QueryPdfEventData(
                question="   ",
                chat_id="chat_123",
                scope_type=ScopeType.CHAT,
                scope_id="chat_123"
            )
        assert "question cannot be empty" in str(exc_info.value)
    
    def test_top_k_validation(self):
        data = QueryPdfEventData(
            question="test",
            chat_id="chat_123",
            scope_type=ScopeType.PROJECT,
            scope_id="proj_456",
            top_k=10
        )
        assert data.top_k == 10
    
    def test_top_k_out_of_range(self):
        with pytest.raises(ValidationError):
            QueryPdfEventData(
                question="test",
                chat_id="chat_123",
                scope_type=ScopeType.CHAT,
                scope_id="chat_123",
                top_k=100
            )


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


# --- Legacy Model Tests ---

class TestLegacyWorkspace:
    """Tests for legacy Workspace model (backward compatibility)."""
    
    def test_create_workspace(self):
        ws = Workspace()
        assert ws.id.startswith("ws_")
        assert ws.name == "Default Workspace"


class TestLegacyChatSession:
    """Tests for legacy ChatSession model (backward compatibility)."""
    
    def test_create_session(self):
        session = ChatSession(workspace_id="ws_123")
        assert session.id.startswith("sess_")
        assert session.workspace_id == "ws_123"
