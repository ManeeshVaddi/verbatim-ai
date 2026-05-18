"""
Ingests political speech transcripts from English Wikisource via the
MediaWiki API. Wikisource is designed for programmatic access and returns
clean plain text — no scraping required.

API endpoint: https://en.wikisource.org/w/api.php
Action: query + extracts (gives plain text, not wikitext)

Usage:
    python -m backend.scripts.ingest_wikisource [--limit N]
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
load_dotenv()

from backend.db.database import SessionLocal, engine
from backend.db.models import Base, Chunk, Transcript

CHUNK_WORDS = 200
OVERLAP_WORDS = 50
API = "https://en.wikisource.org/w/api.php"

# (wikisource_page_title, display_title, speaker, date)
PAGES = [
    # Civil rights
    ("I Have a Dream", "MLK 'I Have a Dream' Speech", "Martin Luther King Jr.", "1963-08-28"),
    ("Letter from Birmingham Jail", "MLK Letter from Birmingham Jail", "Martin Luther King Jr.", "1963-04-16"),
    ("I've Been to the Mountaintop", "MLK 'I've Been to the Mountaintop'", "Martin Luther King Jr.", "1968-04-03"),
    ("The Ballot or the Bullet", "Malcolm X 'The Ballot or the Bullet'", "Malcolm X", "1964-04-03"),
    ("Eulogy for the Martyred Children", "MLK Eulogy for the Martyred Children", "Martin Luther King Jr.", "1963-09-18"),
    # Presidents — Foundational
    ("Gettysburg Address", "Lincoln Gettysburg Address", "Abraham Lincoln", "1863-11-19"),
    ("Second Inaugural Address (Lincoln)", "Lincoln Second Inaugural Address", "Abraham Lincoln", "1865-03-04"),
    ("First Inaugural Address (Franklin D. Roosevelt)", "FDR First Inaugural Address", "Franklin D. Roosevelt", "1933-03-04"),
    ("Infamy Speech", "FDR Pearl Harbor Address", "Franklin D. Roosevelt", "1941-12-08"),
    ("Four Freedoms", "FDR Four Freedoms Speech", "Franklin D. Roosevelt", "1941-01-06"),
    ("Inaugural Address (Kennedy)", "JFK Inaugural Address", "John F. Kennedy", "1961-01-20"),
    ("Address to the Nation on the Soviet Arms Buildup in Cuba", "JFK Cuban Missile Crisis Address", "John F. Kennedy", "1962-10-22"),
    ("Ich bin ein Berliner", "JFK 'Ich Bin Ein Berliner' Berlin Speech", "John F. Kennedy", "1963-06-26"),
    ("Address to a Joint Session of Congress on Civil Rights", "LBJ 'We Shall Overcome' Address", "Lyndon B. Johnson", "1965-03-15"),
    ("Farewell Address (Eisenhower)", "Eisenhower Farewell — Military-Industrial Complex", "Dwight D. Eisenhower", "1961-01-17"),
    ("First Inaugural Address (Richard Nixon)", "Nixon First Inaugural Address", "Richard Nixon", "1969-01-20"),
    ("Address to the Nation Announcing His Resignation (Nixon)", "Nixon Resignation Address", "Richard Nixon", "1974-08-08"),
    ("First Inaugural Address (Ronald Reagan)", "Reagan First Inaugural Address", "Ronald Reagan", "1981-01-20"),
    ("Address to the Nation on the Challenger Disaster", "Reagan Challenger Disaster Address", "Ronald Reagan", "1986-01-28"),
    ("Remarks at the Brandenburg Gate", "Reagan 'Tear Down This Wall' Speech", "Ronald Reagan", "1987-06-12"),
    ("Farewell Address (Reagan)", "Reagan Farewell Address", "Ronald Reagan", "1989-01-11"),
    ("Inaugural Address (Bill Clinton)", "Clinton First Inaugural Address", "Bill Clinton", "1993-01-20"),
    ("First Inaugural Address (George W. Bush)", "George W. Bush First Inaugural Address", "George W. Bush", "2001-01-20"),
    ("Address to a Joint Session of Congress Following 9/11 Attacks", "George W. Bush Address After 9/11", "George W. Bush", "2001-09-20"),
    ("Inaugural Address (Barack Obama)", "Obama First Inaugural Address", "Barack Obama", "2009-01-20"),
    ("Second Inaugural Address (Barack Obama)", "Obama Second Inaugural Address", "Barack Obama", "2013-01-21"),
    # Congressional and political
    ("Barbara Jordan's Opening Statement at the Nixon Impeachment Hearing", "Barbara Jordan Nixon Impeachment Statement", "Barbara Jordan", "1974-07-25"),
    ("A More Perfect Union", "Obama 'A More Perfect Union' Speech", "Barack Obama", "2008-03-18"),
    ("2004 Democratic National Convention keynote address", "Obama DNC Keynote 2004", "Barack Obama", "2004-07-27"),
    ("Address to the Nation on the War in Vietnam (Nixon 1969)", "Nixon Silent Majority Speech", "Richard Nixon", "1969-11-03"),
    # Women's rights and social
    ("'Ain't I a Woman?' (Truth)", "Sojourner Truth 'Ain't I a Woman?'", "Sojourner Truth", "1851-05-29"),
    ("Address to the First Woman's Rights Convention", "Elizabeth Cady Stanton First Women's Rights Convention", "Elizabeth Cady Stanton", "1848-07-19"),
    # Senate / Congress
    ("First Inaugural Address (Jimmy Carter)", "Carter First Inaugural Address", "Jimmy Carter", "1977-01-20"),
    ("Crisis of Confidence", "Carter 'Crisis of Confidence' Speech", "Jimmy Carter", "1979-07-15"),
    ("Checkers speech", "Nixon Checkers Speech", "Richard Nixon", "1952-09-23"),
    ("Address to the Nation on Watergate", "Nixon Watergate Address", "Richard Nixon", "1973-08-15"),
]


def _fetch_extract(page_title: str) -> str:
    """Fetch plain-text extract via MediaWiki API."""
    params = {
        "action": "query",
        "titles": page_title,
        "prop": "extracts",
        "explaintext": "1",
        "exsectionformat": "plain",
        "format": "json",
        "redirects": "1",
    }
    qs = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
    url = f"{API}?{qs}"

    result = subprocess.run(
        ["curl", "-s", "-L",
         "-A", "VerbatimAI/1.0 (educational; contact maneeshvaddi@gmail.com)",
         "-H", "Accept: application/json",
         url],
        capture_output=True, timeout=20,
    )
    raw = result.stdout.decode("utf-8", errors="replace")

    try:
        data = json.loads(raw)
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            if "missing" in page:
                return ""
            extract = page.get("extract", "")
            # Remove section headings (== Heading ==) and references
            extract = re.sub(r"==+[^=]+==+", "", extract)
            extract = re.sub(r"\[\d+\]", "", extract)
            return " ".join(extract.split())
    except json.JSONDecodeError:
        return ""

    return ""


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


def ingest(limit: int = len(PAGES)) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    ingested = 0

    try:
        for i, (wiki_title, display_title, speaker, date) in enumerate(PAGES[:limit]):
            if i > 0:
                time.sleep(0.3)
            print(f"  [{i+1}/{min(limit, len(PAGES))}] {display_title}...")

            text = _fetch_extract(wiki_title)
            if len(text.split()) < 80:
                print(f"    Skipped — {len(text.split())} words (page missing or too short)")
                continue

            source_url = f"https://en.wikisource.org/wiki/{quote(wiki_title.replace(' ', '_'))}"
            if db.query(Transcript).filter(Transcript.source_url == source_url).first():
                print(f"    Already in DB")
                continue

            transcript = Transcript(
                title=display_title,
                source="wikisource.org",
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
            ingested += 1
            print(f"    OK — {len(text.split())} words, {added_chunks} chunks")

    finally:
        db.close()

    print(f"\nDone. {ingested}/{min(limit, len(PAGES))} Wikisource transcripts ingested.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=len(PAGES))
    args = parser.parse_args()
    ingest(args.limit)
