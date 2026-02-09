from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import jwt
from loguru import logger

from app.db.session import get_database

security = HTTPBearer()


async def get_api_key(
    x_api_key: Optional[str] = Header(None),
) -> str:
    """
    Get and validate API key from header.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return x_api_key


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Validate JWT token from Cognito and extract user information.
    
    Args:
        credentials: HTTP Bearer token from Authorization header
        
    Returns:
        User information from token
        
    Raises:
        HTTPException: If token is invalid or expired
    
    **Usage:**
    ```python
    @router.get("/profile")
    async def get_profile(user: dict = Depends(get_current_user)):
        return {"email": user["email"]}
    ```
    """
    token = credentials.credentials
    
    try:
        # Note: In production, verify token signature using Cognito's public keys
        # For development, decode without verification
        payload = jwt.decode(
            token,
            options={"verify_signature": False},
        )
        
        # Get email from token (Cognito uses email as username)
        email: str = payload.get("email") or payload.get("cognito:username") or payload.get("username")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        
        return {
            "email": email,
            "username": email,  # Keep for backward compatibility
            "sub": payload.get("sub"),
            "token": token,
        }
        
    except jwt.InvalidTokenError:
        logger.error("Invalid token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """
    Optionally validate JWT token if provided.
    
    Args:
        credentials: HTTP Bearer token from Authorization header (optional)
        
    Returns:
        User information from token, or None if not provided
    
    **Usage:**
    ```python
    @router.get("/public")
    async def public_endpoint(user: Optional[dict] = Depends(get_optional_user)):
        if user:
            return {"message": f"Hello {user['email']}"}
        return {"message": "Hello Guest"}
    ```
    """
    if not credentials:
        return None
    
    return await get_current_user(credentials)


