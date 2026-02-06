from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union
import secrets


class Settings(BaseSettings):
    """Application settings."""
    
    # Project Info
    PROJECT_NAME: str = "Argus Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    
    # Database
    DATABASE_URL: str = ""
    
    # CORS
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from string."""
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            return [i.strip() for i in self.BACKEND_CORS_ORIGINS.split(",")]
        return self.BACKEND_CORS_ORIGINS
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # AWS Configuration
    AWS_REGION: str
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    
    # S3 Configuration
    S3_BUCKET_NAME: str
    S3_UPLOAD_FOLDER: str
    
    # DynamoDB Configuration
    DYNAMODB_JOBS_TABLE: str
    
    # Cognito Configuration
    COGNITO_USER_POOL_ID: str
    COGNITO_CLIENT_ID: str
    COGNITO_CLIENT_SECRET: str
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()