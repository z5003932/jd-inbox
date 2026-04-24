#!/usr/bin/env python3
"""
import_stories.py — Import master_layer2_merged.csv into JD Inbox stories table.

Usage:
    # Import to local dev server
    python import_stories.py

    # Import to Railway (production)
    python import_stories.py --url https://jd-inbox-production.up.railway.app

    # Full refresh (delete all first)
    python import_stories.py --replace

    # Specify CSV path
    python import_stories.py --csv /path/to/master_layer2_merged.csv
"""

import csv
import json
import argparse
import requests
from pathlib import Path

DEFAULT_CSV = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Career" / "CANDEO" / "master_layer2_merged.csv"
DEFAULT_URL = "http://localhost:8000"
BATCH_SIZE  = 200


def load_csv(path: Path):
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    print(f"Loaded {len(rows)} stories from {path}")
    return rows


def map_row(row: dict) -> dict:
    return {
        "story_id":             row.get("story_id", "").strip(),
        "source_file":          row.get("Source_File", "").strip(),
        "company":              row.get("Company", "").strip(),
        "initiative":           row.get("Initiative", "").strip(),
        "sub_initiative":       row.get("Sub_Initiative", "").strip(),
        "component":            row.get("Component", "").strip(),
        "component_summary":    row.get("Component_Summary", "").strip(),
        "pointer_summary":      row.get("Pointer_Summary", "").strip(),
        "work_behind":          row.get("Work_Behind_The_Work", "").strip(),
        "outcomes":             row.get("Outcomes", "").strip(),
        "year":                 row.get("Year", "").strip(),
        "story_type":           row.get("story_type", "").strip(),
        "parent_story_id":      row.get("parent_story_id", "").strip(),
        "themes":               row.get("themes", "").strip(),
        "skills_demonstrated":  row.get("skills_demonstrated", "").strip(),
        "context_type":         row.get("context_type", "").strip(),
        "stakeholder_level":    row.get("stakeholder_level", "").strip(),
        "outcome_type":         row.get("outcome_type", "").strip(),
        "interview_answer_type": row.get("interview_answer_type", "").strip(),
        "star_story_ready":     row.get("star_story_ready", "").strip(),
        "role_relevance":       row.get("role_relevance", "").strip(),
    }


def import_batch(url: str, stories: list, replace: bool, batch_num: int):
    payload = {"stories": stories, "replace": replace}
    resp = requests.post(
        f"{url.rstrip('/')}/api/stories/import",
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    result = resp.json()
    print(f"  Batch {batch_num}: inserted={result['inserted']} skipped={result['skipped']} errors={result['errors']}")
    return result


def main():
    parser = argparse.ArgumentParser(description="Import stories CSV to JD Inbox")
    parser.add_argument("--csv",     default=str(DEFAULT_CSV), help="Path to master_layer2_merged.csv")
    parser.add_argument("--url",     default=DEFAULT_URL,      help="JD Inbox base URL")
    parser.add_argument("--replace", action="store_true",      help="Delete all stories first (full refresh)")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        raise SystemExit(1)

    rows    = load_csv(csv_path)
    stories = [map_row(r) for r in rows if r.get("story_id", "").strip()]
    print(f"Mapped {len(stories)} valid stories")

    total_inserted = total_skipped = total_errors = 0
    first_batch    = True

    for i in range(0, len(stories), BATCH_SIZE):
        batch      = stories[i:i + BATCH_SIZE]
        # Only send replace=True on first batch to avoid deleting mid-import
        do_replace = args.replace and first_batch
        result     = import_batch(args.url, batch, do_replace, i // BATCH_SIZE + 1)
        total_inserted += result["inserted"]
        total_skipped  += result["skipped"]
        total_errors   += result["errors"]
        first_batch     = False

    print(f"\nDone — inserted: {total_inserted}, skipped: {total_skipped}, errors: {total_errors}")


if __name__ == "__main__":
    main()
