"""Google OAuth2 service for FastAPI.

Handles the OAuth2 flow for Google Sign-In:
1. Generate authorization URL
2. Exchange authorization code for tokens
3. Fetch user profile from Google
"""
import os
import httpx
from typing import Optional
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

# Google OAuth2 configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")

# Google OAuth2 endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def is_configured() -> bool:
    """Check if Google OAuth is properly configured."""
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def get_authorization_url(state: Optional[str] = None) -> str:
    """Generate the Google OAuth2 authorization URL.
    
    Args:
        state: Optional state parameter for CSRF protection
        
    Returns:
        The full authorization URL to redirect the user to
    """
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",  # Get refresh token
        "prompt": "consent",  # Always show consent screen for refresh token
    }
    
    if state:
        params["state"] = state
    
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict:
    """Exchange authorization code for access and ID tokens.
    
    Args:
        code: The authorization code from Google callback
        
    Returns:
        Dict with access_token, id_token, refresh_token, etc.
        
    Raises:
        Exception if token exchange fails
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": GOOGLE_REDIRECT_URI,
            },
        )
        
        if response.status_code != 200:
            raise Exception(f"Token exchange failed: {response.text}")
        
        return response.json()


async def get_user_info(access_token: str) -> dict:
    """Fetch user profile from Google.
    
    Args:
        access_token: The access token from token exchange
        
    Returns:
        Dict with user info (id, email, name, picture, etc.)
        
    Raises:
        Exception if user info fetch fails
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get user info: {response.text}")
        
        return response.json()


async def authenticate_with_google(code: str) -> dict:
    """Complete Google OAuth flow: exchange code and get user info.
    
    Args:
        code: The authorization code from Google callback
        
    Returns:
        Dict with:
        - google_id: User's Google ID
        - email: User's email
        - name: User's display name
        - picture: URL to profile picture
        - email_verified: Whether email is verified by Google
    """
    tokens = await exchange_code_for_tokens(code)
    user_info = await get_user_info(tokens["access_token"])
    
    return {
        "google_id": user_info.get("id"),
        "email": user_info.get("email"),
        "name": user_info.get("name"),
        "picture": user_info.get("picture"),
        "email_verified": user_info.get("verified_email", False),
    }
