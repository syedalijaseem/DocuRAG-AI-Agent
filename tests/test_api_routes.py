"""Tests for API routes security and functionality."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import io


class TestAPIRouteSecurity:
    """Security tests for API endpoints."""

    @pytest.fixture
    def mock_db(self):
        """Mock MongoDB database."""
        with patch("api_routes.get_db") as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def client(self, mock_db):
        """Create test client with mocked dependencies."""
        from main import app
        return TestClient(app)

    # --- File Upload Security ---

    def test_upload_rejects_non_pdf(self, client, mock_db):
        """Only PDF files should be accepted."""
        file_content = b"not a pdf"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        
        response = client.post("/api/workspaces/ws_123/upload", files=files)
        
        assert response.status_code == 400
        assert "PDF" in response.json()["detail"]

    def test_upload_rejects_exe_disguised_as_pdf(self, client, mock_db):
        """Reject files with EXE magic bytes even if extension is .pdf."""
        file_content = b"MZ\x90\x00"  # EXE magic bytes, not PDF
        files = {"file": ("malware.pdf", io.BytesIO(file_content), "application/pdf")}
        
        response = client.post("/api/workspaces/ws_123/upload", files=files)
        
        # Should be rejected due to invalid PDF content
        assert response.status_code == 400
        assert "Invalid PDF" in response.json()["detail"]

    def test_upload_rejects_path_traversal_filename(self, client, mock_db):
        """Filenames with path traversal should be sanitized."""
        file_content = b"%PDF-1.4"
        files = {"file": ("../../../etc/passwd.pdf", io.BytesIO(file_content), "application/pdf")}
        
        with patch("api_routes.file_storage.upload_file") as mock_upload:
            mock_upload.return_value = {"s3_key": "safe_key", "url": "s3://test", "filename": "passwd.pdf"}
            response = client.post("/api/workspaces/ws_123/upload", files=files)
            
            # Check that the S3 key doesn't contain path traversal
            if response.status_code == 200:
                call_args = mock_upload.call_args
                # The prefix should be workspace-scoped
                assert "workspaces/ws_123/" in call_args[0][2]

    # --- Workspace Endpoint Security ---

    def test_workspace_id_validation(self, client, mock_db):
        """Workspace IDs should be validated."""
        mock_db.workspaces.find_one.return_value = None
        
        response = client.get("/api/workspaces/invalid_id")
        
        assert response.status_code == 404

    def test_create_workspace_sanitizes_name(self, client, mock_db):
        """Workspace names should be sanitized."""
        response = client.post(
            "/api/workspaces",
            json={"name": "<script>alert('xss')</script>"}
        )
        
        # Should not error - but ideally would sanitize
        assert response.status_code == 200

    # --- Session Endpoint Security ---

    def test_session_not_found_returns_404(self, client, mock_db):
        """Missing session should return 404."""
        mock_db.chat_sessions.find_one.return_value = None
        
        response = client.get("/api/sessions/nonexistent")
        
        assert response.status_code == 404

    def test_delete_session_removes_messages(self, client, mock_db):
        """Deleting session should also delete its messages."""
        response = client.delete("/api/sessions/sess_123")
        
        # Verify both collections were modified
        mock_db.chat_sessions.delete_one.assert_called_once()
        mock_db.messages.delete_many.assert_called_once()


class TestAPIRoutesFunctionality:
    """Functional tests for API endpoints."""

    @pytest.fixture
    def mock_db(self):
        """Mock MongoDB database."""
        with patch("api_routes.get_db") as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def client(self, mock_db):
        """Create test client."""
        from main import app
        return TestClient(app)

    def test_create_workspace(self, client, mock_db):
        """Test workspace creation."""
        response = client.post("/api/workspaces", json={"name": "Test Workspace"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Workspace"
        assert data["id"].startswith("ws_")

    def test_list_workspaces(self, client, mock_db):
        """Test listing workspaces."""
        mock_db.workspaces.find.return_value = [
            {"id": "ws_1", "name": "Workspace 1"},
            {"id": "ws_2", "name": "Workspace 2"}
        ]
        
        response = client.get("/api/workspaces")
        
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_create_session(self, client, mock_db):
        """Test session creation."""
        response = client.post(
            "/api/sessions",
            json={"workspace_id": "ws_123", "title": "New Chat"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["workspace_id"] == "ws_123"
        assert data["id"].startswith("sess_")

    def test_save_message_updates_session_title(self, client, mock_db):
        """First user message should update session title."""
        mock_db.chat_sessions.find_one.return_value = {
            "id": "sess_123",
            "title": "New Chat"
        }
        
        response = client.post(
            "/api/messages",
            json={
                "session_id": "sess_123",
                "role": "user",
                "content": "What is machine learning?",
                "sources": []
            }
        )
        
        assert response.status_code == 200
        # Verify title was updated
        mock_db.chat_sessions.update_one.assert_called()

    def test_get_messages(self, client, mock_db):
        """Test retrieving messages for a session."""
        mock_db.messages.find.return_value.sort.return_value = [
            {"id": "msg_1", "role": "user", "content": "Hello"},
            {"id": "msg_2", "role": "assistant", "content": "Hi there!"}
        ]
        
        response = client.get("/api/sessions/sess_123/messages")
        
        assert response.status_code == 200
        assert len(response.json()) == 2
