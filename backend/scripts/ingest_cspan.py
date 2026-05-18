"""
Ingests transcripts from C-SPAN's public video library (c-span.org).

C-SPAN covers congressional floor speeches, hearings, presidential addresses,
and political events across C-SPAN, C-SPAN2, and C-SPAN3.

Tries two strategies per video:
  1. WebVTT caption file at /video/transcript/?id=[id]&transcriptType=cc
  2. JSON-LD / transcript div on the main video page

Usage:
    python -m backend.scripts.ingest_cspan [--limit N]
"""

import argparse
import json
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
BASE_URL = "https://www.c-span.org"

# (video_id, title, speaker, date, channel)
VIDEOS = [
    # C-SPAN — Presidential addresses
    ("4724753", "Trump Address to Joint Session of Congress 2025", "Donald Trump", "2025-03-04", "C-SPAN"),
    ("4682673", "Biden State of the Union 2024", "Joe Biden", "2024-03-07", "C-SPAN"),
    ("5154045", "Biden Farewell Address 2025", "Joe Biden", "2025-01-15", "C-SPAN"),
    ("4603966", "Biden Victory Speech 2020", "Joe Biden", "2020-11-07", "C-SPAN"),
    ("523596",  "Obama Victory Speech 2008", "Barack Obama", "2008-11-04", "C-SPAN"),
    ("282218",  "George W. Bush Address to Congress After 9/11", "George W. Bush", "2001-09-20", "C-SPAN"),
    ("11034",   "Clinton First Inaugural Address 1993", "Bill Clinton", "1993-01-20", "C-SPAN"),
    ("6948",    "Reagan First Inaugural Address 1981", "Ronald Reagan", "1981-01-20", "C-SPAN"),
    # C-SPAN — Senate confirmation hearings
    ("4530797", "Brett Kavanaugh Senate Confirmation Hearing Opening", "Brett Kavanaugh", "2018-09-27", "C-SPAN"),
    ("4530798", "Christine Blasey Ford Senate Judiciary Testimony", "Christine Blasey Ford", "2018-09-27", "C-SPAN"),
    ("4886755", "Ketanji Brown Jackson Confirmation Hearing", "Ketanji Brown Jackson", "2022-03-22", "C-SPAN"),
    ("4452205", "James Comey Senate Intelligence Testimony", "James Comey", "2017-06-08", "C-SPAN"),
    ("4576139", "Robert Mueller House Judiciary Testimony", "Robert Mueller", "2019-07-24", "C-SPAN"),
    ("4418308", "Jeff Sessions Senate Intelligence Hearing", "Jeff Sessions", "2017-06-13", "C-SPAN"),
    # C-SPAN — House floor speeches
    ("4663560", "Nancy Pelosi January 6 Committee Opening Statement", "Nancy Pelosi", "2022-06-09", "C-SPAN"),
    ("4719827", "Kevin McCarthy House Floor Speech Before Speaker Vote", "Kevin McCarthy", "2023-10-03", "C-SPAN"),
    ("4724432", "Alexandria Ocasio-Cortez House Floor Speech", "Alexandria Ocasio-Cortez", "2025-02-27", "C-SPAN"),
    # C-SPAN2 — Senate floor
    ("4669891", "Chuck Schumer Senate Floor Speech on Inflation Reduction Act", "Chuck Schumer", "2022-08-06", "C-SPAN2"),
    ("4613430", "Mitch McConnell Senate Floor Speech on Capitol Attack", "Mitch McConnell", "2021-01-19", "C-SPAN2"),
    ("4610154", "Bernie Sanders Senate Floor Speech on COVID Relief", "Bernie Sanders", "2021-03-05", "C-SPAN2"),
    ("4398261", "Elizabeth Warren Senate Floor Speech on Healthcare", "Elizabeth Warren", "2017-02-07", "C-SPAN2"),
    ("4469520", "John McCain Senate Floor Speech on Healthcare Vote", "John McCain", "2017-07-28", "C-SPAN2"),
]


def _curl(url: str) -> str:
    result = subprocess.run(
        [
            "curl", "-s", "-L",
            "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "-H", "Accept-Language: en-US,en;q=0.9",
            "-H", "Referer: https://www.c-span.org/",
            url,
        ],
        capture_output=True, text=True, timeout=30,
    )
    return result.stdout


def _vtt_to_text(vtt: str) -> str:
    lines = []
    for line in vtt.splitlines():
        line = line.strip()
        if not line or line.startswith("WEBVTT") or "-->" in line or re.match(r"^\d+$", line):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        lines.append(line)
    return " ".join(" ".join(lines).split())


def fetch_transcript(video_id: str) -> str:
    from bs4 import BeautifulSoup

    # Strategy 1: WebVTT caption endpoint
    vtt = _curl(f"{BASE_URL}/video/transcript/?id={video_id}&transcriptType=cc")
    if vtt and "WEBVTT" in vtt:
        text = _vtt_to_text(vtt)
        if len(text.split()) > 80:
            return text

    # Strategy 2: Main video page
    html = _curl(f"{BASE_URL}/video/?{video_id}")
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            for key in ("transcript", "text", "description"):
                val = data.get(key, "")
                if isinstance(val, str) and len(val.split()) > 80:
                    return val
        except (json.JSONDecodeError, AttributeError):
            pass

    # Transcript / caption divs
    for sel in ["div.transcript-text", "div#transcript", "div.captions", "div.video-transcript", "div.transcript"]:
        el = soup.select_one(sel)
        if el:
            text = " ".join(el.get_text(" ", strip=True).split())
            if len(text.split()) > 80:
                return text

    # Strategy 3: JSON API
    api = _curl(f"{BASE_URL}/json/video/?id={video_id}")
    if api:
        try:
            data = json.loads(api)
            for key in ("transcript", "caption", "description"):
                val = data.get(key, "")
                if isinstance(val, str) and len(val.split()) > 80:
                    return val
        except json.JSONDecodeError:
            pass

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


def ingest(limit: int = len(VIDEOS)) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    ingested = 0

    try:
        for i, (video_id, title, speaker, date, channel) in enumerate(VIDEOS[:limit]):
            if i > 0:
                time.sleep(1)
            print(f"  [{channel}] {title}...")

            text = fetch_transcript(video_id)
            if len(text.split()) < 80:
                print(f"    Skipped — {len(text.split())} words (C-SPAN may require auth or ID is wrong)")
                continue

            source_url = f"{BASE_URL}/video/?{video_id}"
            if db.query(Transcript).filter(Transcript.source_url == source_url).first():
                print(f"    Already in DB")
                continue

            transcript = Transcript(
                title=f"[{channel}] {title}",
                source=f"c-span.org ({channel})",
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

    print(f"\nDone. {ingested}/{min(limit, len(VIDEOS))} C-SPAN transcripts ingested.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=len(VIDEOS))
    args = parser.parse_args()
    ingest(args.limit)
