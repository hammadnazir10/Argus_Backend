from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash


class UserService:
    """Service class for user operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination."""
        result = await self.db.execute(
            select(User).offset(skip).limit(limit)
        )
        return list(result.scalars().all())
    
    async def create(self, user_in: UserCreate) -> User:
        """Create a new user."""
        user = User(
            email=user_in.email,
            username=user_in.username,
            hashed_password=get_password_hash(user_in.password),
            full_name=user_in.full_name,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user
    
    async def update(self, user_id: int, user_in: UserUpdate) -> Optional[User]:
        """Update user."""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        update_data = user_in.model_dump(exclude_unset=True)
        
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
        for field, value in update_data.items():
            setattr(user, field, value)
        
        await self.db.flush()
        await self.db.refresh(user)
        return user
    
    async def delete(self, user_id: int) -> bool:
        """Delete user."""
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        await self.db.delete(user)
        await self.db.flush()
        return True
    
    async def update_last_login(self, user_id: int) -> None:
        """Update user's last login timestamp."""
        user = await self.get_by_id(user_id)
        if user:
            user.last_login = datetime.utcnow()
            await self.db.flush()
