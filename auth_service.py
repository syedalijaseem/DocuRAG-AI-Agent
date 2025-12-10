"""Authentication service module.

Provides password hashing, JWT generation/validation, and token utilities.
"""
import os
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---

# JWT Settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")  # Use RS256 in production with key pair
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Bcrypt cost factor (12 is recommended for security)
BCRYPT_ROUNDS = 12


# --- Password Utilities ---

def hash_password(password: str) -> str:
    """Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    # Encode to bytes
    password_bytes = password.encode('utf-8')
    # Generate salt and hash
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.
    
    Args:
        plain_password: Password to verify
        hashed_password: Stored hash to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


# --- Token Utilities ---

def generate_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token.
    
    Args:
        length: Token length in bytes (actual string will be longer)
        
    Returns:
        URL-safe base64 encoded token
    """
    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    """Hash a token for secure storage.
    
    Uses SHA-256 for token hashing (faster than bcrypt, 
    appropriate for high-entropy random tokens).
    
    Args:
        token: Token to hash
        
    Returns:
        Hex-encoded SHA-256 hash
    """
    return hashlib.sha256(token.encode()).hexdigest()


# --- JWT Functions ---

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token.
    
    Args:
        data: Payload data (typically {"sub": user_id, "email": email})
        expires_delta: Custom expiration time
        
    Returns:
        Encoded JWT string
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None
) -> tuple[str, str, datetime]:
    """Create a refresh token.
    
    Args:
        user_id: User ID to associate with token
        expires_delta: Custom expiration time
        
    Returns:
        Tuple of (raw_token, hashed_token, expires_at)
    """
    raw_token = generate_token(32)
    hashed = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    return raw_token, hashed, expires_at


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token.
    
    Args:
        token: JWT string
        
    Returns:
        Decoded payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token, 
            JWT_SECRET_KEY, 
            algorithms=[JWT_ALGORITHM]
        )
        # Verify it's an access token
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def get_token_expiry(token: str) -> Optional[datetime]:
    """Get the expiration time of a token without full validation.
    
    Args:
        token: JWT string
        
    Returns:
        Expiration datetime if valid structure, None otherwise
    """
    try:
        # Decode without verification to get expiry
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": False}
        )
        exp = payload.get("exp")
        if exp:
            return datetime.fromtimestamp(exp, tz=timezone.utc)
        return None
    except JWTError:
        return None


# --- Rate Limiting Helpers ---

class RateLimiter:
    """Simple in-memory rate limiter.
    
    For production, use Redis-based rate limiting.
    """
    
    def __init__(self):
        self._attempts: dict[str, list[datetime]] = {}
    
    def is_allowed(
        self, 
        key: str, 
        max_attempts: int = 5, 
        window_minutes: int = 15
    ) -> bool:
        """Check if an action is allowed under rate limit.
        
        Args:
            key: Unique identifier (e.g., email or IP)
            max_attempts: Maximum allowed attempts in window
            window_minutes: Time window in minutes
            
        Returns:
            True if allowed, False if rate limited
        """
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=window_minutes)
        
        # Get attempts for this key
        attempts = self._attempts.get(key, [])
        
        # Filter to attempts within window
        recent = [a for a in attempts if a > window_start]
        
        # Store updated list
        self._attempts[key] = recent
        
        return len(recent) < max_attempts
    
    def record_attempt(self, key: str) -> None:
        """Record an attempt for rate limiting.
        
        Args:
            key: Unique identifier
        """
        now = datetime.now(timezone.utc)
        if key not in self._attempts:
            self._attempts[key] = []
        self._attempts[key].append(now)
    
    def clear(self, key: str) -> None:
        """Clear attempts for a key (e.g., after successful login).
        
        Args:
            key: Unique identifier
        """
        if key in self._attempts:
            del self._attempts[key]


# Global rate limiter instances
login_rate_limiter = RateLimiter()
ip_rate_limiter = RateLimiter()
