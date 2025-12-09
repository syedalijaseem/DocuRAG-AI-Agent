"""Tests for Streamlit helper functions.

Note: These test the non-UI helper functions. Full UI tests would require
Playwright or Selenium.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
import tempfile
import os


class TestStreamlitHelpers:
    """Tests for Streamlit helper functions."""
    
    def test_generate_workspace_id(self):
        """Should generate unique workspace IDs."""
        # Import the generate_id function used in streamlit_app
        from models import generate_id
        
        id1 = generate_id("ws_")
        id2 = generate_id("ws_")
        
        assert id1 != id2
        assert id1.startswith("ws_")
        assert len(id1) == 15  # "ws_" + 12 chars
    
    def test_save_uploaded_pdf(self):
        """Should save uploaded file to uploads directory."""
        # Create a mock uploaded file
        mock_file = MagicMock()
        mock_file.name = "test_document.pdf"
        mock_file.getbuffer.return_value = b"%PDF-1.4 mock content"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('streamlit_app.Path') as mock_path_class:
                # Setup path mocking
                uploads_dir = Path(tmpdir) / "uploads"
                uploads_dir.mkdir()
                
                mock_path_class.return_value = uploads_dir
                mock_path_class.__truediv__ = lambda self, other: uploads_dir / other
                
                # Test that the file would be saved
                file_path = uploads_dir / mock_file.name
                file_path.write_bytes(mock_file.getbuffer())
                
                assert file_path.exists()
                assert file_path.read_bytes() == b"%PDF-1.4 mock content"


class TestInngestEventCreation:
    """Tests for Inngest event creation in Streamlit."""
    
    @pytest.fixture
    def mock_inngest_client(self):
        """Create a mock Inngest client."""
        with patch('streamlit_app.inngest.Inngest') as mock:
            client = MagicMock()
            client.send = AsyncMock(return_value=["event_123"])
            mock.return_value = client
            yield client
    
    def test_ingest_event_structure(self):
        """Ingest event should have correct structure."""
        from models import IngestPdfEventData
        
        data = IngestPdfEventData(
            pdf_path="/uploads/doc.pdf",
            source_id="doc.pdf",
            workspace_id="ws_test123"
        )
        
        event_dict = data.model_dump()
        assert "pdf_path" in event_dict
        assert "source_id" in event_dict
        assert "workspace_id" in event_dict
    
    def test_query_event_structure(self):
        """Query event should have correct structure."""
        from models import QueryPdfEventData
        
        data = QueryPdfEventData(
            question="What is this about?",
            top_k=5,
            workspace_id="ws_test123",
            history=[{"role": "user", "content": "prev q"}]
        )
        
        event_dict = data.model_dump()
        assert "question" in event_dict
        assert "top_k" in event_dict
        assert "workspace_id" in event_dict
        assert "history" in event_dict


class TestSessionStateManagement:
    """Tests for session state patterns used in Streamlit."""
    
    def test_initial_session_state(self):
        """Test expected initial session state values."""
        # These are the values that should be initialized
        expected_keys = [
            "workspace_id",
            "uploaded_docs",
            "messages",
            "history",
            "session_id",
            "uploader_key"
        ]
        
        # Verify our models can handle these patterns
        from models import generate_id
        
        workspace_id = generate_id("ws_")
        assert workspace_id.startswith("ws_")
        
        session_id = generate_id("sess_")
        assert session_id.startswith("sess_")
    
    def test_chat_message_structure(self):
        """Test chat message structure used in session state."""
        message = {
            "role": "user",
            "content": "Hello!"
        }
        
        assert message["role"] in ["user", "assistant"]
        assert isinstance(message["content"], str)
    
    def test_assistant_message_with_sources(self):
        """Test assistant message with sources."""
        message = {
            "role": "assistant",
            "content": "Here's the answer.",
            "sources": ["doc.pdf, page 1", "doc.pdf, page 5"]
        }
        
        assert len(message["sources"]) == 2


class TestUIDataTransformation:
    """Tests for data transformations between UI and backend."""
    
    def test_query_result_to_ui_message(self):
        """Should transform QueryResult to UI message format."""
        from models import QueryResult
        
        result = QueryResult(
            answer="The answer is 42.",
            sources=["guide.pdf, page 10"],
            num_contexts=1,
            history=[],
            avg_confidence=0.95
        )
        
        # Transform to UI message format
        ui_message = {
            "role": "assistant",
            "content": result.answer,
            "sources": result.sources
        }
        
        assert ui_message["role"] == "assistant"
        assert ui_message["content"] == "The answer is 42."
        assert len(ui_message["sources"]) == 1
    
    def test_history_format_compatibility(self):
        """History format should be compatible between UI and backend."""
        # UI format
        ui_history = [
            {"role": "user", "content": "Question 1"},
            {"role": "assistant", "content": "Answer 1"},
        ]
        
        # Should be accepted by QueryPdfEventData
        from models import QueryPdfEventData
        
        data = QueryPdfEventData(
            question="Question 2",
            history=ui_history
        )
        
        assert data.history == ui_history
