from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class JobBase(BaseModel):
    """Base job schema."""
    project_name: str = Field(..., min_length=1, max_length=100, description="Project name for the bid")
    due_date: Optional[datetime] = Field(None, description="Optional due date for the bid")
    gc_name: Optional[str] = Field(None, max_length=200, description="General contractor name")



    @field_validator("due_date", mode="before")
    @classmethod
    def parse_due_date(cls, value):
        if isinstance(value, str):
            try:
                # Handle ISO format (2026-02-05T11:00:00)
                if 'T' in value:
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                # Handle date only format (2026-02-05)
                elif len(value) == 10 and value.count('-') == 2:
                    return datetime.strptime(value, "%Y-%m-%d")
                # Handle datetime with space separator (2026-02-05 11:00:00)
                else:
                    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid date format: {value}. Expected ISO format (YYYY-MM-DDTHH:MM:SS) or YYYY-MM-DD HH:MM:SS")
        return value

class JobCreate(JobBase):
    """Schema for creating a new job."""
    pass


class JobStatusUpdate(BaseModel):
    """Schema for updating job status."""
    status: str = Field(..., description="Job status: draft, processing, ready_for_review, completed, failed")


class JobRead(JobBase):
    """Schema for reading job data."""
    job_id: str = Field(..., description="Unique job identifier (UUID)")
    user_id: str = Field(..., description="User who created the job")
    status: str = Field(..., description="Current job status")
    created_at: datetime = Field(..., description="Timestamp when job was created")
    bom_file_key: Optional[str] = Field(None, description="S3 key for BOM file")
    quote_file_keys: List[str] = Field(default_factory=list, description="List of S3 keys for quote files")
    execution_arn: Optional[str] = Field(None, description="Step Functions execution ARN")

    class Config:
        from_attributes = True


class JobListItem(BaseModel):
    """Simplified job schema for list view."""
    job_id: str
    project_name: str
    status: str
    created_at: datetime
    due_date: Optional[datetime] = None
    gc_name: Optional[str] = None


class JobDetailResponse(JobRead):
    """Detailed job response with all fields."""
    pass


class JobCreatedResponse(BaseModel):
    """Response when a job is created."""
    job_id: str = Field(..., description="Newly created job ID")
    user_id: str = Field(..., description="User who created the job")
    project_name: str
    created_at: datetime
    status: str = "draft"


class JobStatusResponse(BaseModel):
    """Response for job status polling."""
    job_id: str
    status: str
    current_step: Optional[str] = Field(None, description="Current processing step")
    elapsed_time: Optional[int] = Field(None, description="Elapsed time in seconds")
    estimated_time_remaining: Optional[int] = Field(None, description="Estimated time remaining in seconds")
    error_message: Optional[str] = Field(None, description="Error message if status is failed")


class BOMUploadResponse(BaseModel):
    """Response for successful BOM file upload."""
    job_id: str = Field(..., description="Job ID")
    filename: str = Field(..., description="Original filename")
    file_key: str = Field(..., description="Storage file key/path")
    row_count: Optional[int] = Field(None, description="Number of rows in BOM file")
    file_size: int = Field(..., description="File size in bytes")


class QuoteUploadResponse(BaseModel):
    """Response for successful quote file upload."""
    job_id: str = Field(..., description="Job ID")
    uploaded_files: List[dict] = Field(..., description="List of uploaded file details")
    total_files: int = Field(..., description="Total number of files uploaded")


class AnalysisStartResponse(BaseModel):
    """Response when analysis is started."""
    job_id: str = Field(..., description="Job ID")
    execution_arn: str = Field(..., description="Step Functions execution ARN")
    status: str = Field(default="processing", description="Updated job status")
    estimated_duration_minutes: int = Field(default=5, description="Estimated processing time")
