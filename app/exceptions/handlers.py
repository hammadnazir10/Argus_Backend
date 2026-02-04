from fastapi import HTTPException, status


class ArgusException(HTTPException):
    """Base exception for Argus application."""
    
    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "An unexpected error occurred",
    ):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundException(ArgusException):
    """Resource not found exception."""
    
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class BadRequestException(ArgusException):
    """Bad request exception."""
    
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UnauthorizedException(ArgusException):
    """Unauthorized exception."""
    
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )


class ForbiddenException(ArgusException):
    """Forbidden exception."""
    
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
