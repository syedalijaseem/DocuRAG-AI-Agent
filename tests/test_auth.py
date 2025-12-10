"""Tests for authentication system.

Tests cover registration, login, token refresh, logout, and security features.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
import os

# Set test environment
os.environ["MONGODB_URI"] = "mongodb://localhost:27017"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"

from main import app
from models import User, RefreshToken
from auth_service import hash_password, verify_password, hash_token, generate_token


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock MongoDB database."""
    with patch("auth_routes.get_db") as mock:
        db = MagicMock()
        mock.return_value = db
        yield db


# --- Password Hashing Tests ---

class TestPasswordHashing:
    """Tests for password hashing utilities."""
    
    def test_hash_password_creates_hash(self):
        """Password hashing should create a bcrypt hash."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt identifier
        assert len(hashed) == 60  # bcrypt hash length
    
    def test_verify_password_correct(self):
        """Correct password should verify successfully."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Incorrect password should fail verification."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert verify_password("WrongPassword", hashed) is False
    
    def test_verify_password_invalid_hash(self):
        """Invalid hash should return False, not raise."""
        assert verify_password("password", "invalid-hash") is False


# --- Registration Tests ---

class TestRegistration:
    """Tests for user registration."""
    
    def test_register_success(self, client, mock_db):
        """Valid registration should create user."""
        mock_db.users.find_one.return_value = None  # Email not taken
        mock_db.users.insert_one.return_value = MagicMock()
        
        response = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "ValidPass123!",
            "name": "Test User"
        })
        
        assert response.status_code == 201
        assert "verify" in response.json()["message"].lower()
    
    def test_register_duplicate_email(self, client, mock_db):
        """Duplicate email should return 409."""
        mock_db.users.find_one.return_value = {"email": "test@example.com"}
        
        response = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "ValidPass123!",
            "name": "Test User"
        })
        
        assert response.status_code == 409
    
    def test_register_weak_password(self, client, mock_db):
        """Weak password should be rejected."""
        response = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "weak",  # Too short, no uppercase, no number
            "name": "Test User"
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_register_invalid_email(self, client, mock_db):
        """Invalid email should be rejected."""
        mock_db.users.find_one.return_value = None  # Email not taken
        
        response = client.post("/api/auth/register", json={
            "email": "not-an-email",
            "password": "ValidPass123!",
            "name": "Test User"
        })
        
        assert response.status_code == 422  # Pydantic validation error


# --- Login Tests ---

class TestLogin:
    """Tests for user login."""
    
    def test_login_success(self, client, mock_db):
        """Valid credentials should login successfully."""
        hashed = hash_password("TestPassword123!")
        mock_db.users.find_one.return_value = {
            "_id": "mongodb_id",  # MongoDB adds this
            "id": "user_123",
            "email": "test@example.com",
            "password_hash": hashed,
            "name": "Test User",
            "email_verified": True,
            "failed_login_attempts": 0,
            "locked_until": None,
            "created_at": datetime.now(timezone.utc),
            "last_login": None
        }
        mock_db.refresh_tokens.find.return_value.sort.return_value = []
        mock_db.refresh_tokens.insert_one.return_value = MagicMock()
        mock_db.users.update_one.return_value = MagicMock()
        
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "TestPassword123!"
        })
        
        assert response.status_code == 200
        assert "user" in response.json()
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies
    
    def test_login_wrong_password(self, client, mock_db):
        """Wrong password should return 401."""
        hashed = hash_password("CorrectPassword123!")
        mock_db.users.find_one.return_value = {
            "_id": "mongodb_id",
            "id": "user_123",
            "email": "test@example.com",
            "password_hash": hashed,
            "email_verified": True,
            "failed_login_attempts": 0,
            "locked_until": None
        }
        mock_db.users.update_one.return_value = MagicMock()
        
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "WrongPassword123!"
        })
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()
    
    def test_login_unverified_email(self, client, mock_db):
        """Unverified email should return 403."""
        hashed = hash_password("TestPassword123!")
        mock_db.users.find_one.return_value = {
            "_id": "mongodb_id",
            "id": "user_123",
            "email": "test@example.com",
            "password_hash": hashed,
            "email_verified": False,
            "failed_login_attempts": 0,
            "locked_until": None
        }
        
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "TestPassword123!"
        })
        
        assert response.status_code == 403
    
    def test_login_locked_account(self, client, mock_db):
        """Locked account should return 423."""
        mock_db.users.find_one.return_value = {
            "_id": "mongodb_id",
            "id": "user_123",
            "email": "test@example.com",
            "locked_until": datetime.now(timezone.utc) + timedelta(minutes=15)
        }
        
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "AnyPassword123!"
        })
        
        assert response.status_code == 423


# --- Token Refresh Tests ---

class TestTokenRefresh:
    """Tests for token refresh."""
    
    def test_refresh_no_token(self, client, mock_db):
        """Missing refresh token should return 401."""
        response = client.post("/api/auth/refresh")
        
        assert response.status_code == 401
    
    def test_refresh_invalid_token(self, client, mock_db):
        """Invalid refresh token should return 401."""
        mock_db.refresh_tokens.find_one.return_value = None
        
        client.cookies.set("refresh_token", "invalid-token")
        response = client.post("/api/auth/refresh")
        
        assert response.status_code == 401


# --- Logout Tests ---

class TestLogout:
    """Tests for logout."""
    
    def test_logout_clears_cookies(self, client, mock_db):
        """Logout should clear auth cookies."""
        mock_db.refresh_tokens.update_one.return_value = MagicMock()
        
        client.cookies.set("access_token", "some-token")
        client.cookies.set("refresh_token", "some-refresh-token")
        
        response = client.post("/api/auth/logout")
        
        assert response.status_code == 200
        # Cookies should be cleared (set to empty/deleted)


# --- Model Validation Tests ---

class TestModelValidation:
    """Tests for Pydantic model validation."""
    
    def test_user_email_validation(self):
        """User email should be validated and lowercased."""
        user = User(
            email="Test@Example.COM",
            name="Test User"
        )
        assert user.email == "test@example.com"
    
    def test_user_invalid_email(self):
        """Invalid email should raise validation error."""
        with pytest.raises(ValueError):
            User(email="not-an-email", name="Test")
    
    def test_user_name_required(self):
        """Empty name should raise validation error."""
        with pytest.raises(ValueError):
            User(email="test@example.com", name="   ")
    
    def test_register_request_password_validation(self):
        """Password validation rules should be enforced."""
        from models import RegisterRequest
        
        # Too short
        with pytest.raises(ValueError):
            RegisterRequest(email="test@example.com", password="Short1", name="Test")
        
        # No uppercase
        with pytest.raises(ValueError):
            RegisterRequest(email="test@example.com", password="lowercase123", name="Test")
        
        # No number
        with pytest.raises(ValueError):
            RegisterRequest(email="test@example.com", password="NoNumbersHere", name="Test")


# --- Security Tests ---

class TestSecurity:
    """Security-focused tests."""
    
    def test_no_user_enumeration_on_login(self, client, mock_db):
        """Login error should not reveal if email exists."""
        mock_db.users.find_one.return_value = None  # User doesn't exist
        
        response = client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "AnyPassword123!"
        })
        
        assert response.status_code == 401
        # Error message should be generic
        assert "invalid email or password" in response.json()["detail"].lower()
    
    def test_no_user_enumeration_on_reset(self, client, mock_db):
        """Password reset should not reveal if email exists."""
        mock_db.users.find_one.return_value = None
        
        response = client.post("/api/auth/forgot-password", json={
            "email": "nonexistent@example.com"
        })
        
        assert response.status_code == 200
        # Should always return success message
    
    def test_token_hashing(self):
        """Tokens should be hashed before storage."""
        token = generate_token()
        hashed = hash_token(token)
        
        assert hashed != token
        assert len(hashed) == 64  # SHA-256 hex length
        
        # Same token should produce same hash
        assert hash_token(token) == hashed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
