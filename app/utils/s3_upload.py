"""S3 upload utilities for file management."""

import boto3
import asyncio
import aiofiles
from typing import Dict, Optional, Callable, Any
from botocore.exceptions import ClientError, NoCredentialsError
from app.core.config import settings
import uuid
import mimetypes
import os


class S3UploadManager:
    """Manager class for S3 file uploads with progress tracking."""
    
    def __init__(self):
        """Initialize S3 client with configured credentials."""
        self.s3_client = boto3.client(
            's3',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.bucket_name = settings.S3_BUCKET_NAME
    
    async def upload_file(
        self, 
        file_content: bytes, 
        file_key: str, 
        content_type: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Upload file content to S3 with progress tracking.
        
        Args:
            file_content: File content as bytes
            file_key: S3 object key (path)
            content_type: MIME type of the file
            progress_callback: Callback function for progress updates (bytes_transferred, total_bytes)
            
        Returns:
            Dict with upload details
            
        Raises:
            Exception: If upload fails
        """
        try:
            # Determine content type
            if not content_type:
                content_type, _ = mimetypes.guess_type(file_key)
                if not content_type:
                    content_type = 'application/octet-stream'
            
            # For small files, upload directly
            file_size = len(file_content)
            
            # Use multipart upload for larger files (>5MB)
            if file_size > 5 * 1024 * 1024:
                return await self._multipart_upload(
                    file_content, file_key, content_type, progress_callback
                )
            else:
                return await self._simple_upload(
                    file_content, file_key, content_type, progress_callback
                )
                
        except NoCredentialsError:
            raise Exception("AWS credentials not configured")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                raise Exception(f"S3 bucket '{self.bucket_name}' does not exist")
            elif error_code == 'AccessDenied':
                raise Exception("Access denied to S3 bucket")
            else:
                raise Exception(f"S3 upload error: {e.response['Error']['Message']}")
        except Exception as e:
            raise Exception(f"Upload failed: {str(e)}")
    
    async def _simple_upload(
        self,
        file_content: bytes,
        file_key: str,
        content_type: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """Simple upload for smaller files."""
        file_size = len(file_content)
        
        # Run the upload in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._put_object,
            file_content,
            file_key,
            content_type
        )
        
        # Call progress callback with completion
        if progress_callback:
            progress_callback(file_size, file_size)
        
        return {
            'file_key': file_key,
            'file_size': file_size,
            'upload_id': None,
            'etag': result.get('ETag', '').strip('"'),
            's3_url': f"s3://{self.bucket_name}/{file_key}"
        }
    
    def _put_object(self, file_content: bytes, file_key: str, content_type: str) -> Dict[str, Any]:
        """Execute S3 put_object in thread."""
        return self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=file_key,
            Body=file_content,
            ContentType=content_type,
            ServerSideEncryption='AES256'  # Enable server-side encryption
        )
    
    async def _multipart_upload(
        self,
        file_content: bytes,
        file_key: str,
        content_type: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """Multipart upload for larger files with progress tracking."""
        file_size = len(file_content)
        chunk_size = 5 * 1024 * 1024  # 5MB chunks
        
        # Initiate multipart upload
        response = self.s3_client.create_multipart_upload(
            Bucket=self.bucket_name,
            Key=file_key,
            ContentType=content_type,
            ServerSideEncryption='AES256'
        )
        upload_id = response['UploadId']
        
        parts = []
        bytes_uploaded = 0
        
        try:
            # Upload parts
            part_number = 1
            for start in range(0, file_size, chunk_size):
                end = min(start + chunk_size, file_size)
                chunk = file_content[start:end]
                
                # Upload part in thread pool
                loop = asyncio.get_event_loop()
                part_response = await loop.run_in_executor(
                    None,
                    self._upload_part,
                    chunk,
                    file_key,
                    upload_id,
                    part_number
                )
                
                parts.append({
                    'ETag': part_response['ETag'],
                    'PartNumber': part_number
                })
                
                bytes_uploaded += len(chunk)
                
                # Call progress callback
                if progress_callback:
                    progress_callback(bytes_uploaded, file_size)
                
                part_number += 1
            
            # Complete multipart upload
            result = self.s3_client.complete_multipart_upload(
                Bucket=self.bucket_name,
                Key=file_key,
                UploadId=upload_id,
                MultipartUpload={'Parts': parts}
            )
            
            return {
                'file_key': file_key,
                'file_size': file_size,
                'upload_id': upload_id,
                'etag': result.get('ETag', '').strip('"'),
                's3_url': f"s3://{self.bucket_name}/{file_key}"
            }
            
        except Exception as e:
            # Abort multipart upload on error
            try:
                self.s3_client.abort_multipart_upload(
                    Bucket=self.bucket_name,
                    Key=file_key,
                    UploadId=upload_id
                )
            except:
                pass  # Best effort cleanup
            raise e
    
    def _upload_part(self, chunk: bytes, file_key: str, upload_id: str, part_number: int) -> Dict[str, Any]:
        """Upload a single part in thread."""
        return self.s3_client.upload_part(
            Bucket=self.bucket_name,
            Key=file_key,
            PartNumber=part_number,
            UploadId=upload_id,
            Body=chunk
        )
    
    async def delete_file(self, file_key: str) -> bool:
        """
        Delete a file from S3.
        
        Args:
            file_key: S3 object key to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.s3_client.delete_object,
                self.bucket_name,
                file_key
            )
            return True
        except Exception:
            return False
    
    async def file_exists(self, file_key: str) -> bool:
        """
        Check if a file exists in S3.
        
        Args:
            file_key: S3 object key to check
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.s3_client.head_object,
                self.bucket_name,
                file_key
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise e
    
    def generate_presigned_url(self, file_key: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for file download.
        
        Args:
            file_key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL string
        """
        try:
            return self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_key},
                ExpiresIn=expiration
            )
        except ClientError as e:
            raise Exception(f"Failed to generate presigned URL: {str(e)}")


# Global S3 manager instance
s3_manager = S3UploadManager()


def sanitize_project_name(project_name: str) -> str:
    """
    Sanitize project name for safe use in S3 folder names.
    
    Args:
        project_name: Original project name
        
    Returns:
        Sanitized project name safe for S3 folder names
    """
    import re
    
    if not project_name:
        return "unnamed"
    
    # Replace spaces with underscores and keep only alphanumeric, underscores, and hyphens
    sanitized = re.sub(r'[^a-zA-Z0-9\-_]', '_', project_name.strip())
    
    # Remove multiple consecutive underscores
    sanitized = re.sub(r'_{2,}', '_', sanitized)
    
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    
    # Ensure it's not empty and limit length
    if not sanitized:
        sanitized = "unnamed"
    
    # Limit to 50 characters for S3 folder safety
    return sanitized[:50].lower()


def get_job_root_folder(job_id: str, project_name: str = None) -> str:
    """
    Generate root job folder path.
    
    Args:
        job_id: Job ID
        project_name: Optional project name for folder structure
        
    Returns:
        Folder path in format: {job_id}_{project_name}
    """
    if project_name:
        sanitized_name = sanitize_project_name(project_name)
        return f"{job_id}_{sanitized_name}"
    else:
        return job_id


def get_bom_folder_path(job_id: str, project_name: str = None) -> str:
    """
    Generate BOM folder path for storing all BOM files.
    
    Args:
        job_id: Job ID
        project_name: Optional project name for folder structure
        
    Returns:
        Folder path in format: {job_id}_{project_name}/bom
    """
    folder_name = get_job_root_folder(job_id, project_name)
    return f"{folder_name}/bom"


def get_s3_key_for_bom(job_id: str, filename: str, project_name: str = None) -> str:
    """
    Generate S3 key for BOM file as per Story 1.2 requirements.
    
    Args:
        job_id: Job ID
        filename: Original filename
        project_name: Optional project name for folder structure
        
    Returns:
        S3 key in format: {job_id}_{project_name}/bom/{job_id}_bom_{original_filename}
    """
    # Get the BOM folder path
    bom_folder = get_bom_folder_path(job_id, project_name)
    
    # Create BOM filename with job_id prefix and original filename
    bom_filename = f"{job_id}_bom_{filename}"
    
    return f"{bom_folder}/{bom_filename}"


def get_quotes_folder_path(job_id: str, project_name: str = None) -> str:
    """
    Generate quotes folder path for storing all quote files.
    
    Args:
        job_id: Job ID
        project_name: Optional project name for folder structure
        
    Returns:
        Folder path in format: {job_id}_{project_name}/quotes
    """
    folder_name = get_job_root_folder(job_id, project_name)
    return f"{folder_name}/quotes"


def get_s3_key_for_quote(job_id: str, filename: str, project_name: str = None) -> str:
    """
    Generate S3 key for quote file.
    
    Args:
        job_id: Job ID
        filename: Original filename
        project_name: Optional project name for folder structure
        
    Returns:
        S3 key in format: {job_id}_{project_name}/quotes/{job_id}_quote_{original_filename}
    """
    # Get the quotes folder path
    quotes_folder = get_quotes_folder_path(job_id, project_name)
    
    # Create quote filename with job_id prefix and original filename
    quote_filename = f"{job_id}_quote_{filename}"
    
    return f"{quotes_folder}/{quote_filename}"


async def create_s3_job_folder(job_id: str, project_name: str = None) -> bool:
    """
    Create a job folder in S3 by uploading a placeholder object.
    
    Args:
        job_id: Job ID
        project_name: Optional project name for folder structure
        
    Returns:
        True if successful, False otherwise
    """
    try:
        folder_name = get_job_root_folder(job_id, project_name)
        placeholder_key = f"{folder_name}/.placeholder"
        await s3_manager.upload_file(
            file_content=b"",
            file_key=placeholder_key,
            content_type="text/plain"
        )
        return True
    except Exception:
        return False