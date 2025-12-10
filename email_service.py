"""Email service using Resend.

Provides functions for sending transactional emails (verification, password reset).
"""
import os
from typing import Optional
import resend
from dotenv import load_dotenv

load_dotenv()

# Configure Resend
resend.api_key = os.getenv("RESEND_API_KEY", "")

# Email configuration
FROM_EMAIL = os.getenv("FROM_EMAIL", "DocuRAG <onboarding@resend.dev>")
APP_NAME = os.getenv("APP_NAME", "DocuRAG")
APP_URL = os.getenv("APP_URL", "http://localhost:5173")


def is_configured() -> bool:
    """Check if email service is properly configured."""
    return bool(resend.api_key)


def send_verification_email(to_email: str, token: str, name: Optional[str] = None) -> bool:
    """Send email verification link.
    
    Args:
        to_email: Recipient email address
        token: Verification token
        name: Optional user name for personalization
        
    Returns:
        True if sent successfully, False otherwise
    """
    if not is_configured():
        print(f"[DEV] Email not configured. Verification token for {to_email}: {token}")
        return False
    
    verify_url = f"{APP_URL}/verify-email?token={token}"
    greeting = f"Hi {name}," if name else "Hi,"
    
    try:
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": f"Verify your {APP_NAME} account",
            "html": f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f4f4f5;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding: 40px 20px;">
    <tr>
      <td align="center">
        <table width="100%" style="max-width: 480px; background: white; border-radius: 12px; padding: 40px;">
          <tr>
            <td>
              <h1 style="margin: 0 0 24px; font-size: 24px; font-weight: 600; color: #18181b;">
                Verify your email
              </h1>
              <p style="margin: 0 0 16px; color: #52525b; line-height: 1.6;">
                {greeting}
              </p>
              <p style="margin: 0 0 24px; color: #52525b; line-height: 1.6;">
                Thanks for signing up for {APP_NAME}! Please verify your email address by clicking the button below.
              </p>
              <a href="{verify_url}" 
                 style="display: inline-block; padding: 14px 28px; background: linear-gradient(135deg, #f97316, #ec4899); 
                        color: white; text-decoration: none; border-radius: 10px; font-weight: 600; font-size: 14px;">
                Verify Email
              </a>
              <p style="margin: 32px 0 0; color: #a1a1aa; font-size: 13px; line-height: 1.5;">
                If you didn't create an account, you can safely ignore this email.
              </p>
              <p style="margin: 16px 0 0; color: #a1a1aa; font-size: 12px;">
                This link expires in 24 hours.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
            """
        })
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send verification email: {e}")
        return False


def send_password_reset_email(to_email: str, token: str) -> bool:
    """Send password reset link.
    
    Args:
        to_email: Recipient email address
        token: Password reset token
        
    Returns:
        True if sent successfully, False otherwise
    """
    if not is_configured():
        print(f"[DEV] Email not configured. Password reset token for {to_email}: {token}")
        return False
    
    reset_url = f"{APP_URL}/reset-password?token={token}"
    
    try:
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": f"Reset your {APP_NAME} password",
            "html": f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f4f4f5;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding: 40px 20px;">
    <tr>
      <td align="center">
        <table width="100%" style="max-width: 480px; background: white; border-radius: 12px; padding: 40px;">
          <tr>
            <td>
              <h1 style="margin: 0 0 24px; font-size: 24px; font-weight: 600; color: #18181b;">
                Reset your password
              </h1>
              <p style="margin: 0 0 24px; color: #52525b; line-height: 1.6;">
                We received a request to reset your password. Click the button below to choose a new password.
              </p>
              <a href="{reset_url}" 
                 style="display: inline-block; padding: 14px 28px; background: #18181b; 
                        color: white; text-decoration: none; border-radius: 10px; font-weight: 600; font-size: 14px;">
                Reset Password
              </a>
              <p style="margin: 32px 0 0; color: #a1a1aa; font-size: 13px; line-height: 1.5;">
                If you didn't request a password reset, you can safely ignore this email.
              </p>
              <p style="margin: 16px 0 0; color: #a1a1aa; font-size: 12px;">
                This link expires in 1 hour.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
            """
        })
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send password reset email: {e}")
        return False


def send_email_change_verification(to_email: str, token: str) -> bool:
    """Send email change verification link.
    
    Args:
        to_email: New email address to verify
        token: Verification token
        
    Returns:
        True if sent successfully, False otherwise
    """
    if not is_configured():
        print(f"[DEV] Email not configured. Email change token for {to_email}: {token}")
        return False
    
    verify_url = f"{APP_URL}/verify-email?token={token}"
    
    try:
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": f"Verify your new email for {APP_NAME}",
            "html": f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f4f4f5;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding: 40px 20px;">
    <tr>
      <td align="center">
        <table width="100%" style="max-width: 480px; background: white; border-radius: 12px; padding: 40px;">
          <tr>
            <td>
              <h1 style="margin: 0 0 24px; font-size: 24px; font-weight: 600; color: #18181b;">
                Verify your new email
              </h1>
              <p style="margin: 0 0 24px; color: #52525b; line-height: 1.6;">
                You requested to change your {APP_NAME} email to this address. Please verify by clicking the button below.
              </p>
              <a href="{verify_url}" 
                 style="display: inline-block; padding: 14px 28px; background: linear-gradient(135deg, #f97316, #ec4899); 
                        color: white; text-decoration: none; border-radius: 10px; font-weight: 600; font-size: 14px;">
                Verify Email
              </a>
              <p style="margin: 32px 0 0; color: #a1a1aa; font-size: 13px; line-height: 1.5;">
                If you didn't request this change, please contact support immediately.
              </p>
              <p style="margin: 16px 0 0; color: #a1a1aa; font-size: 12px;">
                This link expires in 24 hours.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
            """
        })
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send email change verification: {e}")
        return False
