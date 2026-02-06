"""
Pydantic schemas for authentication endpoints.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any


# ============================================================================
# Sign Up Schemas
# ============================================================================

class SignUpRequest(BaseModel):
    """User signup request."""
    username: str = Field(..., min_length=3, max_length=128)
    email: EmailStr
    password: str = Field(..., min_length=8)


class SignUpResponse(BaseModel):
    """User signup response."""
    user_sub: str
    username: str
    message: str = "User registered successfully. Please check your email for verification code."
    code_delivery_details: Optional[Dict[str, Any]] = None


# ============================================================================
# Email Verification Schemas
# ============================================================================

class ConfirmEmailRequest(BaseModel):
    """Email confirmation request."""
    username: str = Field(..., min_length=3, max_length=128, description="Username or email address")
    confirmation_code: str = Field(..., min_length=6, max_length=6)


class ConfirmEmailResponse(BaseModel):
    """Email confirmation response."""
    message: str = "Email verified successfully"


class ResendConfirmationCodeRequest(BaseModel):
    """Resend confirmation code request."""
    username: str = Field(..., min_length=3, max_length=128, description="Username or email address")


class ResendConfirmationCodeResponse(BaseModel):
    """Resend confirmation code response."""
    message: str = "Confirmation code sent to your email"
    code_delivery_details: Optional[Dict[str, Any]] = None


# ============================================================================
# Sign In Schemas
# ============================================================================

class SignInRequest(BaseModel):
    """User signin request."""
    username: str = Field(..., min_length=3, max_length=128, description="Username or email address")
    password: str = Field(...)


class TokenResponse(BaseModel):
    """OAuth token response."""
    access_token: str
    id_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"


class SignInResponse(BaseModel):
    """User signin response."""
    message: str = "Sign in successful"
    tokens: TokenResponse
    user: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Password Management Schemas
# ============================================================================

class ForgotPasswordRequest(BaseModel):
    """Forgot password request."""
    identifier: str = Field(..., min_length=3, max_length=128, description="Username or email address")


class ForgotPasswordResponse(BaseModel):
    """Forgot password response."""
    message: str = "Password reset code sent to your email"
    code_delivery_details: Optional[Dict[str, Any]] = None


class ConfirmForgotPasswordRequest(BaseModel):
    """Confirm forgot password request."""
    identifier: str = Field(..., min_length=3, max_length=128, description="Username or email address")
    confirmation_code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8)


class ConfirmForgotPasswordResponse(BaseModel):
    """Confirm forgot password response."""
    message: str = "Password reset successfully"


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    previous_password: str = Field(...)
    proposed_password: str = Field(..., min_length=8)


class ChangePasswordResponse(BaseModel):
    """Change password response."""
    message: str = "Password changed successfully"


# ============================================================================
# Refresh Token Schemas
# ============================================================================

class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """Refresh token response."""
    access_token: str
    id_token: str
    expires_in: int
    token_type: str = "Bearer"


# ============================================================================
# User Profile Schemas
# ============================================================================

class UserProfileResponse(BaseModel):
    """User profile response."""
    username: str
    email: Optional[str] = None
    email_verified: Optional[bool] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    sub: Optional[str] = None


class SignOutRequest(BaseModel):
    """Sign out request."""
    access_token: str


class SignOutResponse(BaseModel):
    """Sign out response."""
    message: str = "Signed out successfully"


# ============================================================================
# Error Response Schema
# ============================================================================

class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
