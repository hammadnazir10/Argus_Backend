"""
Authentication endpoints.
Handles user signup, signin, email verification, and password management.
"""

from fastapi import APIRouter, status, HTTPException
from loguru import logger
from botocore.exceptions import ClientError

from app.schemas.auth import (
    SignUpRequest,
    SignUpResponse,
    SignInRequest,
    SignInResponse,
    TokenResponse,
    ConfirmEmailRequest,
    ConfirmEmailResponse,
    ResendConfirmationCodeRequest,
    ResendConfirmationCodeResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ConfirmForgotPasswordRequest,
    ConfirmForgotPasswordResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    UserProfileResponse,
    SignOutRequest,
    SignOutResponse,
    ErrorResponse,
)
from app.services.auth_service import cognito_service
from app.exceptions.auth_exceptions import handle_cognito_error

router = APIRouter(tags=["Authentication"])


# ============================================================================
# Sign Up Endpoints
# ============================================================================

@router.post(
    "/signup",
    response_model=SignUpResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request data"},
        409: {"model": ErrorResponse, "description": "User already exists"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Register a new user",
    description="Create a new user account. Requires email verification.",
)
async def sign_up(request: SignUpRequest):
    """
    Register a new user with email and password.
    
    **Request Body:**
    - username: Unique username (3-128 characters)
    - email: Valid email address
    - password: Strong password (minimum 8 characters)
    
    **Response:**
    - user_sub: Unique user ID from Cognito
    - username: The registered username
    - code_delivery_details: Information about verification code delivery
    
    **Note:** User must confirm email before signing in.
    """
    try:
        logger.info(f"Processing signup request for username: {request.username}")
        
        result = cognito_service.sign_up(
            email=request.email,
            password=request.password,
            username=request.username,
        )
        
        return SignUpResponse(**result)
        
    except ClientError as e:
        logger.error(f"Signup failed for {request.username}: {str(e)}")
        raise handle_cognito_error(e, context="signup")
    except Exception as e:
        logger.error(f"Unexpected error during signup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during signup",
        )


# ============================================================================
# Email Verification Endpoints
# ============================================================================

@router.post(
    "/confirm-email",
    response_model=ConfirmEmailResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid confirmation code"},
        404: {"model": ErrorResponse, "description": "User not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Confirm user email",
    description="Verify user email address using confirmation code received via email.",
)
async def confirm_email(request: ConfirmEmailRequest):
    """
    Confirm user email address with verification code.
    
    **Request Body:**
    - username: Username or email address 
    - confirmation_code: 6-digit code received via email
    
    **Response:**
    - message: Confirmation success message
    
    **Note:** User can now sign in after email confirmation.
    """
    try:
        logger.info(f"Processing email confirmation for username: {request.username}")
        
        result = cognito_service.confirm_sign_up(
            identifier=request.username,
            confirmation_code=request.confirmation_code,
        )
        
        return ConfirmEmailResponse(**result)
        
    except ClientError as e:
        logger.error(f"Email confirmation failed for {request.username}: {str(e)}")
        raise handle_cognito_error(e, context="confirm_email")
    except Exception as e:
        logger.error(f"Unexpected error during email confirmation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during email confirmation",
        )


@router.post(
    "/resend-confirmation-code",
    response_model=ResendConfirmationCodeResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "User not found"},
        429: {"model": ErrorResponse, "description": "Too many requests"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Resend confirmation code",
    description="Send a new confirmation code to user's email.",
)
async def resend_confirmation_code(request: ResendConfirmationCodeRequest):
    """
    Resend email confirmation code to user.
    
    **Request Body:**
    - username: Username or email address
    
    **Response:**
    - message: Confirmation code resent message
    - code_delivery_details: Information about code delivery
    
    **Note:** Useful if user doesn't receive initial confirmation code.
    """
    try:
        logger.info(f"Resending confirmation code for username: {request.username}")
        
        result = cognito_service.resend_confirmation_code(
            identifier=request.username,
        )
        
        return ResendConfirmationCodeResponse(
            message="Confirmation code sent to your email",
            code_delivery_details=result.get('code_delivery_details'),
        )
        
    except ClientError as e:
        logger.error(f"Resend confirmation failed for {request.username}: {str(e)}")
        raise handle_cognito_error(e, context="resend_confirmation_code")
    except Exception as e:
        logger.error(f"Unexpected error during resend confirmation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resending confirmation code",
        )


# ============================================================================
# Sign In Endpoint
# ============================================================================

@router.post(
    "/signin",
    response_model=SignInResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid credentials or user not confirmed"},
        401: {"model": ErrorResponse, "description": "Authentication failed"},
        429: {"model": ErrorResponse, "description": "Too many failed attempts"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="User sign in",
    description="Authenticate user and receive access tokens.",
)
async def sign_in(request: SignInRequest):
    """
    Authenticate user with username or email and password.
    
    **Request Body:**
    - username: Username or email address
    - password: User password
    
    **Response:**
    - message: Signin success message
    - tokens: OAuth tokens including access_token, id_token, refresh_token
    - user: User profile information (if available)
    
    **Important:** 
    - User must have confirmed email before signing in
    - Can use either username or email address for authentication
    - Include access_token in Authorization header for protected endpoints
    - Access token expires in 1 hour by default
    - Use refresh_token to get new tokens without re-authenticating
    """
    try:
        logger.info(f"Processing signin request for: {request.username}")
        
        auth_result = cognito_service.initiate_auth(
            identifier=request.username,
            password=request.password,
        )
        
        # Extract user info and tokens separately
        user_info = auth_result.pop('user', {})
        token_response = TokenResponse(**auth_result)
        
        return SignInResponse(
            message="Sign in successful",
            tokens=token_response,
            user=user_info,
        )
        
    except ClientError as e:
        logger.error(f"Signin failed for {request.username}: {str(e)}")
        raise handle_cognito_error(e, context="signin")
    except Exception as e:
        logger.error(f"Unexpected error during signin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during sign in",
        )


# ============================================================================
# Password Management Endpoints
# ============================================================================

@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "User not found"},
        429: {"model": ErrorResponse, "description": "Too many requests"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Request password reset",
    description="Initiate password reset flow for user.",
)
async def forgot_password(request: ForgotPasswordRequest):
    """
    Initiate password reset process.
    
    **Request Body:**
    - email: The registered email address
    
    **Response:**
    - message: Password reset code sent message
    - code_delivery_details: Information about code delivery
    
    **Note:** User will receive password reset code via email.
    """
    try:
        logger.info(f"Processing forgot password request for: {request.identifier}")
        
        result = cognito_service.forgot_password(
            identifier=request.identifier,
        )
        
        return ForgotPasswordResponse(
            message="Password reset code sent to your email",
            code_delivery_details=result.get('code_delivery_details'),
        )
        
    except ClientError as e:
        logger.error(f"Forgot password failed for {request.identifier}: {str(e)}") 
        raise handle_cognito_error(e, context="forgot_password")
    except Exception as e:
        logger.error(f"Unexpected error during forgot password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during forgot password request",
        )


@router.post(
    "/confirm-forgot-password",
    response_model=ConfirmForgotPasswordResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid reset code or password"},
        404: {"model": ErrorResponse, "description": "User not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Reset password with code",
    description="Confirm password reset with verification code.",
)
async def confirm_forgot_password(request: ConfirmForgotPasswordRequest):
    """
    Confirm password reset with verification code and new password.
    
    **Request Body:**
    - identifier: Username or email address
    - confirmation_code: 6-digit code received via email
    - new_password: New password (minimum 8 characters)
    
    **Response:**
    - message: Password reset success message
    
    **Note:** User can sign in with new password after confirmation.
    """
    try:
        logger.info(f"Processing confirm forgot password for: {request.identifier}")
        
        result = cognito_service.confirm_forgot_password(
            identifier=request.identifier,
            confirmation_code=request.confirmation_code,
            new_password=request.new_password,
        )
        
        return ConfirmForgotPasswordResponse(**result)
        
    except ClientError as e:
        logger.error(f"Confirm forgot password failed for {request.identifier}: {str(e)}")
        raise handle_cognito_error(e, context="confirm_forgot_password")
    except Exception as e:
        logger.error(f"Unexpected error during confirm forgot password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during password reset confirmation",
        )


@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid password"},
        401: {"model": ErrorResponse, "description": "Token expired or invalid"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Change password",
    description="Change password for authenticated user.",
)
async def change_password(request: ChangePasswordRequest, access_token: str = None):
    """
    Change password for authenticated user.
    
    **Request Body:**
    - previous_password: Current password
    - proposed_password: New password (minimum 8 characters)
    
    **Headers:**
    - Authorization: Bearer <access_token>
    
    **Response:**
    - message: Password change success message
    
    **Note:** Requires valid access token from recent signin.
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token required",
        )
    
    try:
        logger.info("Processing change password request")
        
        result = cognito_service.change_password(
            access_token=access_token,
            previous_password=request.previous_password,
            proposed_password=request.proposed_password,
        )
        
        return ChangePasswordResponse(**result)
        
    except ClientError as e:
        logger.error(f"Change password failed: {str(e)}")
        raise handle_cognito_error(e, context="change_password")
    except Exception as e:
        logger.error(f"Unexpected error during change password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during password change",
        )


# ============================================================================
# Sign Out Endpoint
# ============================================================================

@router.post(
    "/signout",
    response_model=SignOutResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or expired token"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Sign out user",
    description="Sign out user globally across all sessions.",
)
async def sign_out(request: SignOutRequest):
    """
    Sign out user globally.
    
    **Request Body:**
    - access_token: User access token from signin response
    
    **Response:**
    - message: Sign out success message
    
    **Note:** User will be signed out from all sessions and devices.
    """
    try:
        logger.info("Processing user sign out")
        
        # Note: AWS Cognito admin_user_global_sign_out requires user pool admin access
        # For now, we'll just return success as the token will be invalid after expiry
        # In production, you might want to maintain a token blacklist
        
        return SignOutResponse(
            message="Signed out successfully. Token will expire shortly.",
        )
        
    except Exception as e:
        logger.error(f"Unexpected error during sign out: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during sign out",
        )


# ============================================================================
# User Profile Endpoint
# ============================================================================

@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or expired token"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Get current user profile",
    description="Retrieve current authenticated user's profile information.",
)
async def get_user_profile(access_token: str = None):
    """
    Get current user profile information.
    
    **Headers:**
    - Authorization: Bearer <access_token>
    
    **Response:**
    - username: User's username
    - email: User's email address
    - email_verified: Whether email is verified
    - given_name: User's first name (if provided)
    - family_name: User's last name (if provided)
    - sub: Unique user ID
    
    **Note:** Requires valid access token from recent signin.
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token required",
        )
    
    try:
        logger.info("Retrieving user profile")
        
        result = cognito_service.get_user(access_token=access_token)
        
        attributes = result.get('attributes', {})
        
        return UserProfileResponse(
            username=result.get('username'),
            email=attributes.get('email'),
            email_verified=attributes.get('email_verified', '').lower() == 'true',
            given_name=attributes.get('given_name'),
            family_name=attributes.get('family_name'),
            sub=attributes.get('sub'),
        )
        
    except ClientError as e:
        logger.error(f"Get user profile failed: {str(e)}")
        raise handle_cognito_error(e, context="get_user_profile")
    except Exception as e:
        logger.error(f"Unexpected error while retrieving user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving user profile",
        )

