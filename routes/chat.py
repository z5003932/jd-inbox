"""
Chat refinement endpoint
TODO: Implement in Session 5
"""
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.post("/chat/{job_id}")
async def chat_message(job_id: int, message: dict):
    """Chat refinement - TODO Session 5"""
    raise HTTPException(status_code=501, detail="Chat - coming in Session 5")
