from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date, time


class JobBase(BaseModel):
    """Base job schema."""
    project_name: str = Field(..., min_length=1, max_length=100, description="Project name for the bid")
    bid_date: Optional[date] = Field(None, description="Optional bid date")
    bid_time: Optional[str] = Field(None, description="Optional bid time (e.g., '7:10 AM' or '14:30')")
    client_name: Optional[str] = Field(None, max_length=255, description="Client name for the project")
    location: Optional[str] = Field(None, max_length=255, description="Project location")



    @field_validator("bid_date", mode="before")
    @classmethod
    def parse_bid_date(cls, value):
        if isinstance(value, str):
            try:
                # Handle ISO format date (2026-02-05 or 2026-02-05T...)
                if 'T' in value:
                    # Extract date part from ISO datetime
                    return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
                # Handle date only format (2026-02-05)
                return datetime.strptime(value, "%Y-%m-%d").date()
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid date format: {value}. Expected YYYY-MM-DD")
        elif isinstance(value, datetime):
            return value.date()
        elif isinstance(value, date):
            return value
        return value
    
    @field_validator("bid_time", mode="before")
    @classmethod
    def parse_bid_time(cls, value):
        if isinstance(value, str):
            # Validate format but return as string to preserve AM/PM
            value = value.strip()
            try:
                # Try 12-hour format with AM/PM (7:10:00 AM or 7:10 AM)
                if 'AM' in value.upper() or 'PM' in value.upper():
                    # Handle H:MM:SS AM/PM format
                    if value.count(':') == 2:
                        datetime.strptime(value, "%I:%M:%S %p")
                    # Handle H:MM AM/PM format
                    elif value.count(':') == 1:
                        datetime.strptime(value, "%I:%M %p")
                    return value  # Return original string with AM/PM
                # Handle 24-hour ISO format time (14:30:00 or HH:MM:SS)
                elif value.count(':') == 2:
                    datetime.strptime(value, "%H:%M:%S")
                    return value
                # Handle 24-hour HH:MM format
                elif value.count(':') == 1:
                    datetime.strptime(value, "%H:%M")
                    return value
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid time format: {value}. Expected HH:MM:SS, HH:MM, H:MM:SS AM/PM, or H:MM AM/PM")
        elif isinstance(value, datetime):
            return value.strftime("%I:%M %p")
        elif isinstance(value, time):
            return value.strftime("%I:%M %p")
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
    bid_date: Optional[date] = None
    bid_time: Optional[str] = None
    client_name: Optional[str] = None
    location: Optional[str] = None


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
    bid_date: Optional[date] = None
    bid_time: Optional[str] = None
    client_name: Optional[str] = None
    location: Optional[str] = None


class JobStatusResponse(BaseModel):
    """Response for job status polling."""
    job_id: str
    status: str
    error_message: Optional[str] = Field(None, description="Error message if status is failed")


class BOMUploadResponse(BaseModel):
    """Response for successful BOM file upload."""
    job_id: str = Field(..., description="Job ID")
    uploaded_files: List[dict] = Field(..., description="List of uploaded BOM file details")
    total_files: int = Field(..., description="Total number of BOM files uploaded")


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
