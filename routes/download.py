"""
CV download endpoint
TODO: Implement in Session 4
"""
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/download/{job_id}")
async def download_cv(job_id: int):
    """Download generated CV - TODO Session 4"""
    raise HTTPException(status_code=501, detail="Download - coming in Session 4")
