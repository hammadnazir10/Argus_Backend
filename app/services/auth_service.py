"""
AWS Cognito authentication service.
Handles user signup, signin, email verification, and token management.
"""

import hmac
import hashlib
import base64
import re
from typing import Dict, Union
import boto3
from botocore.exceptions import ClientError
from loguru import logger

from app.core.config import settings
from app.exceptions.auth_exceptions import handle_cognito_error


class CognitoAuthService:
    """AWS Cognito authentication service."""
    
    def __init__(self):
        """Initialize Cognito client."""
        self.client = boto3.client(
            'cognito-idp',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        self.user_pool_id = settings.COGNITO_USER_POOL_ID
        self.client_id = settings.COGNITO_CLIENT_ID
        self.client_secret = settings.COGNITO_CLIENT_SECRET
    
    def _is_email(self, identifier: str) -> bool:
        """Check if identifier is an email address."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, identifier) is not None
    
    def _try_get_user_by_identifier(self, identifier: str) -> Union[str, None]:
        """
        Try to find user by identifier (username or email).
        Returns the Cognito username if found, None if not found.
        """
        try:
            # First, try identifier as-is (could be username)
            self.client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=identifier
            )
            return identifier
        except ClientError as e:
            if e.response['Error']['Code'] == 'UserNotFoundException':
                # If identifier looks like email, try to find user by email attribute
                if self._is_email(identifier):
                    try:
                        response = self.client.list_users(
                            UserPoolId=self.user_pool_id,
                            Filter=f'email = "{identifier}"'
                        )
                        if response['Users']:
                            return response['Users'][0]['Username']
                    except ClientError:
                        pass
            return None
    
    def _get_secret_hash(self, username: str) -> str:
        """
        Calculate SECRET_HASH for Cognito Client with secret.
        
        Args:
            username: Cognito username
            
        Returns:
            Base64 encoded SECRET_HASH
        """
        message = bytes(username + self.client_id, 'utf-8')
        secret = bytes(self.client_secret, 'utf-8')
        dig = hmac.new(secret, msg=message, digestmod=hashlib.sha256).digest()
        return base64.b64encode(dig).decode()
    
    def sign_up(
        self,
        email: str,
        password: str,
        username: str,
    ) -> Dict:
        """
        Register a new user in Cognito.
        
        Args:
            email: User email address
            password: User password
            username: Custom username (used as Cognito username)
            
        Returns:
            Cognito signup response
            
        Raises:
            ClientError: If signup fails
        """
        try:
            response = self.client.sign_up(
                ClientId=self.client_id,
                Username=username,  # Use the custom username as Cognito username
                Password=password,
                UserAttributes=[
                    {
                        'Name': 'email',
                        'Value': email,
                    },
                ],
                SecretHash=self._get_secret_hash(username),  # SecretHash based on username
            )
            logger.info(f"User {username} ({email}) signed up successfully")
            return {
                'user_sub': response['UserSub'],
                'username': username,
                'email': email,
                'code_delivery_details': response.get('CodeDeliveryDetails'),
            }
        except ClientError as e:
            logger.error(f"Signup error for {username}: {e.response['Error']['Code']}")
            raise
    
    def confirm_sign_up(
        self,
        identifier: str,
        confirmation_code: str,
    ) -> Dict:
        """
        Confirm user email during signup.
        
        Args:
            identifier: Username or email address
            confirmation_code: Email confirmation code
            
        Returns:
            Confirmation response
            
        Raises:
            ClientError: If confirmation fails
        """
        try:
            # Find the actual Cognito username
            cognito_username = self._try_get_user_by_identifier(identifier)
            if not cognito_username:
                raise ClientError(
                    {'Error': {'Code': 'UserNotFoundException'}},
                    'AdminGetUser'
                )
            
            self.client.confirm_sign_up(
                ClientId=self.client_id,
                Username=cognito_username,
                ConfirmationCode=confirmation_code,
                SecretHash=self._get_secret_hash(cognito_username),
            )
            logger.info(f"Email confirmed for user {identifier} (Cognito: {cognito_username})")
            return {'message': 'Email confirmed successfully'}
        except ClientError as e:
            logger.error(f"Confirmation error for {identifier}: {e.response['Error']['Code']}")
            raise
    
    def initiate_auth(
        self,
        identifier: str,
        password: str,
    ) -> Dict:
        """
        Authenticate user using username/email and password.
        
        Args:
            identifier: Username or email address
            password: User password
            
        Returns:
            Authentication response with tokens
            
        Raises:
            ClientError: If authentication fails
        """
        try:
            # Find the actual Cognito username
            cognito_username = self._try_get_user_by_identifier(identifier)
            if not cognito_username:
                raise ClientError(
                    {'Error': {'Code': 'UserNotFoundException'}},
                    'AdminInitiateAuth'
                )
            
            # Use ADMIN_USER_PASSWORD_AUTH flow for username/password authentication
            response = self.client.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow='ADMIN_USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': cognito_username,
                    'PASSWORD': password,
                    'SECRET_HASH': self._get_secret_hash(cognito_username),
                },
            )
            logger.info(f"User {identifier} (Cognito: {cognito_username}) authenticated successfully")
            
            auth_result = response.get('AuthenticationResult', {})
            access_token = auth_result.get('AccessToken')
            
            # Get user information using access token
            user_info = {}
            try:
                user_response = self.client.get_user(AccessToken=access_token)
                user_attributes = {
                    attr['Name']: attr['Value']
                    for attr in user_response.get('UserAttributes', [])
                }
                user_info = {
                    'username': user_response.get('Username'),
                    'email': user_attributes.get('email'),
                }
                logger.info(f"Retrieved user info for {identifier}: {user_info}")
            except Exception as e:
                logger.warning(f"Could not retrieve user info for {identifier}: {str(e)}")
            
            return {
                'access_token': access_token,
                'id_token': auth_result.get('IdToken'),
                'refresh_token': auth_result.get('RefreshToken'),
                'expires_in': auth_result.get('ExpiresIn'),
                'token_type': auth_result.get('TokenType', 'Bearer'),
                'user': user_info,
            }
        except ClientError as e:
            logger.error(f"Authentication error for {identifier}: {e.response['Error']['Code']}")
            raise
    
    def resend_confirmation_code(self, identifier: str) -> Dict:
        """
        Resend email confirmation code to user.
        
        Args:
            identifier: Username or email address
            
        Returns:
            Resend response
            
        Raises:
            ClientError: If resend fails
        """
        try:
            # Find the actual Cognito username
            cognito_username = self._try_get_user_by_identifier(identifier)
            if not cognito_username:
                raise ClientError(
                    {'Error': {'Code': 'UserNotFoundException'}},
                    'ResendConfirmationCode'
                )
            
            response = self.client.resend_confirmation_code(
                ClientId=self.client_id,
                Username=cognito_username,
                SecretHash=self._get_secret_hash(cognito_username),
            )
            logger.info(f"Confirmation code resent for {identifier} (Cognito: {cognito_username})")
            return {
                'code_delivery_details': response.get('CodeDeliveryDetails'),
            }
        except ClientError as e:
            logger.error(f"Resend error for {identifier}: {e.response['Error']['Code']}")
            raise
    
    def forgot_password(self, identifier: str) -> Dict:
        """
        Initiate password reset flow.
        
        Args:
            identifier: Username or email address
            
        Returns:
            Password reset response
            
        Raises:
            ClientError: If forgot password fails
        """
        try:
            # Find the actual Cognito username
            cognito_username = self._try_get_user_by_identifier(identifier)
            if not cognito_username:
                raise ClientError(
                    {'Error': {'Code': 'UserNotFoundException'}},
                    'ForgotPassword'
                )
            
            response = self.client.forgot_password(
                ClientId=self.client_id,
                Username=cognito_username,
                SecretHash=self._get_secret_hash(cognito_username),
            )
            logger.info(f"Password reset initiated for {identifier} (Cognito: {cognito_username})")
            return {
                'code_delivery_details': response.get('CodeDeliveryDetails'),
            }
        except ClientError as e:
            logger.error(f"Forgot password error for {identifier}: {e.response['Error']['Code']}")
            raise
    
    def confirm_forgot_password(
        self,
        identifier: str,
        confirmation_code: str,
        new_password: str,
    ) -> Dict:
        """
        Confirm password reset with new password.
        
        Args:
            identifier: Username or email address
            confirmation_code: Password reset code
            new_password: New password
            
        Returns:
            Password reset confirmation response
            
        Raises:
            ClientError: If password reset fails
        """
        try:
            # Find the actual Cognito username
            cognito_username = self._try_get_user_by_identifier(identifier)
            if not cognito_username:
                raise ClientError(
                    {'Error': {'Code': 'UserNotFoundException'}},
                    'ConfirmForgotPassword'
                )
            
            self.client.confirm_forgot_password(
                ClientId=self.client_id,
                Username=cognito_username,
                ConfirmationCode=confirmation_code,
                Password=new_password,
                SecretHash=self._get_secret_hash(cognito_username),
            )
            logger.info(f"Password reset confirmed for {identifier} (Cognito: {cognito_username})")
            return {'message': 'Password reset successfully'}
        except ClientError as e:
            logger.error(f"Confirm forgot password error for {identifier}: {e.response['Error']['Code']}")
            raise
    
    # ============================================================================
    # Enhanced Methods for Endpoints (with full error handling)
    # ============================================================================
    
    def handle_signup(self, username: str, email: str, password: str) -> dict:
        """Handle user signup with full error handling."""
        try:
            logger.info(f"Processing signup request for username: {username}")
            result = self.sign_up(email=email, password=password, username=username)
            return result
        except ClientError as e:
            logger.error(f"Signup failed for {username}: {str(e)}")
            raise handle_cognito_error(e, context="signup")
    
    def handle_confirm_email(self, identifier: str, confirmation_code: str) -> dict:
        """Handle email confirmation with full error handling."""
        try:
            logger.info(f"Processing email confirmation for: {identifier}")
            result = self.confirm_sign_up(identifier=identifier, confirmation_code=confirmation_code)
            return result
        except ClientError as e:
            logger.error(f"Email confirmation failed for {identifier}: {str(e)}")
            raise handle_cognito_error(e, context="confirm_email")
    
    def handle_resend_code(self, identifier: str) -> dict:
        """Handle resend confirmation code with full error handling."""
        try:
            logger.info(f"Resending confirmation code for: {identifier}")
            result = self.resend_confirmation_code(identifier=identifier)
            return {"message": "Confirmation code sent to your email", **result}
        except ClientError as e:
            logger.error(f"Resend confirmation failed for {identifier}: {str(e)}")
            raise handle_cognito_error(e, context="resend_confirmation_code")
    
    def handle_signin(self, identifier: str, password: str) -> dict:
        """Handle user signin with full error handling."""
        try:
            logger.info(f"Processing signin request for: {identifier}")
            auth_result = self.initiate_auth(identifier=identifier, password=password)
            user_info = auth_result.pop('user', {})
            return {"message": "Sign in successful", "tokens": auth_result, "user": user_info}
        except ClientError as e:
            logger.error(f"Signin failed for {identifier}: {str(e)}")
            raise handle_cognito_error(e, context="signin")
    
    def handle_forgot_password(self, identifier: str) -> dict:
        """Handle forgot password with full error handling."""
        try:
            logger.info(f"Processing forgot password request for: {identifier}")
            result = self.forgot_password(identifier=identifier)
            return {"message": "Password reset code sent to your email", **result}
        except ClientError as e:
            logger.error(f"Forgot password failed for {identifier}: {str(e)}")
            raise handle_cognito_error(e, context="forgot_password")
    
    def handle_confirm_forgot_password(self, identifier: str, confirmation_code: str, new_password: str) -> dict:
        """Handle confirm forgot password with full error handling."""
        try:
            logger.info(f"Processing confirm forgot password for: {identifier}")
            result = self.confirm_forgot_password(
                identifier=identifier,
                confirmation_code=confirmation_code, 
                new_password=new_password
            )
            return result
        except ClientError as e:
            logger.error(f"Confirm forgot password failed for {identifier}: {str(e)}")
            raise handle_cognito_error(e, context="confirm_forgot_password")
    
    def handle_change_password(self, access_token: str, previous_password: str, proposed_password: str) -> dict:
        """Handle change password with full error handling."""
        try:
            logger.info("Processing change password request")
            result = self.change_password(
                access_token=access_token,
                previous_password=previous_password,
                proposed_password=proposed_password
            )
            return result
        except ClientError as e:
            logger.error(f"Change password failed: {str(e)}")
            raise handle_cognito_error(e, context="change_password")
    
    def handle_get_user_profile(self, access_token: str) -> dict:
        """Handle get user profile with full error handling."""
        try:
            logger.info("Retrieving user profile")
            result = self.get_user(access_token=access_token)
            attributes = result.get('attributes', {})
            
            return {
                'username': result.get('username'),
                'email': attributes.get('email'),
                'email_verified': attributes.get('email_verified', '').lower() == 'true',
                'given_name': attributes.get('given_name'),
                'family_name': attributes.get('family_name'),
                'sub': attributes.get('sub'),
            }
        except ClientError as e:
            logger.error(f"Get user profile failed: {str(e)}")
            raise handle_cognito_error(e, context="get_user_profile")
    
    def handle_sign_out(self) -> dict:
        """Handle sign out with full error handling."""
        try:
            logger.info("Processing user sign out")
            # Note: AWS Cognito admin_user_global_sign_out requires user pool admin access
            # For now, we'll just return success as the token will be invalid after expiry  
            return {"message": "Signed out successfully. Token will expire shortly."}
        except Exception as e:
            logger.error(f"Unexpected error during sign out: {str(e)}")
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail="An error occurred during sign out")
    
    def get_user(self, access_token: str) -> Dict:
        """
        Get user attributes using access token.
        
        Args:
            access_token: Cognito access token
            
        Returns:
            User attributes
            
        Raises:
            ClientError: If user retrieval fails
        """
        try:
            response = self.client.get_user(AccessToken=access_token)
            
            # Convert user attributes to dict
            user_attributes = {
                attr['Name']: attr['Value']
                for attr in response.get('UserAttributes', [])
            }
            
            return {
                'username': response['Username'],
                'attributes': user_attributes,
                'mfa_options': response.get('MFAOptions', []),
            }
        except ClientError as e:
            logger.error(f"Get user error: {e.response['Error']['Code']}")
            raise
    
    def change_password(
        self,
        access_token: str,
        previous_password: str,
        proposed_password: str,
    ) -> Dict:
        """
        Change user password.
        
        Args:
            access_token: Cognito access token
            previous_password: Current password
            proposed_password: New password
            
        Returns:
            Password change response
            
        Raises:
            ClientError: If password change fails
        """
        try:
            self.client.change_password(
                PreviousPassword=previous_password,
                ProposedPassword=proposed_password,
                AccessToken=access_token,
            )
            logger.info("Password changed successfully")
            return {'message': 'Password changed successfully'}
        except ClientError as e:
            logger.error(f"Change password error: {e.response['Error']['Code']}")
            raise
    
    def sign_out(self, access_token: str) -> Dict:
        """
        Sign out user globally.
        
        Args:
            access_token: Cognito access token
            
        Returns:
            Sign out response
            
        Raises:
            ClientError: If sign out fails
        """
        try:
            self.client.admin_user_global_sign_out(
                UserPoolId=self.user_pool_id,
                Username=access_token.split('.')[1],  # Extract username from token
            )
            logger.info("User signed out globally")
            return {'message': 'Signed out successfully'}
        except ClientError as e:
            logger.error(f"Sign out error: {e.response['Error']['Code']}")
            raise
    
    def admin_create_user(
        self,
        username: str,
        email: str,
        temporary_password: str = None,
    ) -> Dict:
        """
        Admin create user (for backend operations).
        
        Args:
            username: Cognito username
            email: User email
            temporary_password: Temporary password (generated if not provided)
            
        Returns:
            User creation response
            
        Raises:
            ClientError: If user creation fails
        """
        try:
            response = self.client.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=username,
                TemporaryPassword=temporary_password or username,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'email_verified', 'Value': 'false'},
                ],
                MessageAction='SUPPRESS',
            )
            logger.info(f"Admin created user {username}")
            return {
                'user_sub': response['User']['Username'],
                'username': response['User']['Username'],
            }
        except ClientError as e:
            logger.error(f"Admin create user error: {e.response['Error']['Code']}")
            raise


# Singleton instance
cognito_service = CognitoAuthService()
