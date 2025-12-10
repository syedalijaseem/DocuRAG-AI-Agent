# Milestone 0: User Authentication - Requirements

## Overview

Implement complete user authentication system with email/password registration, Google OAuth, email verification, and session management.

**Branch**: `feature/m0-authentication`  
**Duration**: 4-5 days  
**Prerequisite for**: All other milestones

---

## Functional Requirements

### FR-1: User Registration (Email/Password)

| ID     | Requirement                                                                 | Priority |
| ------ | --------------------------------------------------------------------------- | -------- |
| FR-1.1 | User can register with email, password, and name                            | P0       |
| FR-1.2 | Password must be validated: min 8 chars, 1 uppercase, 1 lowercase, 1 number | P0       |
| FR-1.3 | Password is checked against HaveIBeenPwned API (k-anonymity)                | P1       |
| FR-1.4 | Duplicate email registration returns 409 Conflict                           | P0       |
| FR-1.5 | Verification email is sent asynchronously via Inngest                       | P0       |
| FR-1.6 | User cannot login until email is verified                                   | P0       |

### FR-2: Email Verification

| ID     | Requirement                                                  | Priority |
| ------ | ------------------------------------------------------------ | -------- |
| FR-2.1 | Verification link contains secure random token               | P0       |
| FR-2.2 | Token expires after 24 hours                                 | P0       |
| FR-2.3 | Clicking valid link sets email_verified=true                 | P0       |
| FR-2.4 | Clicking expired/invalid link shows error with resend option | P0       |
| FR-2.5 | User can request resend (rate limited to 3/hour)             | P1       |

### FR-3: User Login

| ID     | Requirement                                                             | Priority |
| ------ | ----------------------------------------------------------------------- | -------- |
| FR-3.1 | User can login with email and password                                  | P0       |
| FR-3.2 | Successful login issues access token (15min) and refresh token (7 days) | P0       |
| FR-3.3 | Tokens are stored in HTTP-only, Secure, SameSite=Strict cookies         | P0       |
| FR-3.4 | Invalid credentials return generic 401 (no user enumeration)            | P0       |
| FR-3.5 | Unverified email returns 403 with message                               | P0       |
| FR-3.6 | Locked account returns 423 with retry-after header                      | P0       |

### FR-4: Account Lockout

| ID     | Requirement                                        | Priority |
| ------ | -------------------------------------------------- | -------- |
| FR-4.1 | Failed login increments failed_login_attempts      | P0       |
| FR-4.2 | 5 failed attempts triggers 15-minute lockout       | P0       |
| FR-4.3 | Successful login resets failed_login_attempts to 0 | P0       |
| FR-4.4 | Lockout status is stored in locked_until field     | P0       |

### FR-5: Token Refresh

| ID     | Requirement                                           | Priority |
| ------ | ----------------------------------------------------- | -------- |
| FR-5.1 | Client can refresh access token using refresh token   | P0       |
| FR-5.2 | Refresh rotates both tokens (old refresh invalidated) | P0       |
| FR-5.3 | Expired refresh token requires re-login               | P0       |
| FR-5.4 | Max 10 refresh tokens per user (oldest revoked)       | P1       |

### FR-6: Logout

| ID     | Requirement                                            | Priority |
| ------ | ------------------------------------------------------ | -------- |
| FR-6.1 | User can logout current session (revoke refresh token) | P0       |
| FR-6.2 | User can logout all sessions ("logout everywhere")     | P1       |
| FR-6.3 | Logout clears cookies and revokes server-side tokens   | P0       |

### FR-7: Google OAuth

| ID     | Requirement                                                     | Priority |
| ------ | --------------------------------------------------------------- | -------- |
| FR-7.1 | User can sign up/login with Google                              | P0       |
| FR-7.2 | Google users are auto-verified (email_verified=true)            | P0       |
| FR-7.3 | If email already exists, provider is linked to existing account | P0       |
| FR-7.4 | Provider info stored in user_providers table                    | P0       |
| FR-7.5 | User can unlink Google if they have password or other provider  | P1       |

### FR-8: Password Reset

| ID     | Requirement                                                 | Priority |
| ------ | ----------------------------------------------------------- | -------- |
| FR-8.1 | User can request password reset via email                   | P0       |
| FR-8.2 | Reset link contains secure token (1 hour TTL)               | P0       |
| FR-8.3 | Clicking link shows password reset form                     | P0       |
| FR-8.4 | Submitting new password updates hash and revokes all tokens | P0       |
| FR-8.5 | Request always returns 200 (no email enumeration)           | P0       |

### FR-9: Email Change

| ID     | Requirement                                            | Priority |
| ------ | ------------------------------------------------------ | -------- |
| FR-9.1 | User can change email (requires password verification) | P1       |
| FR-9.2 | New email sets email_verified=false                    | P1       |
| FR-9.3 | Verification email sent to new address                 | P1       |
| FR-9.4 | New email must not be in use                           | P1       |

### FR-10: Account Deletion

| ID      | Requirement                                         | Priority |
| ------- | --------------------------------------------------- | -------- |
| FR-10.1 | User can delete account (requires password/re-auth) | P1       |
| FR-10.2 | Deletion immediately revokes all tokens             | P1       |
| FR-10.3 | User data is queued for background deletion         | P1       |
| FR-10.4 | Confirmation email is sent                          | P2       |

### FR-11: Session Management

| ID      | Requirement                              | Priority |
| ------- | ---------------------------------------- | -------- |
| FR-11.1 | User can view list of active sessions    | P2       |
| FR-11.2 | Sessions show device info (if available) | P2       |
| FR-11.3 | User can revoke individual sessions      | P2       |

### FR-12: Frontend Pages

| ID      | Requirement                                                   | Priority |
| ------- | ------------------------------------------------------------- | -------- |
| FR-12.1 | Login page with email/password form and Google button         | P0       |
| FR-12.2 | Register page with name/email/password form                   | P0       |
| FR-12.3 | Verify email page (success/error/resend)                      | P0       |
| FR-12.4 | Forgot password page                                          | P0       |
| FR-12.5 | Reset password page                                           | P0       |
| FR-12.6 | Settings page (profile, password, email, providers, sessions) | P1       |

---

## Non-Functional Requirements

### NFR-1: Security

| ID      | Requirement                                          | Target   |
| ------- | ---------------------------------------------------- | -------- |
| NFR-1.1 | Passwords hashed with bcrypt (cost=12)               | Required |
| NFR-1.2 | JWT signed with RS256 (asymmetric)                   | Required |
| NFR-1.3 | Tokens stored in HTTP-only cookies                   | Required |
| NFR-1.4 | CSRF protection via SameSite=Strict                  | Required |
| NFR-1.5 | All tokens hashed before storage                     | Required |
| NFR-1.6 | Rate limiting: 100 req/IP/15min, 5 login/email/15min | Required |
| NFR-1.7 | No user enumeration in error messages                | Required |
| NFR-1.8 | TLS required for all endpoints                       | Required |

### NFR-2: Performance

| ID      | Requirement                         | Target |
| ------- | ----------------------------------- | ------ |
| NFR-2.1 | Login response time                 | <500ms |
| NFR-2.2 | Token validation (no DB lookup)     | <10ms  |
| NFR-2.3 | Registration (excluding email send) | <1s    |

### NFR-3: Scalability

| ID      | Requirement                              | Target   |
| ------- | ---------------------------------------- | -------- |
| NFR-3.1 | Stateless auth (JWT, no session storage) | Required |
| NFR-3.2 | Horizontal scaling support               | Required |
| NFR-3.3 | Connection pooling for MongoDB           | Required |

### NFR-4: Reliability

| ID      | Requirement                                       | Target   |
| ------- | ------------------------------------------------- | -------- |
| NFR-4.1 | Email delivery via managed service (SendGrid/SES) | Required |
| NFR-4.2 | Async email sending (non-blocking)                | Required |
| NFR-4.3 | Graceful error handling                           | Required |

### NFR-5: Maintainability

| ID      | Requirement                                | Target        |
| ------- | ------------------------------------------ | ------------- |
| NFR-5.1 | Type hints on all functions                | Required      |
| NFR-5.2 | Pydantic models for all requests/responses | Required      |
| NFR-5.3 | Unit tests for all auth flows              | >80% coverage |
| NFR-5.4 | Audit logging for auth events              | Required      |

---

## API Specification

### Endpoints

```
POST   /api/auth/register            # Register with email/password
POST   /api/auth/login               # Login
POST   /api/auth/google              # Google OAuth
GET    /api/auth/verify-email        # Verify email (link click)
POST   /api/auth/resend-verification # Resend verification
POST   /api/auth/refresh             # Refresh tokens
POST   /api/auth/logout              # Logout current session
POST   /api/auth/logout-all          # Logout all sessions
GET    /api/auth/me                  # Get current user
PATCH  /api/auth/me                  # Update profile
PATCH  /api/auth/email               # Change email
PATCH  /api/auth/password            # Change password
POST   /api/auth/forgot-password     # Request reset
POST   /api/auth/reset-password      # Complete reset
GET    /api/auth/sessions            # List sessions
DELETE /api/auth/sessions/{id}       # Revoke session
DELETE /api/auth/providers/{name}    # Unlink OAuth
DELETE /api/auth/account             # Delete account
```

---

## Database Schema

### Collections

- `users` - User accounts
- `user_providers` - OAuth provider links
- `refresh_tokens` - Active refresh tokens

### Indexes

```javascript
db.users.createIndex({ email: 1 }, { unique: true });
db.users.createIndex({ verification_token_hash: 1 }, { sparse: true });
db.users.createIndex({ reset_token_hash: 1 }, { sparse: true });
db.user_providers.createIndex({ user_id: 1 });
db.user_providers.createIndex(
  { provider: 1, provider_user_id: 1 },
  { unique: true }
);
db.refresh_tokens.createIndex({ user_id: 1 });
db.refresh_tokens.createIndex({ token_hash: 1 }, { unique: true });
db.refresh_tokens.createIndex({ expires_at: 1 }, { expireAfterSeconds: 0 });
```

---

## Dependencies

### Backend (Python)

```
python-jose[cryptography]>=3.3
passlib[bcrypt]>=1.7
google-auth>=2.0
sendgrid>=6.0
```

### Frontend (npm)

```
@react-oauth/google>=0.12
react-router-dom>=7.0
```

---

## Acceptance Criteria

| Test                        | Expected Result              |
| --------------------------- | ---------------------------- |
| Register with valid data    | 201, verification email sent |
| Register with weak password | 400, validation error        |
| Login before verified       | 403                          |
| Login after verified        | 200, tokens set              |
| 5 failed logins             | 423, locked                  |
| Google OAuth (new)          | User created, verified       |
| Google OAuth (existing)     | Provider linked              |
| Password reset              | Email sent, password updated |
| Delete account              | Data removed                 |
