"""
AWS Cognito authentication service.
Handles user signup, signin, email verification, and token management.
"""

import hmac
import hashlib
import base64
from typing import Dict
import boto3
from botocore.exceptions import ClientError
from loguru import logger

from app.core.config import settings


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
        email: str,
        confirmation_code: str,
    ) -> Dict:
        """
        Confirm user email during signup.
        
        Args:
            email: User email (used as identifier with email alias)
            confirmation_code: Email confirmation code
            
        Returns:
            Confirmation response
            
        Raises:
            ClientError: If confirmation fails
        """
        try:
            # With email alias enabled, can confirm using email as identifier
            self.client.confirm_sign_up(
                ClientId=self.client_id,
                Username=email,
                ConfirmationCode=confirmation_code,
                SecretHash=self._get_secret_hash(email),
            )
            logger.info(f"Email confirmed for user {email}")
            return {'message': 'Email confirmed successfully'}
        except ClientError as e:
            logger.error(f"Confirmation error for {email}: {e.response['Error']['Code']}")
            raise
    
    def initiate_auth(
        self,
        username: str,
        password: str,
    ) -> Dict:
        """
        Authenticate user using username and password.
        
        Args:
            username: Cognito username or email (if email alias is enabled)
            password: User password
            
        Returns:
            Authentication response with tokens
            
        Raises:
            ClientError: If authentication fails
        """
        try:
            # Use ADMIN_USER_PASSWORD_AUTH flow for username/password authentication
            response = self.client.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow='ADMIN_USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password,
                    'SECRET_HASH': self._get_secret_hash(username),
                },
            )
            logger.info(f"User {username} authenticated successfully")
            
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
                logger.info(f"Retrieved user info for {username}: {user_info}")
            except Exception as e:
                logger.warning(f"Could not retrieve user info for {username}: {str(e)}")
            
            return {
                'access_token': access_token,
                'id_token': auth_result.get('IdToken'),
                'refresh_token': auth_result.get('RefreshToken'),
                'expires_in': auth_result.get('ExpiresIn'),
                'token_type': auth_result.get('TokenType', 'Bearer'),
                'user': user_info,
            }
        except ClientError as e:
            logger.error(f"Authentication error for {username}: {e.response['Error']['Code']}")
            raise
    
    def resend_confirmation_code(self, email: str) -> Dict:
        """
        Resend email confirmation code to user.
        
        Args:
            email: User email (used as Cognito username)
            
        Returns:
            Resend response
            
        Raises:
            ClientError: If resend fails
        """
        try:
            response = self.client.resend_confirmation_code(
                ClientId=self.client_id,
                Username=email,
                SecretHash=self._get_secret_hash(email),
            )
            logger.info(f"Confirmation code resent for {email}")
            return {
                'code_delivery_details': response.get('CodeDeliveryDetails'),
            }
        except ClientError as e:
            logger.error(f"Resend error for {email}: {e.response['Error']['Code']}")
            raise
    
    def forgot_password(self, email: str) -> Dict:
        """
        Initiate password reset flow.
        
        Args:
            email: User email address
            
        Returns:
            Password reset response
            
        Raises:
            ClientError: If forgot password fails
        """
        try:
            response = self.client.forgot_password(
                ClientId=self.client_id,
                Username=email,
                SecretHash=self._get_secret_hash(email),
            )
            logger.info(f"Password reset initiated for {email}")
            return {
                'code_delivery_details': response.get('CodeDeliveryDetails'),
            }
        except ClientError as e:
            logger.error(f"Forgot password error for {email}: {e.response['Error']['Code']}")
            raise
    
    def confirm_forgot_password(
        self,
        email: str,
        confirmation_code: str,
        new_password: str,
    ) -> Dict:
        """
        Confirm password reset with new password.
        
        Args:
            email: User email (used as Cognito username)
            confirmation_code: Password reset code
            new_password: New password
            
        Returns:
            Password reset confirmation response
            
        Raises:
            ClientError: If password reset fails
        """
        try:
            self.client.confirm_forgot_password(
                ClientId=self.client_id,
                Username=email,
                ConfirmationCode=confirmation_code,
                Password=new_password,
                SecretHash=self._get_secret_hash(email),
            )
            logger.info(f"Password reset confirmed for {email}")
            return {'message': 'Password reset successfully'}
        except ClientError as e:
            logger.error(f"Confirm forgot password error for {email}: {e.response['Error']['Code']}")
            raise
    
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
