import uuid
import re
import os
import asyncio
import tempfile
from typing import Optional, List, Tuple, Callable
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import UploadFile, HTTPException
from app.core.config import settings
from app.models.job import Job
from app.schemas.job import JobCreate, JobListItem, JobDetailResponse
from app.utils.file_upload import (
    validate_file_extension, validate_file_magic_number,
    ALLOWED_BOM_EXTENSIONS, ALLOWED_QUOTE_EXTENSIONS,
    MAX_BOM_FILE_SIZE, MAX_QUOTE_FILE_SIZE,
    validate_bom_columns, sanitize_filename
)
from app.utils.s3_upload import (
    s3_manager, get_s3_key_for_bom, get_s3_key_for_quote, 
    create_s3_job_folder
)



class JobService:
    """Service class for job operations in PostgreSQL."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_job(self, user_id: str, job_in: JobCreate) -> Job:
        """
        Create a new job and store in PostgreSQL.
        
        Args:
            user_id: User ID who created the job
            job_in: Job creation schema with project_name, due_date, gc_name
            
        Returns:
            Created Job object
            
        Raises:
            ValueError: If project name is invalid
        """
        # Validate project name format
        if not self._is_valid_project_name(job_in.project_name):
            raise ValueError(
                "Project name can only contain letters, numbers, spaces, and dashes"
            )
        
        job_id = str(uuid.uuid4())
        
        job = Job(
            job_id=job_id,
            user_id=user_id,
            project_name=job_in.project_name,
            status="draft",
            due_date=job_in.due_date,
            gc_name=job_in.gc_name,
        )
        
        # Create S3 folder for this job as per Story 1.1 acceptance criteria
        try:
            folder_created = await create_s3_job_folder(job_id, job_in.project_name)
            if not folder_created:
                raise Exception("Failed to create job folder in S3")
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create S3 folder: {str(e)}"
            )
        
        # Store in PostgreSQL
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        
        return job
    
    async def get_job_by_id(self, job_id: str, user_id: Optional[str] = None) -> Optional[Job]:
        """
        Get job by job_id.
        
        Args:
            job_id: Job ID to retrieve
            user_id: Optional user_id to verify ownership
            
        Returns:
            Job object or None if not found
        """
        query = select(Job).where(Job.job_id == job_id)
        
        # If user_id provided, ensure ownership
        if user_id:
            query = query.where(Job.user_id == user_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_jobs_by_user(
        self, 
        user_id: str, 
        skip: int = 0, 
        limit: int = 100,
        sort_by: str = "created_at",
        sort_order: int = -1
    ) -> List[JobListItem]:
        """
        Get all jobs for a user with pagination and sorting.
        Returns JobListItem objects formatted for list view.
        """
        from sqlalchemy import desc, asc
        
        query = select(Job).where(Job.user_id == user_id)
        
        # Apply sorting
        if sort_by == "created_at":
            query = query.order_by(desc(Job.created_at) if sort_order == -1 else asc(Job.created_at))
        else:
            query = query.order_by(desc(getattr(Job, sort_by)) if sort_order == -1 else asc(getattr(Job, sort_by)))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        jobs = result.scalars().all()
        
        return [JobListItem(
            job_id=job.job_id,
            project_name=job.project_name,
            status=job.status,
            created_at=job.created_at,
            due_date=job.due_date,
            gc_name=job.gc_name,
        ) for job in jobs]
    
    async def count_user_jobs(self, user_id: str) -> int:
        """Get total count of jobs for a user."""
        from sqlalchemy import func
        query = select(func.count(Job.id)).where(Job.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def get_job_detail(self, job_id: str, user_id: Optional[str] = None) -> Optional[JobDetailResponse]:
        """
        Get full job details for detail view.
        Returns JobDetailResponse formatted object.
        """
        job = await self.get_job_by_id(job_id=job_id, user_id=user_id)
        if not job:
            return None
        
        return JobDetailResponse(
            job_id=job.job_id,
            user_id=job.user_id,
            project_name=job.project_name,
            status=job.status,
            created_at=job.created_at,
            due_date=job.due_date,
            gc_name=job.gc_name,
            bom_file_key=job.bom_file_key,
            quote_file_keys=job.quote_file_keys or [],
            execution_arn=job.execution_arn,
        )
    
    async def update_job_status(
        self, 
        job_id: str, 
        status: str,
        user_id: Optional[str] = None
    ) -> Optional[Job]:
        """
        Update job status.
        
        Args:
            job_id: Job ID to update
            status: New status (draft, processing, ready_for_review, completed, failed)
            user_id: Optional user_id to verify ownership
            
        Returns:
            Updated Job object or None if not found
        """
        job = await self.get_job_by_id(job_id, user_id)
        if not job:
            return None
        
        job.status = status
        await self.db.commit()
        await self.db.refresh(job)
        
        return job
    
    async def update_bom_file(
        self,
        job_id: str,
        bom_file_key: str,
        user_id: Optional[str] = None
    ) -> Optional[Job]:
        """Update BOM file key for a job."""
        job = await self.get_job_by_id(job_id, user_id)
        if not job:
            return None
        
        job.bom_file_key = bom_file_key
        await self.db.commit()
        await self.db.refresh(job)
        
        return job
    
    async def add_quote_file(
        self,
        job_id: str,
        quote_file_key: str,
        user_id: Optional[str] = None
    ) -> Optional[Job]:
        """Add a quote file to the job's quote_file_keys list."""
        job = await self.get_job_by_id(job_id, user_id)
        if not job:
            return None
        
        if job.quote_file_keys is None:
            job.quote_file_keys = []
        
        if quote_file_key not in job.quote_file_keys:
            job.quote_file_keys.append(quote_file_key)
        
        await self.db.commit()
        await self.db.refresh(job)
        
        return job
    
    async def update_execution_arn(
        self,
        job_id: str,
        execution_arn: str,
        user_id: Optional[str] = None
    ) -> Optional[Job]:
        """Update Step Functions execution ARN for a job."""
        job = await self.get_job_by_id(job_id, user_id)
        if not job:
            return None
        
        job.execution_arn = execution_arn
        await self.db.commit()
        await self.db.refresh(job)
        
        return job
    
    async def delete_job(
        self,
        job_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """Delete a job."""
        job = await self.get_job_by_id(job_id, user_id)
        if not job:
            return False
        
        await self.db.delete(job)
        await self.db.commit()
        
        return True
    
    @staticmethod
    def _is_valid_project_name(project_name: str) -> bool:
        """
        Validate project name format.
        - Max 100 characters
        - Only alphanumeric, spaces, and dashes allowed
        """
        if not project_name or len(project_name) > 100:
            return False
        
        # Allow letters, numbers, spaces, and dashes only
        pattern = r"^[a-zA-Z0-9\s\-]+$"
        return bool(re.match(pattern, project_name))
    
    async def upload_bom_file(
        self, 
        job_id: str, 
        user_id: str, 
        file: UploadFile,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> dict:
        """
        Handle BOM file upload for a job (Story 1.2).
        
        Args:
            job_id: Job ID
            user_id: User ID for ownership verification
            file: Uploaded BOM file
            progress_callback: Optional callback for upload progress
            
        Returns:
            Dict with upload details
            
        Raises:
            ValueError: If file is invalid or job not found
            HTTPException: If upload fails
        """
        # Verify job exists - skip user ownership verification if anonymous
        if user_id == "anonymous":
            job = await self.get_job_by_id(job_id)
        else:
            job = await self.get_job_by_id(job_id, user_id)
        
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Validate file extension
        if not validate_file_extension(file.filename, ALLOWED_BOM_EXTENSIONS):
            raise ValueError(f"Invalid file type. BOM file must be one of: {', '.join(ALLOWED_BOM_EXTENSIONS)}")
        
        # Read file content
        try:
            file_content = await file.read()
        except Exception as e:
            raise ValueError(f"Failed to read file: {str(e)}")
        
        # Check file size
        file_size = len(file_content)
        if file_size == 0:
            raise ValueError("File is empty")
        
        if file_size > MAX_BOM_FILE_SIZE:
            max_size_mb = MAX_BOM_FILE_SIZE // (1024 * 1024)
            raise ValueError(f"File size exceeds maximum limit of {max_size_mb}MB")
        
        # Validate file magic number
        file_ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if not validate_file_magic_number(file_content, file_ext):
            raise ValueError("File appears to be corrupted or not a valid Excel file")
        
        # Create temporary file for validation
        row_count = 0
        try:
            with tempfile.NamedTemporaryFile(suffix=f'.{file_ext}', delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file.flush()
                
                # Validate BOM columns
                try:
                    row_count = validate_bom_columns(temp_file.name)
                except Exception as e:
                    raise ValueError(f"BOM validation failed: {str(e)}")
                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(temp_file.name)
                    except:
                        pass
        except (OSError, IOError) as e:
            raise ValueError(f"File processing failed: {str(e)}")
        
        # Generate S3 key as per Story 1.2 requirements
        sanitized_filename = sanitize_filename(file.filename)
        s3_key = get_s3_key_for_bom(job_id, sanitized_filename, job.project_name)
        
        # Upload to S3 with progress tracking
        try:
            upload_result = await s3_manager.upload_file(
                file_content=file_content,
                file_key=s3_key,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                progress_callback=progress_callback
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file to S3: {str(e)}"
            )
        
        # Update job with BOM file key
        job.bom_file_key = s3_key
        job.status = "bom_uploaded"  # Update status to indicate BOM uploaded
        
        try:
            await self.db.commit()
            await self.db.refresh(job)
        except Exception as e:
            # Try to clean up S3 file if database update fails
            try:
                await s3_manager.delete_file(s3_key)
            except:
                pass
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update job: {str(e)}"
            )
        
        return {
            "job_id": job_id,
            "filename": sanitized_filename,
            "file_key": s3_key,
            "row_count": row_count,
            "file_size": file_size,
            "s3_url": upload_result.get("s3_url"),
            "upload_id": upload_result.get("upload_id"),
            "etag": upload_result.get("etag")
        }
    
    async def upload_quote_files(self, job_id: str, user_id: str, files: List[UploadFile]) -> dict:
        """
        Handle multiple quote file uploads for a job (Story 1.3).
        
        Args:
            job_id: Job ID
            user_id: User ID for ownership verification
            files: List of uploaded quote files
            
        Returns:
            Dict with upload details
            
        Raises:
            ValueError: If files are invalid or job not found
            HTTPException: If upload fails
        """
        # Verify job exists - skip user ownership verification if anonymous
        if user_id == "anonymous":
            job = await self.get_job_by_id(job_id)
        else:
            job = await self.get_job_by_id(job_id, user_id)
        
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if len(files) > 15:
            raise ValueError("Maximum 15 quote files allowed")
        
        uploaded_files = []
        quote_file_keys = job.quote_file_keys or []
        
        try:
            for i, file in enumerate(files):
                # Validate file extension
                if not validate_file_extension(file.filename, ALLOWED_QUOTE_EXTENSIONS):
                    raise ValueError(f"Invalid file type for '{file.filename}'. Quote files must be one of: {', '.join(ALLOWED_QUOTE_EXTENSIONS)}")
                
                # Read file content
                try:
                    file_content = await file.read()
                except Exception as e:
                    raise ValueError(f"Failed to read file '{file.filename}': {str(e)}")
                
                # Check file size
                file_size = len(file_content)
                if file_size == 0:
                    raise ValueError(f"File '{file.filename}' is empty")
                
                if file_size > MAX_QUOTE_FILE_SIZE:
                    max_size_mb = MAX_QUOTE_FILE_SIZE // (1024 * 1024)
                    raise ValueError(f"File '{file.filename}' exceeds maximum limit of {max_size_mb}MB")
                
                # Validate file magic number (except for CSV which has no fixed signature)
                file_ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
                if file_ext != "csv" and not validate_file_magic_number(file_content, file_ext):
                    raise ValueError(f"File '{file.filename}' appears to be corrupted or invalid")
                
                # Generate S3 key for quote file
                sanitized_filename = sanitize_filename(file.filename)
                quote_index = i + len(quote_file_keys) + 1
                s3_key = get_s3_key_for_quote(job_id, sanitized_filename, quote_index, job.project_name)
                
                # Upload to S3
                try:
                    upload_result = await s3_manager.upload_file(
                        file_content=file_content,
                        file_key=s3_key,
                        content_type="application/octet-stream"  # Generic content type for various file types
                    )
                except Exception as e:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to upload file '{file.filename}' to S3: {str(e)}"
                    )
                
                # Add to quote file keys
                quote_file_keys.append(s3_key)
                
                uploaded_files.append({
                    "filename": sanitized_filename,
                    "original_filename": file.filename,
                    "file_key": s3_key,
                    "file_size": file_size,
                    "vendor_name": "",  # Can be edited later by user
                    "s3_url": upload_result.get("s3_url"),
                    "upload_id": upload_result.get("upload_id"),
                    "etag": upload_result.get("etag")
                })
            
            # Update job with new quote file keys
            job.quote_file_keys = quote_file_keys
            job.status = "quotes_uploaded"  # Update status to indicate quotes uploaded
            
            try:
                await self.db.commit()
                await self.db.refresh(job)
            except Exception as e:
                # Try to clean up S3 files if database update fails
                for file_info in uploaded_files:
                    try:
                        await s3_manager.delete_file(file_info["file_key"])
                    except:
                        pass
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to update job: {str(e)}"
                )
            
            return {
                "job_id": job_id,
                "uploaded_files": uploaded_files,
                "total_files": len(uploaded_files)
            }
            
        except (HTTPException, ValueError) as e:
            # Clean up any uploaded S3 files on error
            for file_info in uploaded_files:
                try:
                    await s3_manager.delete_file(file_info["file_key"])
                except:
                    pass
            raise
    
    async def start_analysis(self, job_id: str, user_id: str) -> dict:
        """
        Start analysis for a job (Story 1.4).
        
        Args:
            job_id: Job ID
            user_id: User ID for ownership verification
            
        Returns:
            Dict with analysis start details
            
        Raises:
            ValueError: If job is not ready for analysis
        """
        # Verify job exists and user owns it
        job = await self.get_job_by_id(job_id, user_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Check if BOM file is uploaded
        if not job.bom_file_key:
            raise ValueError("BOM file must be uploaded before starting analysis")
        
        # Check if at least one quote file is uploaded
        if not job.quote_file_keys or len(job.quote_file_keys) == 0:
            raise ValueError("At least one quote file must be uploaded before starting analysis")
        
        # In production, this would trigger Step Functions
        # For now, we'll simulate with a mock execution ARN
        execution_arn = f"arn:aws:states:us-east-1:123456789012:execution:argus-analysis-sm:{job_id}-{int(datetime.now().timestamp())}"
        
        # Update job status and execution ARN
        job.status = "processing"
        job.execution_arn = execution_arn
        await self.db.commit()
        await self.db.refresh(job)
        
        return {
            "job_id": job_id,
            "execution_arn": execution_arn,
            "status": "processing",
            "estimated_duration_minutes": 5
        }
