from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.db.session import get_database
from app.schemas.user import UserRead, UserUpdate
from app.services.user_service import UserService
from app.api.deps import get_current_user, get_current_superuser
from app.models.user import User

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get current user information."""
    return current_user


@router.put("/me", response_model=UserRead)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update current user information."""
    db = get_database()
    user_service = UserService(db)
    updated_user = await user_service.update(current_user.id, user_update)
    return updated_user


@router.get("/", response_model=List[UserRead])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_superuser),
):
    """Get all users (superuser only)."""
    db = get_database()
    user_service = UserService(db)
    users = await user_service.get_all(skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
):
    """Get user by ID (superuser only)."""
    db = get_database()
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
):
    """Delete user (superuser only)."""
    db = get_database()
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )
    
    await user_service.delete(user_id)
