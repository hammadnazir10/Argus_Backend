from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, List

T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    """Generic response model."""
    success: bool = True
    message: str = "Success"
    data: Optional[T] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response model."""
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int


class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = False
    message: str
    detail: Optional[str] = None
