"""
Rapid execution endpoint
TODO: Implement in Session 2
"""
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.post("/rapid/{job_id}")
async def run_rapid(job_id: int):
    """Run JD Rapid on a job - TODO Session 2"""
    raise HTTPException(status_code=501, detail="Rapid endpoint - coming in Session 2")
