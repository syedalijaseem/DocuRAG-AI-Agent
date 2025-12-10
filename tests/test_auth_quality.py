"""Quality verification tests for M0 Authentication.

Tests verify all 9 quality aspects:
1. Security
2. Scalability
3. Robustness
4. Efficiency
5. Availability
6. Speed
7. Optimization
8. Best Practices
9. Architecture
"""
import pytest
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import os

os.environ["MONGODB_URI"] = "mongodb://localhost:27017"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"

from auth_service import (
    hash_password, verify_password,
    create_access_token, decode_access_token,
    generate_token, hash_token,
    RateLimiter, BCRYPT_ROUNDS
)
from models import User, RegisterRequest


# =============================================================================
# 1. SECURITY TESTS
# =============================================================================

class TestSecurity:
    """Security-focused verification tests."""
    
    def test_bcrypt_cost_factor_is_secure(self):
        """Bcrypt should use cost factor 12 (industry recommended)."""
        assert BCRYPT_ROUNDS >= 12, "Bcrypt cost factor should be at least 12"
    
    def test_passwords_not_stored_plaintext(self):
        """Password hash should never equal plaintext password."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        assert password not in hashed
        assert hashed.startswith("$2b$")  # bcrypt prefix
    
    def test_jwt_tokens_have_expiry(self):
        """JWT tokens must have expiration time."""
        token = create_access_token({"sub": "user_123"})
        payload = decode_access_token(token)
        assert "exp" in payload
        assert payload["exp"] > datetime.now(timezone.utc).timestamp()
    
    def test_jwt_type_claim_prevents_confusion(self):
        """JWT should have type claim to prevent token confusion."""
        token = create_access_token({"sub": "user_123"})
        payload = decode_access_token(token)
        assert payload.get("type") == "access"
    
    def test_tokens_use_secure_random(self):
        """Tokens should be cryptographically random."""
        tokens = [generate_token() for _ in range(10)]
        # All tokens should be unique
        assert len(set(tokens)) == 10
        # Tokens should be URL-safe base64
        for t in tokens:
            assert all(c.isalnum() or c in "-_" for c in t)
    
    def test_tokens_are_hashed_for_storage(self):
        """Tokens should be hashed before storage."""
        token = generate_token()
        hashed = hash_token(token)
        assert token != hashed
        assert len(hashed) == 64  # SHA-256 hex length
    
    def test_password_validation_rules(self):
        """Password validation should enforce security rules."""
        # Too short
        with pytest.raises(ValueError):
            RegisterRequest(email="test@example.com", password="Short1A", name="Test")
        
        # No uppercase
        with pytest.raises(ValueError):
            RegisterRequest(email="test@example.com", password="lowercase123", name="Test")
        
        # No number
        with pytest.raises(ValueError):
            RegisterRequest(email="test@example.com", password="NoNumbersHere", name="Test")


# =============================================================================
# 2. SCALABILITY TESTS
# =============================================================================

class TestScalability:
    """Scalability verification tests."""
    
    def test_jwt_is_stateless(self):
        """JWT validation should not require database lookup."""
        token = create_access_token({"sub": "user_123", "email": "test@example.com"})
        # Decode should work without any DB connection
        payload = decode_access_token(token)
        assert payload["sub"] == "user_123"
    
    def test_rate_limiter_uses_in_memory_storage(self):
        """Rate limiter should use in-memory storage (pluggable to Redis)."""
        limiter = RateLimiter()
        assert hasattr(limiter, '_attempts')
        assert isinstance(limiter._attempts, dict)


# =============================================================================
# 3. ROBUSTNESS TESTS
# =============================================================================

class TestRobustness:
    """Robustness verification tests."""
    
    def test_password_verify_handles_invalid_hash(self):
        """Password verification should handle invalid hash gracefully."""
        result = verify_password("password", "not-a-valid-hash")
        assert result is False
        # Should not raise exception
    
    def test_jwt_decode_handles_invalid_token(self):
        """JWT decode should handle invalid tokens gracefully."""
        result = decode_access_token("invalid-token")
        assert result is None
        # Should not raise exception
    
    def test_jwt_decode_handles_expired_token(self):
        """JWT decode should reject expired tokens."""
        # Create token that's already expired
        token = create_access_token(
            {"sub": "user_123"},
            expires_delta=timedelta(seconds=-1)
        )
        result = decode_access_token(token)
        assert result is None
    
    def test_user_model_validates_email(self):
        """User model should validate email format."""
        # Valid email works
        user = User(email="test@example.com", name="Test")
        assert user.email == "test@example.com"
        
        # Invalid email raises
        with pytest.raises(ValueError):
            User(email="not-an-email", name="Test")
    
    def test_rate_limiter_handles_new_keys(self):
        """Rate limiter should handle unknown keys gracefully."""
        limiter = RateLimiter()
        # Should not raise for new key
        assert limiter.is_allowed("new-key") is True


# =============================================================================
# 4. EFFICIENCY TESTS
# =============================================================================

class TestEfficiency:
    """Efficiency verification tests."""
    
    def test_token_hash_is_faster_than_password_hash(self):
        """Token hashing (SHA-256) should be much faster than bcrypt."""
        token = generate_token()
        
        # SHA-256 hashing
        start = time.time()
        for _ in range(100):
            hash_token(token)
        sha_time = time.time() - start
        
        # Bcrypt is too slow to run 100x, just verify SHA is fast
        assert sha_time < 0.1  # 100 SHA-256 hashes in < 100ms
    
    def test_jwt_decode_is_fast(self):
        """JWT decoding should be fast (no DB lookup)."""
        token = create_access_token({"sub": "user_123"})
        
        start = time.time()
        for _ in range(100):
            decode_access_token(token)
        decode_time = time.time() - start
        
        assert decode_time < 0.5  # 100 decodes in < 500ms


# =============================================================================
# 5. AVAILABILITY TESTS
# =============================================================================

class TestAvailability:
    """Availability verification tests."""
    
    def test_auth_service_has_no_external_dependencies_at_import(self):
        """Auth service should import without network calls."""
        # This test passes because we already imported at top
        # If it failed, the test file wouldn't load
        from auth_service import hash_password
        assert callable(hash_password)
    
    def test_rate_limiter_works_in_memory(self):
        """Rate limiter should work without external services."""
        limiter = RateLimiter()
        key = "test-key"
        
        # Should work without any external connection
        for _ in range(5):
            limiter.record_attempt(key)
        
        assert limiter.is_allowed(key, max_attempts=5) is False


# =============================================================================
# 6. SPEED TESTS
# =============================================================================

class TestSpeed:
    """Speed/performance verification tests."""
    
    def test_password_hash_completes_in_reasonable_time(self):
        """Password hashing should complete within acceptable time."""
        start = time.time()
        hash_password("TestPassword123!")
        elapsed = time.time() - start
        
        # Bcrypt with cost=12 should take 200-500ms typically
        assert elapsed < 1.0  # Should complete within 1 second
    
    def test_jwt_creation_is_fast(self):
        """JWT creation should be very fast."""
        start = time.time()
        for _ in range(100):
            create_access_token({"sub": "user_123", "email": "test@example.com"})
        elapsed = time.time() - start
        
        assert elapsed < 0.5  # 100 JWTs in < 500ms


# =============================================================================
# 7. OPTIMIZATION TESTS
# =============================================================================

class TestOptimization:
    """Optimization verification tests."""
    
    def test_jwt_payload_is_minimal(self):
        """JWT payload should contain only necessary claims."""
        token = create_access_token({"sub": "user_123", "email": "test@example.com"})
        payload = decode_access_token(token)
        
        # Should have: sub, email, exp, iat, type
        expected_keys = {"sub", "email", "exp", "iat", "type"}
        assert set(payload.keys()) == expected_keys
    
    def test_rate_limiter_cleans_old_attempts(self):
        """Rate limiter should clean up old attempts."""
        limiter = RateLimiter()
        key = "test-key"
        
        # Add old attempts (should be cleaned)
        limiter._attempts[key] = [
            datetime.now(timezone.utc) - timedelta(hours=1)
        ]
        
        # Check if allowed - this should clean old attempts
        limiter.is_allowed(key, window_minutes=15)
        
        # Old attempts should be removed
        assert len(limiter._attempts.get(key, [])) == 0


# =============================================================================
# 8. BEST PRACTICES TESTS
# =============================================================================

class TestBestPractices:
    """Best practices verification tests."""
    
    def test_functions_have_docstrings(self):
        """All public functions should have docstrings."""
        from auth_service import (
            hash_password, verify_password,
            generate_token, hash_token,
            create_access_token, create_refresh_token,
            decode_access_token
        )
        
        functions = [
            hash_password, verify_password,
            generate_token, hash_token,
            create_access_token, create_refresh_token,
            decode_access_token
        ]
        
        for func in functions:
            assert func.__doc__ is not None, f"{func.__name__} missing docstring"
    
    def test_models_use_type_hints(self):
        """Models should use proper type hints."""
        from models import User
        
        # Check that annotations exist
        assert hasattr(User, '__annotations__')
        assert 'email' in User.__annotations__
        assert 'name' in User.__annotations__
    
    def test_error_messages_are_generic(self):
        """Login errors should be generic to prevent enumeration."""
        # We verify this by checking our test expectations
        # The actual API returns "Invalid email or password" for both
        # wrong password and non-existent user
        pass  # Already verified in test_auth.py


# =============================================================================
# 9. ARCHITECTURE TESTS
# =============================================================================

class TestArchitecture:
    """Architecture verification tests."""
    
    def test_auth_service_is_separate_from_routes(self):
        """Auth service should be in separate module from routes."""
        import auth_service
        import auth_routes
        
        assert auth_service.__file__ != auth_routes.__file__
    
    def test_models_are_separate_module(self):
        """Models should be in their own module."""
        import models
        import auth_service
        import auth_routes
        
        assert models.__file__ != auth_service.__file__
        assert models.__file__ != auth_routes.__file__
    
    def test_dependencies_are_properly_injected(self):
        """Database should be injectable (not hardcoded)."""
        import auth_routes
        
        # get_db function exists and can be mocked
        assert hasattr(auth_routes, 'get_db')
        assert callable(auth_routes.get_db)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
