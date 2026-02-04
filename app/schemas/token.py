from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Token payload schema."""
    sub: Optional[str] = None
    exp: Optional[int] = None
    type: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    refresh_token: str
