"""
JD Rapid — Gemini 2.0 Flash triage
~$0.001/run vs ~$0.007 with Haiku
"""
import os
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
import google.generativeai as genai

from models import get_job, update_job

router    = APIRouter()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

# ── Career profile ────────────────────────────────────────────────────────────

def load_career_profile() -> str:
    """
    Load career context for fit scoring.
    Priority: data/career_profile.md → CAREER_PROFILE env var → placeholder.
    Add your career summary to data/career_profile.md or set the env var on Railway.
    """
    p = Path("data/career_profile.md")
    if p.exists():
        return p.read_text().strip()
    env = os.environ.get("CAREER_PROFILE", "").strip()
    if env:
        return env
    return (
        "Senior product and transformation professional with 10+ years across "
        "digital transformation, AI strategy, product management, and enterprise "
        "technology. Strong background in government, fintech, healthtech, and "
        "SaaS scale-ups. Experienced leading cross-functional teams, driving "
        "0-to-1 product launches, and bridging technical and business stakeholders."
    )

# ── Prompt ────────────────────────────────────────────────────────────────────

RAPID_PROMPT = """\
You are a career coach doing a rapid triage of a job description.

CANDIDATE PROFILE:
{career_profile}

JOB DESCRIPTION:
{jd_text}

Analyse this role for fit and return ONLY valid JSON — no markdown, no explanation.

{{
  "score": <integer 1-10 overall fit>,
  "tier": <"A" | "B" | "C" | "D" | "SKIP">,
  "archetype": <short role type, e.g. "AI Transformation Lead" or "Senior PM – FinTech">,
  "brief": <one sentence: role + company type + location + salary hint if visible>,
  "why": <2-3 sentences explaining the score, referencing specific candidate background>,
  "green_flags": [<2-4 specific positives>],
  "red_flags": [<0-3 specific concerns or gaps, empty array if none>]
}}

Tier guide:
A = Upload generic CV as-is (low fit or low priority role)
B = Fast CV tweak — tagline + summary only, ~5 min
C = Targeted tweak — Fast CV + rewrite 1-2 role bullet sets, ~20 min
D = Full engine run — high fit, worth doing properly
SKIP = Not worth applying
"""

# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/rapid/{job_id}")
async def run_rapid(job_id: int):
    """Run JD Rapid triage using Gemini 2.0 Flash."""
    if not GEMINI_KEY:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY not set — add it as a Railway environment variable"
        )

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    jd_text = (job.get("jd_text") or "").strip()
    if not jd_text:
        raise HTTPException(
            status_code=400,
            detail="No JD text — file extraction may still be in progress"
        )

    try:
        model = genai.GenerativeModel(
            "gemini-2.0-flash",
            generation_config={"response_mime_type": "application/json"},
        )

        prompt = RAPID_PROMPT.format(
            career_profile=load_career_profile(),
            jd_text=jd_text[:8000],
        )

        response = model.generate_content(prompt)
        result   = json.loads(response.text)

        # Validate required fields
        for field in ("score", "tier", "archetype", "brief", "why", "green_flags", "red_flags"):
            if field not in result:
                raise ValueError(f"Gemini response missing field: {field}")

        # Persist to DB
        update_job(job_id, {
            "status":       "rapid",
            "score":        int(result["score"]),
            "tier":         result["tier"],
            "archetype":    result["archetype"],
            "brief":        result["brief"],
            "why":          result["why"],
            "green_flags":  json.dumps(result["green_flags"]),
            "red_flags":    json.dumps(result["red_flags"]),
            "rapid_output": json.dumps(result),
        })

        return {"success": True, "job_id": job_id, **result}

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Gemini returned invalid JSON: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rapid failed: {str(e)}")
