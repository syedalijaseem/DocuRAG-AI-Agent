"""Tests for M3: Query Integration with project inheritance.

Tests for project-inherited search functionality.
"""
import pytest
from unittest.mock import patch, MagicMock

from chunk_search import get_document_ids_for_scope, search_for_scope


class TestProjectInheritedSearch:
    """Tests for project-inherited document search."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock MongoDB database."""
        with patch("chunk_search.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            yield mock_db
    
    def test_chat_includes_project_documents_when_project_id_provided(self, mock_db):
        """Test that chat search includes project docs when project_id given."""
        # Mock: chat has doc_1, project has doc_2
        mock_db.document_scopes.find.return_value = [
            {"document_id": "doc_chat"},
            {"document_id": "doc_project"}
        ]
        
        doc_ids = get_document_ids_for_scope(
            scope_type="chat",
            scope_id="chat_123",
            include_project=True,
            project_id="proj_456"
        )
        
        # Should query with $or for both chat and project
        call_args = mock_db.document_scopes.find.call_args
        query = call_args[0][0]
        assert "$or" in query
    
    def test_chat_excludes_project_when_include_project_false(self, mock_db):
        """Test chat search excludes project docs when include_project=False."""
        mock_db.document_scopes.find.return_value = [
            {"document_id": "doc_chat_only"}
        ]
        
        doc_ids = get_document_ids_for_scope(
            scope_type="chat",
            scope_id="chat_123",
            include_project=False,
            project_id="proj_456"  # Should be ignored
        )
        
        # Should NOT query with $or
        call_args = mock_db.document_scopes.find.call_args
        query = call_args[0][0]
        assert "$or" not in query
        assert query["scope_type"] == "chat"
    
    def test_chat_without_project_id_only_searches_chat(self, mock_db):
        """Test chat search without project_id only searches chat docs."""
        mock_db.document_scopes.find.return_value = [
            {"document_id": "doc_chat"}
        ]
        
        doc_ids = get_document_ids_for_scope(
            scope_type="chat",
            scope_id="chat_123",
            include_project=True,
            project_id=None  # No project
        )
        
        call_args = mock_db.document_scopes.find.call_args
        query = call_args[0][0]
        assert "$or" not in query
        assert query["scope_type"] == "chat"
    
    def test_project_scope_searches_only_project(self, mock_db):
        """Test project scope searches only project documents."""
        mock_db.document_scopes.find.return_value = [
            {"document_id": "doc_project"}
        ]
        
        doc_ids = get_document_ids_for_scope(
            scope_type="project",
            scope_id="proj_123",
            include_project=True,
            project_id=None
        )
        
        call_args = mock_db.document_scopes.find.call_args
        query = call_args[0][0]
        assert query["scope_type"] == "project"
        assert query["scope_id"] == "proj_123"


class TestSearchForScopeIntegration:
    """Integration tests for search_for_scope."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock MongoDB database."""
        with patch("chunk_search.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            
            # Default: no documents
            mock_db.document_scopes.find.return_value = []
            mock_db.chunks.aggregate.return_value = iter([])
            
            yield mock_db
    
    def test_search_with_project_inheritance_combines_results(self, mock_db):
        """Test that inherited search combines chat and project docs."""
        # Mock document scopes - both chat and project
        mock_db.document_scopes.find.return_value = [
            {"document_id": "doc_chat_1"},
            {"document_id": "doc_proj_1"}
        ]
        
        # Mock chunk search results
        mock_db.chunks.aggregate.return_value = iter([
            {"text": "Chat content", "page_number": 1, "score": 0.9, "filename": "chat.pdf"},
            {"text": "Project content", "page_number": 1, "score": 0.8, "filename": "project.pdf"}
        ])
        
        result = search_for_scope(
            query_vector=[0.1] * 1536,
            scope_type="chat",
            scope_id="chat_123",
            top_k=5,
            include_project=True,
            project_id="proj_456"
        )
        
        assert len(result["contexts"]) == 2
        assert "Chat content" in result["contexts"][0]
        assert "Project content" in result["contexts"][1]
    
    def test_search_returns_filename_in_sources(self, mock_db):
        """Test that search results include filenames from document lookup."""
        mock_db.document_scopes.find.return_value = [{"document_id": "doc_1"}]
        mock_db.chunks.aggregate.return_value = iter([
            {"text": "Content", "page_number": 3, "score": 0.95, "filename": "report.pdf"}
        ])
        
        result = search_for_scope(
            query_vector=[0.1] * 1536,
            scope_type="chat",
            scope_id="chat_123"
        )
        
        assert "report.pdf, page 3" in result["sources"][0]
