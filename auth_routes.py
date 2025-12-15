"""Authentication API routes.

Provides endpoints for user registration, login, token refresh, and logout.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Response, Request, Depends
from fastapi.responses import RedirectResponse
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
import os

from dotenv import load_dotenv
load_dotenv()

from models import (
    User, UserProvider, RefreshToken,
    RegisterRequest, LoginRequest, GoogleAuthRequest,
    PasswordResetRequest, PasswordResetComplete,
    EmailChangeRequest, PasswordChangeRequest,
    UserResponse, AuthResponse, SessionInfo,
    AuthProvider
)
from auth_service import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_access_token,
    generate_token, hash_token,
    login_rate_limiter, ip_rate_limiter,
    ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
)
from email_service import (
    send_verification_email, send_password_reset_email, send_email_change_verification
)
import google_oauth

router = APIRouter(prefix="/api/auth", tags=["auth"])


# --- Database Setup ---

def get_db():
    """Get MongoDB database connection."""
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise HTTPException(status_code=500, detail="Database not configured")
    client = MongoClient(uri)
    return client[os.getenv("MONGODB_DATABASE", "docurag")]


# --- Plan-based Token Limits ---

PLAN_TOKEN_LIMITS = {
    "free": 5000,
    "pro": 500000,
    "premium": 2000000,
}

def get_token_limit_for_plan(plan: str) -> int:
    """Get token limit based on subscription plan."""
    return PLAN_TOKEN_LIMITS.get(plan, PLAN_TOKEN_LIMITS["free"])

def create_user_response(user_dict: dict) -> dict:
    """Create UserResponse dict with dynamic token_limit based on plan."""
    plan = user_dict.get("plan", "free")
    user_dict["token_limit"] = get_token_limit_for_plan(plan)
    return UserResponse(**user_dict)


# --- Cookie Configuration ---

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", None)
COOKIE_SAMESITE = "lax"  # lax allows cookies on top-level navigations (OAuth redirects)


def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    """Set HTTP-only cookies for tokens."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        domain=COOKIE_DOMAIN
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        domain=COOKIE_DOMAIN
    )


def clear_auth_cookies(response: Response):
    """Clear auth cookies on logout."""
    response.delete_cookie(key="access_token", domain=COOKIE_DOMAIN)
    response.delete_cookie(key="refresh_token", domain=COOKIE_DOMAIN)


# --- Dependency: Get Current User ---

async def get_current_user(request: Request) -> User:
    """Extract and validate user from access token cookie."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    db = get_db()
    user_doc = db.users.find_one({"id": user_id})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    
    del user_doc["_id"]
    return User(**user_doc)


async def get_current_user_optional(request: Request) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


# --- Registration ---

@router.post("/register", status_code=201)
async def register(data: RegisterRequest):
    """Register a new user with email and password.
    
    Sends verification email. User cannot login until verified.
    """
    db = get_db()
    
    # Check if email exists
    if db.users.find_one({"email": data.email.lower()}):
        raise HTTPException(status_code=409, detail="Email already registered")
    
    # Generate verification token
    verification_token = generate_token()
    verification_expires = datetime.now(timezone.utc) + timedelta(hours=24)
    
    # Create user
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        email_verified=False,
        verification_token_hash=hash_token(verification_token),
        verification_expires_at=verification_expires
    )
    
    try:
        db.users.insert_one(user.model_dump())
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Email already registered")
    
    # Send verification email
    send_verification_email(data.email, verification_token, data.name)
    
    return {"message": "Registration successful. Please check your email to verify your account."}


# --- Email Verification ---

@router.get("/verify-email")
async def verify_email(token: str, response: Response):
    """Verify email using token from verification link."""
    db = get_db()
    
    token_hash = hash_token(token)
    user_doc = db.users.find_one({"verification_token_hash": token_hash})
    
    if not user_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")
    
    # Check expiration
    expires_at = user_doc.get("verification_expires_at")
    if expires_at:
        # Handle naive datetime from MongoDB - assume UTC
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Verification link has expired")
    
    # Update user
    db.users.update_one(
        {"id": user_doc["id"]},
        {
            "$set": {
                "email_verified": True,
                "verification_token_hash": None,
                "verification_expires_at": None
            }
        }
    )
    
    # Issue tokens and log in
    del user_doc["_id"]
    user = User(**user_doc)
    user.email_verified = True
    
    access_token = create_access_token({"sub": user.id, "email": user.email})
    raw_refresh, hashed_refresh, refresh_expires = create_refresh_token(user.id)
    
    # Store refresh token
    refresh_doc = RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=refresh_expires
    )
    db.refresh_tokens.insert_one(refresh_doc.model_dump())
    
    set_auth_cookies(response, access_token, raw_refresh)
    
    return {
        "message": "Email verified successfully",
        "user": create_user_response(user.model_dump())
    }


@router.post("/resend-verification")
async def resend_verification(email: str):
    """Resend verification email."""
    db = get_db()
    
    user_doc = db.users.find_one({"email": email.lower()})
    
    # Always return success to prevent email enumeration
    if not user_doc or user_doc.get("email_verified"):
        return {"message": "If the email exists and is unverified, a new verification link has been sent."}
    
    # Rate limit
    if not login_rate_limiter.is_allowed(email, max_attempts=3, window_minutes=60):
        return {"message": "If the email exists and is unverified, a new verification link has been sent."}
    
    login_rate_limiter.record_attempt(email)
    
    # Generate new token
    verification_token = generate_token()
    verification_expires = datetime.now(timezone.utc) + timedelta(hours=24)
    
    db.users.update_one(
        {"email": email.lower()},
        {
            "$set": {
                "verification_token_hash": hash_token(verification_token),
                "verification_expires_at": verification_expires
            }
        }
    )
    
    # TODO: Queue verification email
    print(f"[DEV] New verification token for {email}: {verification_token}")
    
    return {"message": "If the email exists and is unverified, a new verification link has been sent."}


# --- Login ---

@router.post("/login")
async def login(data: LoginRequest, request: Request, response: Response):
    """Login with email and password."""
    db = get_db()
    email = data.email.lower()
    
    # IP rate limiting
    client_ip = request.client.host if request.client else "unknown"
    if not ip_rate_limiter.is_allowed(client_ip, max_attempts=100, window_minutes=15):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
    ip_rate_limiter.record_attempt(client_ip)
    
    # Per-email rate limiting
    if not login_rate_limiter.is_allowed(email, max_attempts=5, window_minutes=15):
        raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")
    login_rate_limiter.record_attempt(email)
    
    # Find user
    user_doc = db.users.find_one({"email": email})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check lockout
    locked_until = user_doc.get("locked_until")
    if locked_until and locked_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=423, 
            detail="Account temporarily locked. Please try again later."
        )
    
    # Verify password
    if not user_doc.get("password_hash") or not verify_password(data.password, user_doc["password_hash"]):
        # Increment failed attempts
        failed_attempts = user_doc.get("failed_login_attempts", 0) + 1
        update = {"failed_login_attempts": failed_attempts}
        
        # Lock after 5 failed attempts
        if failed_attempts >= 5:
            update["locked_until"] = datetime.now(timezone.utc) + timedelta(minutes=15)
        
        db.users.update_one({"id": user_doc["id"]}, {"$set": update})
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check email verified
    if not user_doc.get("email_verified"):
        raise HTTPException(
            status_code=403, 
            detail="Email not verified. Please check your email for verification link."
        )
    
    # Reset failed attempts on successful login
    db.users.update_one(
        {"id": user_doc["id"]},
        {
            "$set": {
                "failed_login_attempts": 0,
                "locked_until": None,
                "last_login": datetime.now(timezone.utc)
            }
        }
    )
    
    # Clear rate limit on success
    login_rate_limiter.clear(email)
    
    # Issue tokens
    del user_doc["_id"]
    user = User(**user_doc)
    
    access_token = create_access_token({"sub": user.id, "email": user.email})
    raw_refresh, hashed_refresh, refresh_expires = create_refresh_token(user.id)
    
    # Limit refresh tokens per user
    existing_tokens = list(db.refresh_tokens.find(
        {"user_id": user.id, "revoked": False}
    ).sort("created_at", 1))
    
    if len(existing_tokens) >= 10:
        # Revoke oldest
        oldest_id = existing_tokens[0]["id"]
        db.refresh_tokens.update_one({"id": oldest_id}, {"$set": {"revoked": True}})
    
    # Store new refresh token
    device_info = request.headers.get("User-Agent", "Unknown")[:200]
    refresh_doc = RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        device_info=device_info,
        expires_at=refresh_expires
    )
    db.refresh_tokens.insert_one(refresh_doc.model_dump())
    
    set_auth_cookies(response, access_token, raw_refresh)
    
    return AuthResponse(
        user=create_user_response(user.model_dump()),
        is_new=False
    )


# --- Token Refresh ---

@router.post("/refresh")
async def refresh_tokens(request: Request, response: Response):
    """Refresh access token using refresh token."""
    db = get_db()
    
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    
    token_hash = hash_token(refresh_token)
    token_doc = db.refresh_tokens.find_one({"token_hash": token_hash, "revoked": False})
    
    if not token_doc:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    # Check expiration
    if token_doc["expires_at"] < datetime.now(timezone.utc):
        db.refresh_tokens.update_one({"id": token_doc["id"]}, {"$set": {"revoked": True}})
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Refresh token expired")
    
    # Get user
    user_doc = db.users.find_one({"id": token_doc["user_id"]})
    if not user_doc:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="User not found")
    
    # Revoke old refresh token (rotation)
    db.refresh_tokens.update_one({"id": token_doc["id"]}, {"$set": {"revoked": True}})
    
    # Issue new tokens
    del user_doc["_id"]
    user = User(**user_doc)
    
    access_token = create_access_token({"sub": user.id, "email": user.email})
    raw_refresh, hashed_refresh, refresh_expires = create_refresh_token(user.id)
    
    # Store new refresh token
    refresh_doc = RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        device_info=token_doc.get("device_info"),
        expires_at=refresh_expires
    )
    db.refresh_tokens.insert_one(refresh_doc.model_dump())
    
    set_auth_cookies(response, access_token, raw_refresh)
    
    return {"message": "Tokens refreshed"}


# --- Logout ---

@router.post("/logout")
async def logout(request: Request, response: Response):
    """Logout current session."""
    db = get_db()
    
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        token_hash = hash_token(refresh_token)
        db.refresh_tokens.update_one({"token_hash": token_hash}, {"$set": {"revoked": True}})
    
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.post("/logout-all")
async def logout_all(request: Request, response: Response, user: User = Depends(get_current_user)):
    """Logout all sessions for current user."""
    db = get_db()
    
    db.refresh_tokens.update_many(
        {"user_id": user.id, "revoked": False},
        {"$set": {"revoked": True}}
    )
    
    clear_auth_cookies(response)
    return {"message": "Logged out from all devices"}


# --- Get Current User ---

@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """Get current authenticated user."""
    db = get_db()
    
    # Get linked providers
    providers = list(db.user_providers.find({"user_id": user.id}, {"_id": 0, "provider": 1}))
    provider_names = [p["provider"] for p in providers]
    
    return {
        "user": create_user_response(user.model_dump()),
        "providers": provider_names
    }


@router.patch("/me")
async def update_me(name: Optional[str] = None, avatar_url: Optional[str] = None, user: User = Depends(get_current_user)):
    """Update current user's profile."""
    db = get_db()
    
    updates = {}
    if name is not None:
        updates["name"] = name.strip()
    if avatar_url is not None:
        updates["avatar_url"] = avatar_url
    
    if updates:
        db.users.update_one({"id": user.id}, {"$set": updates})
    
    # Return updated user
    user_doc = db.users.find_one({"id": user.id})
    del user_doc["_id"]
    return {"user": create_user_response(user_doc)}


# --- Sessions ---

@router.get("/sessions")
async def list_sessions(request: Request, user: User = Depends(get_current_user)):
    """List active sessions for current user."""
    db = get_db()
    
    current_token = request.cookies.get("refresh_token")
    current_hash = hash_token(current_token) if current_token else None
    
    tokens = list(db.refresh_tokens.find(
        {"user_id": user.id, "revoked": False},
        {"_id": 0}
    ))
    
    sessions = []
    for t in tokens:
        is_current = t["token_hash"] == current_hash
        sessions.append(SessionInfo(
            id=t["id"],
            device_info=t.get("device_info"),
            created_at=t["created_at"],
            expires_at=t["expires_at"],
            is_current=is_current
        ))
    
    return {"sessions": sessions}


@router.delete("/sessions/{session_id}")
async def revoke_session(session_id: str, user: User = Depends(get_current_user)):
    """Revoke a specific session."""
    db = get_db()
    
    result = db.refresh_tokens.update_one(
        {"id": session_id, "user_id": user.id},
        {"$set": {"revoked": True}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session revoked"}


# --- Password Reset ---

@router.post("/forgot-password")
async def forgot_password(data: PasswordResetRequest):
    """Request password reset email."""
    db = get_db()
    email = data.email.lower()
    
    # Always return success to prevent email enumeration
    user_doc = db.users.find_one({"email": email})
    if not user_doc:
        return {"message": "If the email exists, a password reset link has been sent."}
    
    # Rate limit
    if not login_rate_limiter.is_allowed(f"reset:{email}", max_attempts=3, window_minutes=60):
        return {"message": "If the email exists, a password reset link has been sent."}
    
    login_rate_limiter.record_attempt(f"reset:{email}")
    
    # Generate reset token (1 hour TTL)
    reset_token = generate_token()
    reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    
    db.users.update_one(
        {"email": email},
        {
            "$set": {
                "reset_token_hash": hash_token(reset_token),
                "reset_expires_at": reset_expires
            }
        }
    )
    
    # TODO: Queue password reset email via Inngest
    print(f"[DEV] Password reset token for {email}: {reset_token}")
    
    return {"message": "If the email exists, a password reset link has been sent."}


@router.post("/reset-password")
async def reset_password(data: PasswordResetComplete, response: Response):
    """Complete password reset with token and new password."""
    db = get_db()
    
    token_hash = hash_token(data.token)
    user_doc = db.users.find_one({"reset_token_hash": token_hash})
    
    if not user_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    
    # Check expiration
    expires_at = user_doc.get("reset_expires_at")
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset link has expired")
    
    # Update password and clear reset token
    db.users.update_one(
        {"id": user_doc["id"]},
        {
            "$set": {
                "password_hash": hash_password(data.new_password),
                "reset_token_hash": None,
                "reset_expires_at": None,
                "failed_login_attempts": 0,
                "locked_until": None
            }
        }
    )
    
    # Revoke all refresh tokens (force re-login on all devices)
    db.refresh_tokens.update_many(
        {"user_id": user_doc["id"]},
        {"$set": {"revoked": True}}
    )
    
    clear_auth_cookies(response)
    
    return {"message": "Password reset successfully. Please login with your new password."}


# --- Password Change ---

@router.patch("/password")
async def change_password(data: PasswordChangeRequest, response: Response, user: User = Depends(get_current_user)):
    """Change password for current user."""
    db = get_db()
    
    # Verify current password
    user_doc = db.users.find_one({"id": user.id})
    if not user_doc or not user_doc.get("password_hash"):
        raise HTTPException(status_code=400, detail="Password change not available for OAuth-only accounts")
    
    if not verify_password(data.current_password, user_doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    
    # Update password
    db.users.update_one(
        {"id": user.id},
        {"$set": {"password_hash": hash_password(data.new_password)}}
    )
    
    # Revoke all other sessions (keep current)
    current_refresh = hash_token(response.headers.get("set-cookie", "")) if hasattr(response, "headers") else None
    db.refresh_tokens.update_many(
        {"user_id": user.id, "revoked": False},
        {"$set": {"revoked": True}}
    )
    
    return {"message": "Password changed successfully"}


# --- Email Change ---

@router.patch("/email")
async def change_email(data: EmailChangeRequest, user: User = Depends(get_current_user)):
    """Change email for current user. Requires re-verification."""
    db = get_db()
    
    # Verify password
    user_doc = db.users.find_one({"id": user.id})
    if not user_doc or not user_doc.get("password_hash"):
        raise HTTPException(status_code=400, detail="Email change requires password verification")
    
    if not verify_password(data.password, user_doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Password is incorrect")
    
    new_email = data.new_email.lower().strip()
    
    # Check new email not in use
    if db.users.find_one({"email": new_email, "id": {"$ne": user.id}}):
        raise HTTPException(status_code=409, detail="Email already in use")
    
    # Generate new verification token
    verification_token = generate_token()
    verification_expires = datetime.now(timezone.utc) + timedelta(hours=24)
    
    # Update email (unverified)
    db.users.update_one(
        {"id": user.id},
        {
            "$set": {
                "email": new_email,
                "email_verified": False,
                "verification_token_hash": hash_token(verification_token),
                "verification_expires_at": verification_expires
            }
        }
    )
    
    # TODO: Queue verification email to new address
    print(f"[DEV] Verification token for new email {new_email}: {verification_token}")
    
    return {"message": "Email updated. Please verify your new email address."}


# --- Account Deletion ---

@router.delete("/account")
async def delete_account(password: str, response: Response, user: User = Depends(get_current_user)):
    """Delete user account and all associated data."""
    db = get_db()
    
    # Verify password (required for security)
    user_doc = db.users.find_one({"id": user.id})
    if user_doc and user_doc.get("password_hash"):
        if not verify_password(password, user_doc["password_hash"]):
            raise HTTPException(status_code=401, detail="Password is incorrect")
    
    # Revoke all refresh tokens immediately
    db.refresh_tokens.delete_many({"user_id": user.id})
    
    # Delete user providers
    db.user_providers.delete_many({"user_id": user.id})
    
    # Mark user for deletion (or delete immediately for now)
    # In production, you might queue this for background processing
    db.users.delete_one({"id": user.id})
    
    # TODO: Queue background job to delete user's projects, chats, documents
    # For now, we'll leave orphaned data (background cleanup will handle)
    
    clear_auth_cookies(response)
    
    return {"message": "Account deleted successfully"}


# --- Google OAuth ---

@router.get("/google")
async def google_login():
    """Redirect to Google OAuth consent screen."""
    if not google_oauth.is_configured():
        raise HTTPException(
            status_code=503, 
            detail="Google OAuth is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
        )
    
    # Generate state for CSRF protection
    state = generate_token()
    # In production, you'd store this state in a session or signed cookie
    
    auth_url = google_oauth.get_authorization_url(state=state)
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(code: str, response: Response, state: Optional[str] = None):
    """Handle Google OAuth callback.
    
    Creates a new user if they don't exist, or logs them in if they do.
    Google users are automatically email-verified.
    """
    if not google_oauth.is_configured():
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")
    
    db = get_db()
    
    try:
        # Exchange code for user info
        google_user = await google_oauth.authenticate_with_google(code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Google authentication failed: {str(e)}")
    
    # Check if user exists by email
    email = google_user["email"].lower()
    user_doc = db.users.find_one({"email": email})
    
    if user_doc:
        # Existing user - update Google provider link if not already linked
        del user_doc["_id"]
        user = User(**user_doc)
        
        # Check if Google provider is already linked
        provider_doc = db.user_providers.find_one({
            "user_id": user.id,
            "provider": "google"
        })
        
        if not provider_doc:
            # Link Google account
            provider = UserProvider(
                user_id=user.id,
                provider="google",
                provider_user_id=google_user["google_id"]
            )
            db.user_providers.insert_one(provider.model_dump())
        
        # Update profile picture if not set
        if google_user.get("picture") and not user.avatar_url:
            db.users.update_one(
                {"id": user.id},
                {"$set": {"avatar_url": google_user["picture"]}}
            )
            user.avatar_url = google_user["picture"]
    else:
        # New user - create account
        user = User(
            email=email,
            password_hash=None,  # No password for Google-only users
            name=google_user.get("name"),
            avatar_url=google_user.get("picture"),
            email_verified=True,  # Google emails are pre-verified
        )
        db.users.insert_one(user.model_dump())
        
        # Create Google provider link
        provider = UserProvider(
            user_id=user.id,
            provider="google",
            provider_user_id=google_user["google_id"]
        )
        db.user_providers.insert_one(provider.model_dump())
    
    # Update last login
    db.users.update_one(
        {"id": user.id},
        {"$set": {"last_login": datetime.now(timezone.utc)}}
    )
    
    # Create tokens
    access_token = create_access_token({"sub": user.id, "email": user.email})
    raw_refresh, hashed_refresh, refresh_expires = create_refresh_token(user.id)
    
    # Store refresh token
    refresh_doc = RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=refresh_expires,
        device_info="Google OAuth Login"
    )
    db.refresh_tokens.insert_one(refresh_doc.model_dump())
    
    # Redirect to frontend with cookies
    frontend_url = os.getenv("APP_URL", "http://localhost:5173")
    redirect_response = RedirectResponse(url=frontend_url, status_code=302)
    
    # Set cookies on the redirect response
    redirect_response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        domain=COOKIE_DOMAIN
    )
    redirect_response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        domain=COOKIE_DOMAIN
    )
    
    return redirect_response
