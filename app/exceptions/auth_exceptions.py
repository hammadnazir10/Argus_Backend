"""
Authentication-specific exception handlers.
"""

from fastapi import HTTPException, status
from botocore.exceptions import ClientError
from loguru import logger


class AuthenticationException(HTTPException):
    """Base authentication exception."""
    def __init__(self, detail: str, error_code: str = "AUTH_ERROR"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
        self.error_code = error_code


class InvalidCredentialsException(AuthenticationException):
    """Invalid username or password."""
    def __init__(self):
        super().__init__(
            detail="Invalid username or password",
            error_code="INVALID_CREDENTIALS",
        )


class UserNotConfirmedException(AuthenticationException):
    """User account not confirmed."""
    def __init__(self):
        super().__init__(
            detail="Please confirm your email address before signing in",
            error_code="USER_NOT_CONFIRMED",
        )


class UserLimitExceededException(HTTPException):
    """User limit exceeded."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts, please try again later",
        )


class InvalidPasswordException(HTTPException):
    """Invalid password format."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password does not meet complexity requirements: "
                   "minimum 8 characters, uppercase, lowercase, and number",
        )


class UserAlreadyExistsException(HTTPException):
    """User already exists."""
    def __init__(self, username: str = None):
        detail = "User already exists"
        if username:
            detail = f"Username '{username}' already exists"
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class UserNotFoundException(HTTPException):
    """User not found."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )


class InvalidConfirmationCodeException(HTTPException):
    """Invalid or expired confirmation code."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired confirmation code",
        )


class ExpiredTokenException(AuthenticationException):
    """Token expired."""
    def __init__(self):
        super().__init__(
            detail="Token has expired",
            error_code="EXPIRED_TOKEN",
        )


class InvalidTokenException(AuthenticationException):
    """Invalid token."""
    def __init__(self):
        super().__init__(
            detail="Invalid token",
            error_code="INVALID_TOKEN",
        )


def handle_cognito_error(error: ClientError, context: str = "") -> HTTPException:
    """
    Convert Cognito ClientError to appropriate HTTPException.
    
    Args:
        error: Cognito ClientError
        context: Error context for logging
        
    Returns:
        Appropriate HTTPException
    """
    error_code = error.response['Error']['Code']
    logger.error(f"Cognito error ({context}): {error_code} - {error.response['Error']['Message']}")
    
    error_handlers = {
        'InvalidPasswordException': InvalidPasswordException(),
        'UserNotConfirmedException': UserNotConfirmedException(),
        'UsernameExistsException': UserAlreadyExistsException(),
        'UserNotFoundException': UserNotFoundException(),
        'NotAuthorizedException': InvalidCredentialsException(),
        'UserLimitExceededException': UserLimitExceededException(),
        'InvalidParameterException': HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request parameters",
        ),
        'CodeMismatchException': InvalidConfirmationCodeException(),
        'ExpiredCodeException': InvalidConfirmationCodeException(),
        'TooManyRequestsException': HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests, please try again later",
        ),
        'InvalidAuthFlowConfiguration': HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication flow not configured correctly",
        ),
    }
    
    return error_handlers.get(
        error_code,
        HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication service error: {error_code}",
        ),
    )
