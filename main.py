"""
JD Inbox - Main FastAPI Application
Career Intelligence MVP - Cloud-first build
"""
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from models import init_db, get_db
from routes import upload, rapid, tier, download, chat

# Initialize database on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    print("✓ Database initialized")
    yield
    # Shutdown
    print("✓ Shutting down")

app = FastAPI(
    title="JD Inbox",
    description="AI-powered job application triage and CV generation",
    version="1.0.0",
    lifespan=lifespan
)

# CORS - allow all origins for now (restrict later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (HTML frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include route modules
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(rapid.router, prefix="/api", tags=["rapid"])
app.include_router(tier.router, prefix="/api", tags=["tier"])
app.include_router(download.router, prefix="/api", tags=["download"])
app.include_router(chat.router, prefix="/api", tags=["chat"])

@app.get("/")
async def root():
    """Serve the main HTML interface"""
    return FileResponse("static/jd_inbox.html")

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/api/jobs")
async def list_jobs():
    """Get all jobs for the table"""
    db = get_db()
    jobs = db.execute("""
        SELECT id, filename, role, company, sector, mode, source,
               status, score, tier, brief, created_at, updated_at
        FROM jobs
        ORDER BY created_at DESC
    """).fetchall()
    
    return [dict(row) for row in jobs]

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
