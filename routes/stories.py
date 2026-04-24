"""
Stories — career evidence base browser.
GET  /api/stories          list + filter
GET  /api/stories/:id      single story
POST /api/stories/import   bulk import from CSV payload
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from models import get_db

router = APIRouter()


# ── Schema ────────────────────────────────────────────────────────────────────

class StoryImport(BaseModel):
    story_id:             str
    source_file:          Optional[str] = ""
    company:              Optional[str] = ""
    initiative:           Optional[str] = ""
    sub_initiative:       Optional[str] = ""
    component:            Optional[str] = ""
    component_summary:    Optional[str] = ""
    pointer_summary:      Optional[str] = ""
    work_behind:          Optional[str] = ""
    outcomes:             Optional[str] = ""
    year:                 Optional[str] = ""
    story_type:           Optional[str] = ""
    parent_story_id:      Optional[str] = ""
    themes:               Optional[str] = ""
    skills_demonstrated:  Optional[str] = ""
    context_type:         Optional[str] = ""
    stakeholder_level:    Optional[str] = ""
    outcome_type:         Optional[str] = ""
    interview_answer_type: Optional[str] = ""
    star_story_ready:     Optional[str] = ""
    role_relevance:       Optional[str] = ""


class StoriesImportRequest(BaseModel):
    stories: List[StoryImport]
    replace: bool = False  # if True, DELETE all first


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/stories")
async def list_stories(
    company:  Optional[str] = Query(None),
    q:        Optional[str] = Query(None),
    type:     Optional[str] = Query(None),
    limit:    int = Query(200, le=500),
    offset:   int = Query(0),
):
    """Browse stories with optional company filter and full-text search."""
    with get_db() as db:
        conditions = []
        params     = []

        if company:
            conditions.append("company = ?")
            params.append(company)
        if type:
            conditions.append("story_type = ?")
            params.append(type)
        if q:
            conditions.append(
                "(component_summary LIKE ? OR pointer_summary LIKE ? "
                "OR themes LIKE ? OR skills_demonstrated LIKE ? OR outcomes LIKE ?)"
            )
            like = f"%{q}%"
            params.extend([like, like, like, like, like])

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # total count
        total = db.execute(
            f"SELECT COUNT(*) as n FROM stories {where}", tuple(params)
        ).fetchone()["n"]

        rows = db.execute(
            f"""SELECT story_id, company, initiative, component_summary,
                       pointer_summary, outcomes, year, story_type,
                       parent_story_id, themes, skills_demonstrated, role_relevance
                FROM stories {where}
                ORDER BY company, story_id
                LIMIT ? OFFSET ?""",
            tuple(params) + (limit, offset),
        ).fetchall()

        # Companies list for filter dropdown
        companies = db.execute(
            "SELECT DISTINCT company FROM stories ORDER BY company"
        ).fetchall()

    return {
        "total":     total,
        "offset":    offset,
        "limit":     limit,
        "stories":   rows,
        "companies": [r["company"] for r in companies],
    }


@router.get("/stories/{story_id}")
async def get_story(story_id: str):
    """Get a single story by ID."""
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM stories WHERE story_id = ?", (story_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Story not found")
    return row


@router.post("/stories/import")
async def import_stories(payload: StoriesImportRequest):
    """
    Bulk import stories from CSV.
    replace=true deletes all existing stories first (full refresh).
    """
    inserted = skipped = errors = 0

    with get_db() as db:
        if payload.replace:
            db.execute("DELETE FROM stories")

        # existing IDs for dedup
        existing = {r["story_id"] for r in db.execute(
            "SELECT story_id FROM stories"
        ).fetchall()}

        for s in payload.stories:
            if s.story_id in existing and not payload.replace:
                skipped += 1
                continue
            try:
                db.execute(
                    """INSERT INTO stories
                    (story_id, source_file, company, initiative, sub_initiative,
                     component, component_summary, pointer_summary, work_behind,
                     outcomes, year, story_type, parent_story_id, themes,
                     skills_demonstrated, context_type, stakeholder_level,
                     outcome_type, interview_answer_type, star_story_ready,
                     role_relevance)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(story_id) DO UPDATE SET
                      component_summary=excluded.component_summary,
                      pointer_summary=excluded.pointer_summary,
                      outcomes=excluded.outcomes,
                      themes=excluded.themes,
                      skills_demonstrated=excluded.skills_demonstrated,
                      role_relevance=excluded.role_relevance""",
                    (
                        s.story_id, s.source_file, s.company, s.initiative,
                        s.sub_initiative, s.component, s.component_summary,
                        s.pointer_summary, s.work_behind, s.outcomes, s.year,
                        s.story_type, s.parent_story_id, s.themes,
                        s.skills_demonstrated, s.context_type,
                        s.stakeholder_level, s.outcome_type,
                        s.interview_answer_type, s.star_story_ready,
                        s.role_relevance,
                    ),
                )
                inserted += 1
            except Exception as e:
                errors += 1
                print(f"Story import error [{s.story_id}]: {e}")

    return {"success": True, "inserted": inserted, "skipped": skipped, "errors": errors}


@router.get("/stories-meta")
async def stories_meta():
    """Summary stats for the stories browser header."""
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) as n FROM stories").fetchone()["n"]
        by_company = db.execute(
            "SELECT company, COUNT(*) as n FROM stories GROUP BY company ORDER BY company"
        ).fetchall()
    return {"total": total, "by_company": by_company}
