from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List
from app.api.deps import get_current_user
from app.db.session import get_database
from app.services.job_service import JobService
from app.schemas.job import JobCreate, JobCreatedResponse, JobListItem, JobDetailResponse, JobStatusResponse, BOMUploadResponse, QuoteUploadResponse, AnalysisStartResponse
from app.schemas.common import ResponseModel

router = APIRouter()


@router.post("/", response_model=ResponseModel[JobCreatedResponse], status_code=status.HTTP_201_CREATED)
async def create_job(job_in: JobCreate, user: dict = Depends(get_current_user), db = Depends(get_database)) -> dict:
    """Create a new job (Story 1.1)."""
    try:
        job_service = JobService(db)
        created_job = await job_service.create_job(user_id=user["username"], job_in=job_in)
        data = JobCreatedResponse(
            job_id=created_job.job_id, user_id=created_job.user_id,
            project_name=created_job.project_name, created_at=created_job.created_at, status=created_job.status
        )
        return {"success": True, "message": "Job created successfully", "data": data}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create job: {str(e)}")


@router.get("/", response_model=ResponseModel[List[JobListItem]])
async def list_jobs(user: dict = Depends(get_current_user), db = Depends(get_database), skip: int = 0, limit: int = 100, sort_by: str = "created_at") -> dict:
    """Get all jobs for authenticated user."""
    try:
        job_service = JobService(db)
        sort_order = -1 if sort_by == "created_at" else 1
        jobs = await job_service.get_jobs_by_user(user_id=user["username"], skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order)
        return {"success": True, "message": f"Retrieved {len(jobs)} jobs", "data": jobs}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve jobs: {str(e)}")


@router.get("/{job_id}", response_model=ResponseModel[JobDetailResponse])
async def get_job_detail(job_id: str, user: dict = Depends(get_current_user), db = Depends(get_database)) -> dict:
    """Get detailed information about a specific job."""
    try:
        job_service = JobService(db)
        job = await job_service.get_job_detail(job_id=job_id, user_id=user["username"])
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")
        return {"success": True, "message": "Job details retrieved successfully", "data": job}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve job: {str(e)}")


@router.get("/{job_id}/status", response_model=ResponseModel[JobStatusResponse])
async def get_job_status(job_id: str, user: dict = Depends(get_current_user), db = Depends(get_database)) -> dict:
    """Poll job execution status."""
    try:
        job_service = JobService(db)
        job = await job_service.get_job_by_id(job_id=job_id, user_id=user["username"])
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")
        data = JobStatusResponse(job_id=job.job_id, status=job.status)
        return {"success": True, "message": "Job status retrieved successfully", "data": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve status: {str(e)}")


@router.post("/{job_id}/upload-bom", response_model=ResponseModel[BOMUploadResponse], status_code=status.HTTP_201_CREATED)
async def upload_bom_files(job_id: str, files: List[UploadFile] = File(..., description="BOM files (.xlsm or .xlsx format)"), user: dict = Depends(get_current_user), db = Depends(get_database)) -> dict:
    """Upload multiple BOM files for a job."""
    try:
        job_service = JobService(db)
        result = await job_service.upload_bom_files(job_id=job_id, user_id=user["username"], files=files)
        return {
            "success": True,
            "message": f"Successfully uploaded {result['total_files']} BOM file(s)",
            "data": BOMUploadResponse(**result)
        }
    except (HTTPException, ValueError) as e:
        raise HTTPException(status_code=getattr(e, 'status_code', status.HTTP_400_BAD_REQUEST), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to upload BOM files: {str(e)}")


@router.post("/{job_id}/upload-quotes", response_model=ResponseModel[QuoteUploadResponse], status_code=status.HTTP_201_CREATED)
async def upload_quote_files(job_id: str, files: List[UploadFile] = File(..., description="Quote files (.pdf, .xlsx, .xlsm, .csv formats) - Max 30 files"), user: dict = Depends(get_current_user), db = Depends(get_database)) -> dict:
    """Upload multiple quote files for a job (Story 1.3)."""
    try:
        job_service = JobService(db)
        result = await job_service.upload_quote_files(job_id=job_id, user_id=user["username"], files=files)
        return {
            "success": True,
            "message": f"Successfully uploaded {result['total_files']} quote files",
            "data": QuoteUploadResponse(**result)
        }
    except (HTTPException, ValueError) as e:
        raise HTTPException(status_code=getattr(e, 'status_code', status.HTTP_400_BAD_REQUEST), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to upload quote files: {str(e)}")


@router.post("/{job_id}/analyze", response_model=ResponseModel[AnalysisStartResponse], status_code=status.HTTP_202_ACCEPTED)
async def start_analysis(job_id: str, user: dict = Depends(get_current_user), db = Depends(get_database)) -> dict:
    """Start analysis for a job """
    try:
        job_service = JobService(db)
        result = await job_service.start_analysis(job_id=job_id, user_id=user["username"])
        return {
            "success": True,
            "message": "Analysis started successfully. Usually takes 3-5 minutes for 10 quotes.",
            "data": AnalysisStartResponse(**result)
        }
    except (HTTPException, ValueError) as e:
        raise HTTPException(status_code=getattr(e, 'status_code', status.HTTP_400_BAD_REQUEST), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to start analysis: {str(e)}")
