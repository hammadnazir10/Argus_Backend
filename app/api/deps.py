from fastapi import Depends, HTTPException, status, Header
from typing import Optional

from app.db.session import get_database


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
