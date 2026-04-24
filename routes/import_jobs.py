"""
Bulk import endpoint for Candeo v6 job scraper.
POST /api/jobs/import  {"jobs": [...], "run_date": "2026-04-24"}
Deduplicates by job_url or title|company combo.
"""
import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models import get_db

router = APIRouter()


# ── Schema ────────────────────────────────────────────────────────────────────

class CandeoJob(BaseModel):
    job_title:           str
    company:             str
    location:            Optional[str] = ""
    work_type:           Optional[str] = ""
    employment_type:     Optional[str] = ""
    posted_at:           Optional[str] = ""
    salary_estimate:     Optional[str] = ""
    salary_stated:       Optional[str] = ""
    job_url:             Optional[str] = ""
    description_full:    Optional[str] = ""
    quick_scan:          Optional[str] = ""
    description_summary: Optional[str] = ""
    fit_score:           Optional[str] = ""
    industry:            Optional[str] = ""
    search_label:        Optional[str] = ""
    source:              Optional[str] = "candeo"


class ImportRequest(BaseModel):
    jobs:     List[CandeoJob]
    run_date: Optional[str] = ""


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/jobs/import")
async def import_jobs(payload: ImportRequest):
    """
    Bulk-insert Candeo jobs.
    Returns counts of inserted / skipped (dupes) / errored.
    """
    if not payload.jobs:
        return {"success": True, "inserted": 0, "skipped": 0, "errors": 0, "total": 0}

    inserted = skipped = errors = 0

    with get_db() as db:
        # Load all existing source_ids in one query for fast dedup
        existing = db.execute(
            "SELECT source_id FROM jobs WHERE source_id IS NOT NULL"
        ).fetchall()
        seen_ids = {r["source_id"] for r in existing}

        for job in payload.jobs:
            # Dedup key: prefer job_url, fall back to title|company
            source_id = (job.job_url or "").strip() or \
                        f"{job.job_title.lower().strip()}|{job.company.lower().strip()}"

            if source_id in seen_ids:
                skipped += 1
                continue

            try:
                db.insert(
                    """INSERT INTO jobs
                    (filename, role, company, sector, mode, source, source_id,
                     jd_text, status, brief, location, employment_type,
                     posted_at, salary_estimate, job_url, search_label, candeo_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        f"{job.company} — {job.job_title}",
                        job.job_title,
                        job.company,
                        job.industry or "",
                        job.work_type or "",
                        "candeo",
                        source_id,
                        job.description_full or "",
                        "pending",
                        job.quick_scan or job.description_summary or "",
                        job.location or "",
                        job.employment_type or "",
                        job.posted_at or "",
                        job.salary_estimate or job.salary_stated or "",
                        job.job_url or "",
                        job.search_label or "",
                        json.dumps({
                            "fit_score":           job.fit_score,
                            "description_summary": job.description_summary,
                            "run_date":            payload.run_date,
                        }),
                    ),
                )
                seen_ids.add(source_id)
                inserted += 1
            except Exception as e:
                errors += 1
                print(f"Import error for {job.job_title} @ {job.company}: {e}")

    return {
        "success":  True,
        "inserted": inserted,
        "skipped":  skipped,
        "errors":   errors,
        "total":    len(payload.jobs),
    }


@router.get("/jobs/import/status")
async def import_status():
    """Quick summary of jobs by source."""
    with get_db() as db:
        rows = db.execute(
            "SELECT source, COUNT(*) as count FROM jobs GROUP BY source"
        ).fetchall()
    return {"counts": rows}
