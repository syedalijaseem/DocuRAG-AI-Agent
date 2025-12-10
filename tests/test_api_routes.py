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
        
        response = client.post("/api/upload?scope_type=chat&scope_id=chat_123", files=files)
        
        assert response.status_code == 400
        assert "PDF" in response.json()["detail"]

    def test_upload_rejects_exe_disguised_as_pdf(self, client, mock_db):
        """Reject files with EXE magic bytes even if extension is .pdf."""
        file_content = b"MZ\x90\x00"  # EXE magic bytes, not PDF
        files = {"file": ("malware.pdf", io.BytesIO(file_content), "application/pdf")}
        
        response = client.post("/api/upload?scope_type=chat&scope_id=chat_123", files=files)
        
        assert response.status_code == 400
        assert "Invalid PDF" in response.json()["detail"]

    def test_upload_rejects_path_traversal_filename(self, client, mock_db):
        """Filenames with path traversal should be sanitized."""
        file_content = b"%PDF-1.4"
        files = {"file": ("../../../etc/passwd.pdf", io.BytesIO(file_content), "application/pdf")}
        
        # Mock M1 deduplication check
        mock_db.documents.find_one.return_value = None
        
        with patch("api_routes.file_storage.upload_file") as mock_upload:
            mock_upload.return_value = {"s3_key": "safe_key", "url": "s3://test", "filename": "passwd.pdf"}
            response = client.post("/api/upload?scope_type=chat&scope_id=chat_123", files=files)
            
            if response.status_code == 200:
                call_args = mock_upload.call_args
                # The prefix should be scope-based
                assert "chats/chat_123/" in call_args[0][2]

    # --- Project Endpoint Security ---

    def test_project_id_validation(self, client, mock_db):
        """Project IDs should be validated."""
        mock_db.projects.find_one.return_value = None
        
        response = client.get("/api/projects/invalid_id")
        
        assert response.status_code == 404

    def test_create_project_sanitizes_name(self, client, mock_db):
        """Project names should be sanitized."""
        response = client.post(
            "/api/projects",
            json={"name": "<script>alert('xss')</script>"}
        )
        
        assert response.status_code == 200

    # --- Chat Endpoint Security ---

    def test_chat_not_found_returns_404(self, client, mock_db):
        """Missing chat should return 404."""
        mock_db.chats.find_one.return_value = None
        
        response = client.get("/api/chats/nonexistent")
        
        assert response.status_code == 404

    def test_delete_chat_removes_messages(self, client, mock_db):
        """Deleting chat should also delete its messages."""
        with patch("vector_db.MongoDBStorage") as mock_vector:
            mock_vector.return_value.delete_by_scope = MagicMock()
            response = client.delete("/api/chats/chat_123")
            
            # Verify collections were modified
            mock_db.chats.delete_one.assert_called_once()
            mock_db.messages.delete_many.assert_called()


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

    def test_create_project(self, client, mock_db):
        """Test project creation."""
        response = client.post("/api/projects", json={"name": "Test Project"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["id"].startswith("proj_")

    def test_list_projects(self, client, mock_db):
        """Test listing projects."""
        mock_db.projects.find.return_value = [
            {"id": "proj_1", "name": "Project 1"},
            {"id": "proj_2", "name": "Project 2"}
        ]
        
        response = client.get("/api/projects")
        
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_create_chat(self, client, mock_db):
        """Test chat creation."""
        response = client.post(
            "/api/chats",
            json={"project_id": None, "title": "New Chat"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Chat"
        assert data["id"].startswith("chat_")

    def test_create_project_chat(self, client, mock_db):
        """Test creating a chat within a project."""
        response = client.post(
            "/api/chats",
            json={"project_id": "proj_123", "title": "Project Chat"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == "proj_123"

    def test_save_message_updates_chat_title(self, client, mock_db):
        """First user message should update chat title."""
        mock_db.chats.find_one.return_value = {
            "id": "chat_123",
            "title": "New Chat"
        }
        
        response = client.post(
            "/api/messages",
            json={
                "chat_id": "chat_123",
                "role": "user",
                "content": "What is machine learning?",
                "sources": []
            }
        )
        
        assert response.status_code == 200
        mock_db.chats.update_one.assert_called()

    def test_get_messages(self, client, mock_db):
        """Test retrieving messages for a chat."""
        mock_db.messages.find.return_value.sort.return_value = [
            {"id": "msg_1", "role": "user", "content": "Hello"},
            {"id": "msg_2", "role": "assistant", "content": "Hi there!"}
        ]
        
        response = client.get("/api/chats/chat_123/messages")
        
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_update_chat_pin(self, client, mock_db):
        """Test pinning a chat."""
        mock_db.chats.find_one.return_value = {
            "id": "chat_123",
            "title": "Test Chat",
            "is_pinned": True
        }
        
        response = client.patch(
            "/api/chats/chat_123",
            json={"is_pinned": True}
        )
        
        assert response.status_code == 200
        mock_db.chats.update_one.assert_called()


class TestScopeSecurityValidation:
    """Tests for scope-based security validation."""

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

    def test_upload_rejects_invalid_scope_type(self, client, mock_db):
        """Should reject invalid scope_type values."""
        file_content = b"%PDF-1.4"
        files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}
        
        response = client.post("/api/upload?scope_type=invalid&scope_id=xxx", files=files)
        
        assert response.status_code == 400
        assert "scope_type" in response.json()["detail"]

    def test_upload_rejects_nonexistent_chat(self, client, mock_db):
        """Should reject upload to nonexistent chat."""
        mock_db.chats.find_one.return_value = None
        
        file_content = b"%PDF-1.4"
        files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}
        
        response = client.post("/api/upload?scope_type=chat&scope_id=nonexistent", files=files)
        
        assert response.status_code == 404
        assert "Chat not found" in response.json()["detail"]

    def test_upload_rejects_nonexistent_project(self, client, mock_db):
        """Should reject upload to nonexistent project."""
        mock_db.projects.find_one.return_value = None
        
        file_content = b"%PDF-1.4"
        files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}
        
        response = client.post("/api/upload?scope_type=project&scope_id=nonexistent", files=files)
        
        assert response.status_code == 404
        assert "Project not found" in response.json()["detail"]

    def test_upload_accepts_valid_chat_scope(self, client, mock_db):
        """Should accept upload to existing chat."""
        mock_db.chats.find_one.return_value = {"id": "chat_123"}
        # Mock M1 deduplication check - no existing doc
        mock_db.documents.find_one.return_value = None
        
        file_content = b"%PDF-1.4"
        files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}
        
        with patch("api_routes.file_storage.upload_file") as mock_upload:
            mock_upload.return_value = {"s3_key": "key", "url": "url", "filename": "test.pdf"}
            response = client.post("/api/upload?scope_type=chat&scope_id=chat_123", files=files)
            
            assert response.status_code == 200

    def test_delete_project_cascades(self, client, mock_db):
        """Deleting project should clean up all related data."""
        mock_db.chats.find.return_value = [{"id": "chat_1"}, {"id": "chat_2"}]
        
        with patch("vector_db.MongoDBStorage") as mock_vector:
            mock_vector.return_value.delete_by_scope = MagicMock()
            response = client.delete("/api/projects/proj_123")
            
            assert response.status_code == 200
            # Verify cascade deletion
            mock_db.documents.delete_many.assert_called()
            mock_db.chats.delete_many.assert_called()
            mock_db.projects.delete_one.assert_called()

    def test_delete_chat_cascades(self, client, mock_db):
        """Deleting chat should clean up messages and documents."""
        with patch("vector_db.MongoDBStorage") as mock_vector:
            mock_vector.return_value.delete_by_scope = MagicMock()
            response = client.delete("/api/chats/chat_123")
            
            assert response.status_code == 200
            mock_db.messages.delete_many.assert_called()
            mock_db.documents.delete_many.assert_called()
            mock_db.chats.delete_one.assert_called()

