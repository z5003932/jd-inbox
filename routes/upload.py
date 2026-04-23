"""
File upload and JD extraction endpoint
Handles PDF, images, Word docs
"""
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from models import create_job, update_job
from services.extraction import extract_jd_content

router = APIRouter()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Allowed file types
ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.docx', '.doc'}

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload JD file (PDF, image, Word doc)
    - Saves file to disk
    - Extracts JD content via Claude API
    - Creates database record
    - Returns job object for frontend
    """
    
    # Validate file type
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Generate unique filename
    unique_id = str(uuid.uuid4())[:8]
    safe_filename = f"{unique_id}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename
    
    # Save file
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Extract JD content via Claude API
    try:
        extraction_result = await extract_jd_content(str(file_path), file_ext)
    except Exception as e:
        # Clean up file on extraction failure
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"JD extraction failed: {str(e)}")
    
    # Create database record
    job_data = {
        "filename": file.filename,
        "jd_file_path": str(file_path),
        "source": "upload",
        "status": "pending",  # Will auto-Rapid after creation
        **extraction_result  # role, company, sector, mode, jd_text
    }
    
    try:
        job_id = create_job(job_data)
    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    # Return job object
    from models import get_job
    job = get_job(job_id)
    
    return JSONResponse(content={
        "success": True,
        "job_id": job_id,
        "job": dict(job),
        "message": f"Uploaded {file.filename}. Extracting content..."
    })

@router.get("/upload/status/{job_id}")
async def get_upload_status(job_id: int):
    """Check extraction status for a job"""
    from models import get_job
    job = get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job_id,
        "status": job['status'],
        "has_jd_text": bool(job.get('jd_text')),
        "role": job.get('role'),
        "company": job.get('company')
    }
