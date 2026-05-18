"""
Ingests presidential speech transcripts from The American Presidency Project
(presidency.ucsb.edu) — a comprehensive, open academic archive of US
presidential documents hosted by UC Santa Barbara.

Usage:
    python -m backend.scripts.ingest_ucsb [--limit N]
"""

import argparse
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
BASE_URL = "https://www.presidency.ucsb.edu/documents"

# (slug, display_title, speaker, date)
SPEECHES = [
    # Inaugural addresses
    ("inaugural-address-2",  "JFK Inaugural Address", "John F. Kennedy", "1961-01-20"),
    ("inaugural-address-8",  "FDR First Inaugural Address", "Franklin D. Roosevelt", "1933-03-04"),
    ("inaugural-address-11", "Reagan First Inaugural Address", "Ronald Reagan", "1981-01-20"),
    ("inaugural-address-10", "Reagan Second Inaugural Address", "Ronald Reagan", "1985-01-21"),
    ("inaugural-address-5",  "Obama First Inaugural Address", "Barack Obama", "2009-01-20"),
    ("inaugural-address-15", "Obama Second Inaugural Address", "Barack Obama", "2013-01-21"),
    ("inaugural-address-14", "Trump First Inaugural Address", "Donald Trump", "2017-01-20"),
    ("inaugural-address-12", "Clinton Second Inaugural Address", "Bill Clinton", "1997-01-20"),
    ("inaugural-address-13", "George W. Bush Second Inaugural Address", "George W. Bush", "2005-01-20"),
    ("inaugural-address-1",  "Nixon First Inaugural Address", "Richard Nixon", "1969-01-20"),
    ("inaugural-address-0",  "Carter Inaugural Address", "Jimmy Carter", "1977-01-20"),
    ("inaugural-address-3",  "Eisenhower First Inaugural Address", "Dwight D. Eisenhower", "1953-01-20"),
    ("inaugural-address-4",  "Truman Inaugural Address", "Harry S. Truman", "1949-01-20"),
    ("inaugural-address-6",  "FDR Fourth Inaugural Address", "Franklin D. Roosevelt", "1945-01-20"),
    ("inaugural-address-7",  "FDR Third Inaugural Address", "Franklin D. Roosevelt", "1941-01-20"),
    ("inaugural-address-16", "Washington First Inaugural Address", "George Washington", "1789-04-30"),
    ("inaugural-address-19", "Jefferson First Inaugural Address", "Thomas Jefferson", "1801-03-04"),
    # Major addresses to the nation / Congress
    ("radio-and-television-report-the-american-people-the-soviet-arms-buildup-cuba",
     "JFK Cuban Missile Crisis Address", "John F. Kennedy", "1962-10-22"),
    ("special-message-the-congress-urgent-national-needs",
     "JFK 'We Choose to Go to the Moon' Address to Congress", "John F. Kennedy", "1961-05-25"),
    ("special-message-the-congress-the-right-vote",
     "LBJ 'We Shall Overcome' — Special Message on Voting Rights", "Lyndon B. Johnson", "1965-03-15"),
    ("special-message-the-congress-civil-rights",
     "JFK Special Message to Congress on Civil Rights", "John F. Kennedy", "1963-02-28"),
    ("address-the-nation-defense-and-national-security",
     "Reagan Strategic Defense Initiative (Star Wars) Address", "Ronald Reagan", "1983-03-23"),
    ("address-the-nation-the-explosion-the-space-shuttle-challenger",
     "Reagan Challenger Disaster Address", "Ronald Reagan", "1986-01-28"),
    ("address-the-nation-the-economy",
     "Reagan Address on the Economy", "Ronald Reagan", "1982-10-13"),
    ("address-the-nation-vietnam-0",
     "Nixon Vietnam Address (Silent Majority)", "Richard Nixon", "1969-05-14"),
    ("address-the-nation-vietnam",
     "Nixon Vietnam Address 1972", "Richard Nixon", "1972-04-26"),
    # FDR Fireside Chats
    ("fireside-chat-0",  "FDR Fireside Chat — War Production", "Franklin D. Roosevelt", "1943-05-02"),
    ("fireside-chat-1",  "FDR Fireside Chat — Inflation and Food", "Franklin D. Roosevelt", "1943-07-28"),
    ("fireside-chat-2",  "FDR Fireside Chat — D-Day Eve", "Franklin D. Roosevelt", "1944-06-05"),
    ("fireside-chat-3",  "FDR Fireside Chat — Fall of Rome", "Franklin D. Roosevelt", "1944-06-12"),
    ("fireside-chat-4",  "FDR Fireside Chat — Guadalcanal", "Franklin D. Roosevelt", "1942-10-12"),
    ("fireside-chat-5",  "FDR Fireside Chat — Civilian War Effort", "Franklin D. Roosevelt", "1942-04-28"),
    ("fireside-chat-10", "FDR Fireside Chat — Summer 1940", "Franklin D. Roosevelt", "1940-05-26"),
    # FDR State of the Union
    ("state-the-union-address-0",
     "FDR State of the Union 1943", "Franklin D. Roosevelt", "1943-01-07"),
    ("state-the-union-address-1",
     "FDR State of the Union 1942", "Franklin D. Roosevelt", "1942-01-06"),
]


def _curl(url: str) -> str:
    result = subprocess.run(
        [
            "curl", "-s", "-L",
            "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "-H", "Accept-Language: en-US,en;q=0.9",
            "-H", "Referer: https://www.presidency.ucsb.edu/",
            url,
        ],
        capture_output=True, timeout=30,
    )
    return result.stdout.decode("utf-8", errors="replace")


def scrape(slug: str) -> str:
    from bs4 import BeautifulSoup
    html = _curl(f"{BASE_URL}/{slug}")
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    el = soup.find("div", class_="field-docs-content")
    if not el:
        return ""
    for tag in el(["script", "style"]):
        tag.decompose()
    return " ".join(el.get_text(" ", strip=True).split())


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


def ingest(limit: int = len(SPEECHES)) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    ingested = 0

    try:
        for i, (slug, title, speaker, date) in enumerate(SPEECHES[:limit]):
            if i > 0:
                time.sleep(0.8)
            print(f"  [{i+1}/{min(limit, len(SPEECHES))}] {title}...")

            source_url = f"{BASE_URL}/{slug}"
            if db.query(Transcript).filter(Transcript.source_url == source_url).first():
                print(f"    Already in DB")
                continue

            text = scrape(slug)
            if len(text.split()) < 80:
                print(f"    Skipped — {len(text.split())} words")
                continue

            transcript = Transcript(
                title=title,
                source="presidency.ucsb.edu",
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

    print(f"\nDone. {ingested}/{min(limit, len(SPEECHES))} UCSB transcripts ingested.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=len(SPEECHES))
    args = parser.parse_args()
    ingest(args.limit)
