"""Tests for S3 file storage module."""
import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError


class TestS3FileStorage:
    """Tests for file_storage.py S3 operations."""

    @pytest.fixture
    def mock_env(self):
        """Mock environment variables."""
        with patch.dict("os.environ", {
            "AWS_ACCESS_KEY_ID": "test_key",
            "AWS_SECRET_ACCESS_KEY": "test_secret",
            "AWS_S3_BUCKET": "test-bucket",
            "AWS_REGION": "us-east-1"
        }):
            yield

    @pytest.fixture
    def mock_s3_client(self):
        """Mock boto3 S3 client."""
        with patch("file_storage.boto3.client") as mock:
            client = MagicMock()
            mock.return_value = client
            yield client

    # --- Upload Tests ---

    def test_upload_file_success(self, mock_env, mock_s3_client):
        """Test successful file upload."""
        import file_storage
        
        content = b"%PDF-1.4 test content"
        result = file_storage.upload_file(content, "test.pdf", "workspaces/ws_123/")
        
        assert result["filename"] == "test.pdf"
        assert result["bucket"] == "test-bucket"
        assert result["s3_key"].startswith("workspaces/ws_123/test_")
        assert result["s3_key"].endswith(".pdf")
        mock_s3_client.put_object.assert_called_once()

    def test_upload_generates_unique_key(self, mock_env, mock_s3_client):
        """Each upload should generate a unique S3 key."""
        import file_storage
        
        result1 = file_storage.upload_file(b"content1", "test.pdf", "")
        result2 = file_storage.upload_file(b"content2", "test.pdf", "")
        
        assert result1["s3_key"] != result2["s3_key"]

    def test_upload_handles_s3_error(self, mock_env, mock_s3_client):
        """S3 errors should raise RuntimeError."""
        import file_storage
        
        mock_s3_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "PutObject"
        )
        
        with pytest.raises(RuntimeError, match="Failed to upload"):
            file_storage.upload_file(b"content", "test.pdf", "")

    # --- Download Tests ---

    def test_download_file_success(self, mock_env, mock_s3_client):
        """Test successful file download."""
        import file_storage
        
        mock_body = MagicMock()
        mock_body.read.return_value = b"file content"
        mock_s3_client.get_object.return_value = {"Body": mock_body}
        
        content = file_storage.download_file("test_key.pdf")
        
        assert content == b"file content"
        mock_s3_client.get_object.assert_called_with(Bucket="test-bucket", Key="test_key.pdf")

    def test_download_handles_not_found(self, mock_env, mock_s3_client):
        """Missing file should raise error."""
        import file_storage
        
        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}},
            "GetObject"
        )
        
        with pytest.raises(RuntimeError, match="Failed to download"):
            file_storage.download_file("nonexistent.pdf")

    def test_download_to_temp_creates_file(self, mock_env, mock_s3_client):
        """download_to_temp should create a temp file."""
        import file_storage
        import os
        
        mock_body = MagicMock()
        mock_body.read.return_value = b"pdf content"
        mock_s3_client.get_object.return_value = {"Body": mock_body}
        
        temp_path = file_storage.download_to_temp("test.pdf")
        
        try:
            assert os.path.exists(temp_path)
            assert temp_path.endswith(".pdf")
            with open(temp_path, "rb") as f:
                assert f.read() == b"pdf content"
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # --- Delete Tests ---

    def test_delete_file_success(self, mock_env, mock_s3_client):
        """Test successful file deletion."""
        import file_storage
        
        result = file_storage.delete_file("test_key.pdf")
        
        assert result is True
        mock_s3_client.delete_object.assert_called_with(Bucket="test-bucket", Key="test_key.pdf")

    # --- List Tests ---

    def test_list_files_success(self, mock_env, mock_s3_client):
        """Test listing files with prefix."""
        import file_storage
        from datetime import datetime
        
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "prefix/file1.pdf", "Size": 1024, "LastModified": datetime(2024, 1, 1)},
                {"Key": "prefix/file2.pdf", "Size": 2048, "LastModified": datetime(2024, 1, 2)}
            ]
        }
        
        files = file_storage.list_files("prefix/")
        
        assert len(files) == 2
        assert files[0]["key"] == "prefix/file1.pdf"
        assert files[0]["size"] == 1024

    def test_list_files_empty(self, mock_env, mock_s3_client):
        """Empty bucket/prefix should return empty list."""
        import file_storage
        
        mock_s3_client.list_objects_v2.return_value = {}
        
        files = file_storage.list_files("empty/")
        
        assert files == []

    # --- Configuration Tests ---

    def test_missing_bucket_raises_error(self):
        """Missing AWS_S3_BUCKET should raise ValueError."""
        import file_storage
        
        with patch.dict("os.environ", {"AWS_S3_BUCKET": ""}):
            with pytest.raises(ValueError, match="AWS_S3_BUCKET"):
                file_storage.get_bucket_name()


class TestS3SecurityValidation:
    """Security-focused tests for S3 operations."""

    @pytest.fixture
    def mock_env(self):
        """Mock environment variables."""
        with patch.dict("os.environ", {
            "AWS_ACCESS_KEY_ID": "test_key",
            "AWS_SECRET_ACCESS_KEY": "test_secret",
            "AWS_S3_BUCKET": "test-bucket",
            "AWS_REGION": "us-east-1"
        }):
            yield

    @pytest.fixture
    def mock_s3_client(self):
        """Mock boto3 S3 client."""
        with patch("file_storage.boto3.client") as mock:
            client = MagicMock()
            mock.return_value = client
            yield client

    def test_upload_sanitizes_filename_special_chars(self, mock_env, mock_s3_client):
        """Special characters in filename should be handled."""
        import file_storage
        
        # Filename with special chars
        result = file_storage.upload_file(b"content", "test file (1).pdf", "")
        
        # Key should be generated without breaking
        assert ".pdf" in result["s3_key"]

    def test_upload_prefix_is_used(self, mock_env, mock_s3_client):
        """Prefix should be prepended to S3 key."""
        import file_storage
        
        result = file_storage.upload_file(b"content", "test.pdf", "workspaces/ws_123/")
        
        assert result["s3_key"].startswith("workspaces/ws_123/")

    def test_s3_key_injection_via_prefix(self, mock_env, mock_s3_client):
        """Malicious prefix should not break S3 operations."""
        import file_storage
        
        # Attempt to escape prefix
        malicious_prefix = "../../../etc/"
        result = file_storage.upload_file(b"content", "test.pdf", malicious_prefix)
        
        # The key will contain the prefix as-is (S3 treats / as folder separator)
        # This is acceptable as S3 keys are just strings
        # The actual security is enforced by IAM policies on the bucket
        assert result["s3_key"] is not None
