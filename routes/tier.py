"""
Tier execution endpoints (A/B/C/D)
TODO: Implement in Session 3
"""
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.post("/tier/a/{job_id}")
async def tier_a(job_id: int):
    """Tier A - Upload as-is - TODO Session 3"""
    raise HTTPException(status_code=501, detail="Tier A - coming in Session 3")

@router.post("/tier/b/{job_id}")
async def tier_b(job_id: int):
    """Tier B - Fast CV - TODO Session 3"""
    raise HTTPException(status_code=501, detail="Tier B - coming in Session 3")

@router.post("/tier/c/{job_id}")
async def tier_c(job_id: int):
    """Tier C - Targeted tweak - TODO Session 3"""
    raise HTTPException(status_code=501, detail="Tier C - coming in Session 3")

@router.post("/tier/d/{job_id}")
async def tier_d(job_id: int):
    """Tier D - Full engine - TODO Session 3"""
    raise HTTPException(status_code=501, detail="Tier D - coming in Session 3")
