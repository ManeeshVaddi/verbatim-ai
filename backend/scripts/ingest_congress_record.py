"""
Ingests floor speeches from the Congressional Record via the GovInfo API
(api.govinfo.gov). Covers House and Senate floor speeches from C-SPAN,
C-SPAN2, and C-SPAN3 broadcast sessions.

The Congressional Record is a public domain government publication.
GovInfo is operated by the Government Publishing Office.

Usage:
    GOVINFO_API_KEY=<key> python -m backend.scripts.ingest_congress_record [--limit N]
    or set CONGRESS_API_KEY in .env
"""

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
load_dotenv()

from backend.db.database import SessionLocal, engine
from backend.db.models import Base, Chunk, Transcript

CHUNK_WORDS = 200
OVERLAP_WORDS = 50
API_KEY = os.getenv("CONGRESS_API_KEY", "5j6oEh3jAJnKMmwba6DKm2CXsd8tXKqMgUmuDJu8")
GOVINFO_BASE = "https://api.govinfo.gov"

MIN_WORDS = 250  # skip procedural one-liners

# Key sessions to pull — high-interest dates where famous speeches were given
# Format: (package_id, description, chamber)
KEY_SESSIONS = [
    # Presidential responses / State of the Union debates
    ("CREC-2024-03-07", "State of the Union Response Speeches 2024", "SENATE"),
    ("CREC-2024-03-07", "State of the Union Response Speeches 2024", "HOUSE"),
    ("CREC-2022-03-02", "State of the Union Response Speeches 2022", "SENATE"),
    # Inflation Reduction Act
    ("CREC-2022-08-06", "Inflation Reduction Act Floor Debate", "SENATE"),
    ("CREC-2022-08-12", "Inflation Reduction Act House Passage", "HOUSE"),
    # January 6th aftermath
    ("CREC-2021-01-07", "Congressional Response to January 6th Attack", "SENATE"),
    ("CREC-2021-01-07", "Congressional Response to January 6th Attack", "HOUSE"),
    # Trump Second Impeachment
    ("CREC-2021-01-13", "Trump Second Impeachment Debate", "HOUSE"),
    # COVID Relief
    ("CREC-2021-03-06", "American Rescue Plan Senate Debate", "SENATE"),
    # ACA / Obamacare repeal vote
    ("CREC-2017-07-28", "ACA Repeal Vote — McCain Thumbs Down", "SENATE"),
    ("CREC-2017-07-25", "ACA Repeal Debate — McCain Return Speech", "SENATE"),
    # George Floyd / racial justice
    ("CREC-2020-06-08", "George Floyd Memorial and Police Reform Debate", "SENATE"),
    ("CREC-2020-06-08", "George Floyd Memorial and Police Reform Debate", "HOUSE"),
    # Trump First Impeachment acquittal
    ("CREC-2020-02-05", "Trump First Impeachment Acquittal Speeches", "SENATE"),
    # Kavanaugh confirmation
    ("CREC-2018-10-05", "Kavanaugh Confirmation Vote Floor Speeches", "SENATE"),
    # Gun control / Parkland
    ("CREC-2018-02-14", "Gun Violence Floor Speeches After Parkland", "SENATE"),
    ("CREC-2018-02-14", "Gun Violence Floor Speeches After Parkland", "HOUSE"),
    # Tax Cuts and Jobs Act 2017
    ("CREC-2017-12-01", "Tax Cuts and Jobs Act Senate Debate", "SENATE"),
    # Sanders 2016 campaign issues
    ("CREC-2016-03-08", "Income Inequality Floor Speeches", "SENATE"),
    # Obama farewell / transition
    ("CREC-2017-01-12", "Senators React to Obama Farewell Address", "SENATE"),
    # Black Lives Matter 2020
    ("CREC-2020-06-11", "Justice in Policing Act Debate", "HOUSE"),
    # Debt ceiling 2023
    ("CREC-2023-06-01", "Debt Ceiling Crisis Floor Speeches", "SENATE"),
    # Ukraine aid
    ("CREC-2024-04-23", "Ukraine Aid Package Senate Debate", "SENATE"),
]


def _curl_json(url: str) -> dict:
    r = subprocess.run(
        ["curl", "-s", "-L",
         "-A", "VerbatimAI/1.0 (educational project)",
         "-H", "Accept: application/json",
         url],
        capture_output=True, timeout=20,
    )
    import json
    try:
        return json.loads(r.stdout.decode("utf-8", errors="replace"))
    except Exception:
        return {}


def _curl_html(url: str) -> str:
    r = subprocess.run(
        ["curl", "-s", "-L",
         "-A", "VerbatimAI/1.0 (educational project)",
         url],
        capture_output=True, timeout=20,
    )
    return r.stdout.decode("utf-8", errors="replace")


def get_granules(package_id: str, chamber: str) -> list[dict]:
    """Fetch all granules for a package, filtered by chamber."""
    all_granules = []
    offset = 0
    page_size = 100

    while True:
        url = f"{GOVINFO_BASE}/packages/{package_id}/granules?offset={offset}&pageSize={page_size}&api_key={API_KEY}"
        data = _curl_json(url)
        granules = data.get("granules", [])
        if not granules:
            break
        all_granules.extend(g for g in granules if g.get("granuleClass") == chamber)
        if len(granules) < page_size:
            break
        offset += page_size
        time.sleep(0.2)

    return all_granules


def extract_text(package_id: str, granule_id: str) -> str:
    from bs4 import BeautifulSoup
    url = f"{GOVINFO_BASE}/packages/{package_id}/granules/{granule_id}/htm?api_key={API_KEY}"
    html = _curl_html(url)
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return " ".join(soup.get_text(" ", strip=True).split())


def extract_speaker(text: str) -> str | None:
    """
    Congressional Record attributes speeches as 'Mr./Mrs./Ms. LASTNAME.'
    Extract the first speaker found.
    """
    # Pattern: Mr./Mrs./Ms./Miss LASTNAME (all caps)
    m = re.search(r'\b(Mr\.|Mrs\.|Ms\.|Miss|Senator|Representative)\s+([A-Z][A-Z\-\']+)\.', text)
    if m:
        title = m.group(1)
        name = m.group(2).title()
        return f"{title} {name}"
    return None


def chunk_text(text: str) -> list[tuple[str, int]]:
    words = text.split()
    chunks = []
    step = CHUNK_WORDS - OVERLAP_WORDS
    char_offset = 0
    for start in range(0, len(words), step):
        window = words[start: start + CHUNK_WORDS]
        if not window:
            break
        chunk_str = " ".join(window)
        idx = text.find(words[start], char_offset)
        if idx == -1:
            idx = char_offset
        chunks.append((chunk_str, idx))
        char_offset = idx + len(chunk_str)
    return chunks


def ingest(limit: int = len(KEY_SESSIONS)) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    total_ingested = 0

    try:
        seen_packages = {}  # cache granule lists

        for i, (package_id, description, chamber) in enumerate(KEY_SESSIONS[:limit]):
            print(f"\n[{i+1}/{min(limit, len(KEY_SESSIONS))}] {package_id} — {description} ({chamber})")

            cache_key = f"{package_id}:{chamber}"
            if cache_key not in seen_packages:
                granules = get_granules(package_id, chamber)
                seen_packages[cache_key] = granules
                print(f"  Found {len(granules)} {chamber} granules")
            else:
                granules = seen_packages[cache_key]

            session_ingested = 0
            for g in granules:
                granule_id = g["granuleId"]
                title = g.get("title", granule_id)

                # Skip procedural, legislative boilerplate, and tribute entries
                skip_keywords = [
                    "PRAYER", "PLEDGE", "QUORUM", "JOURNAL", "RECESS", "ADJOURNMENT",
                    "COMMUNICATION", "FRONT MATTER", "ENROLLED BILL", "NOMINATION",
                    "TEXT OF AMENDMENT", "TEXT OF SENATE AMENDMENT", "TEXT OF HOUSE AMENDMENT",
                    "AMENDMENTS SUBMITTED", "ADDITIONAL COSPONSOR", "ADDITIONAL SPONSOR",
                    "INTRODUCTION OF BILLS", "PUBLIC BILLS AND RESOLUTIONS",
                    "REPORTS OF COMMITTEES", "EXECUTIVE REPORTS", "PETITIONS AND MEMORIALS",
                    "AUTHORITY FOR COMMITTEES", "CONFIRMATIONS", "APPOINTMENTS",
                    "SUBMISSION OF CONCURRENT", "SENATE RESOLUTION", "HOUSE RESOLUTION",
                    "SENATE CONCURRENT", "HOUSE CONCURRENT",
                    "HONORING", "RECOGNIZING", "CONGRATULATING", "WELCOMING", "TRIBUTE TO",
                    "CELEBRATING", "REMEMBERING", "IN MEMORY", "IN HONOR",
                    "DESIGNATION OF SPEAKER", "MORNING-HOUR", "PRESIDENTIAL MESSAGE",
                    "ORDER OF BUSINESS", "ORDERS FOR",
                ]
                if any(k in title.upper() for k in skip_keywords):
                    continue

                source_url = f"https://www.govinfo.gov/app/details/{package_id}/{granule_id}"
                if db.query(Transcript).filter(Transcript.source_url == source_url).first():
                    continue

                time.sleep(0.15)
                text = extract_text(package_id, granule_id)
                if len(text.split()) < MIN_WORDS:
                    continue

                speaker = extract_speaker(text) or "Congress Member"
                date = package_id.replace("CREC-", "")  # YYYY-MM-DD

                transcript = Transcript(
                    title=f"[{chamber}] {title}",
                    source=f"Congressional Record ({chamber})",
                    source_url=source_url,
                    speaker=speaker,
                    full_text=text,
                    date=date,
                )
                db.add(transcript)
                db.flush()

                added_chunks = 0
                for j, (chunk_str, start_char) in enumerate(chunk_text(text)):
                    if len(chunk_str.split()) < 20:
                        continue
                    db.add(Chunk(
                        transcript_id=transcript.id,
                        chunk_index=j,
                        text=chunk_str,
                        start_char=start_char,
                    ))
                    added_chunks += 1

                db.commit()
                total_ingested += 1
                session_ingested += 1
                print(f"    + [{speaker}] {title[:60]} — {len(text.split())} words, {added_chunks} chunks")

            if session_ingested == 0:
                print(f"  (no new speeches above {MIN_WORDS} words)")

    finally:
        db.close()

    print(f"\nDone. {total_ingested} Congressional Record speeches ingested.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=len(KEY_SESSIONS))
    args = parser.parse_args()
    ingest(args.limit)
