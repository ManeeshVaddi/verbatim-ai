"""
Ingests verbatim presidential speech transcripts from the Miller Center
(millercenter.org) into the SQLite database.

All transcripts are public-domain US government speeches. Miller Center
is a nonpartisan presidential research center at the University of Virginia.

Usage:
    python -m backend.scripts.ingest_congress [--limit N]
"""

import argparse
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
BASE_URL = "https://millercenter.org"

SPEECHES = [
    ("/the-presidency/presidential-speeches/january-20-1961-inaugural-address", "JFK Inaugural Address", "John F. Kennedy", "1961-01-20"),
    ("/the-presidency/presidential-speeches/march-4-1933-first-inaugural-address", "FDR First Inaugural Address", "Franklin D. Roosevelt", "1933-03-04"),
    ("/the-presidency/presidential-speeches/january-20-1981-first-inaugural-address", "Reagan First Inaugural Address", "Ronald Reagan", "1981-01-20"),
    ("/the-presidency/presidential-speeches/january-20-2009-inaugural-address", "Obama First Inaugural Address", "Barack Obama", "2009-01-20"),
    ("/the-presidency/presidential-speeches/january-20-2017-inaugural-address", "Trump First Inaugural Address", "Donald Trump", "2017-01-20"),
    ("/the-presidency/presidential-speeches/january-20-2021-inaugural-address", "Biden Inaugural Address", "Joe Biden", "2021-01-20"),
    ("/the-presidency/presidential-speeches/january-20-2025-inaugural-address", "Trump Second Inaugural Address", "Donald Trump", "2025-01-20"),
    ("/the-presidency/presidential-speeches/december-29-1940-fireside-chat-16-arsenal-democracy", "FDR Arsenal of Democracy Speech", "Franklin D. Roosevelt", "1940-12-29"),
    ("/the-presidency/presidential-speeches/march-12-1933-fireside-chat-1-banking-crisis", "FDR First Fireside Chat — Banking Crisis", "Franklin D. Roosevelt", "1933-03-12"),
    ("/the-presidency/presidential-speeches/august-6-1945-statement-president-announcing-use-bomb", "Truman Statement on Atomic Bomb", "Harry S. Truman", "1945-08-06"),
    ("/the-presidency/presidential-speeches/january-17-1961-farewell-address", "Eisenhower Farewell Address — Military-Industrial Complex", "Dwight D. Eisenhower", "1961-01-17"),
    ("/the-presidency/presidential-speeches/september-12-1962-address-rice-university-nation-space", "JFK Moon Speech at Rice University", "John F. Kennedy", "1962-09-12"),
    ("/the-presidency/presidential-speeches/october-22-1962-address-nation-cuba", "JFK Cuban Missile Crisis Address", "John F. Kennedy", "1962-10-22"),
    ("/the-presidency/presidential-speeches/august-8-1974-address-nation-watergate", "Nixon Resignation Address", "Richard Nixon", "1974-08-08"),
    ("/the-presidency/presidential-speeches/january-28-1986-address-nation-space-shuttle-challenger", "Reagan Challenger Disaster Address", "Ronald Reagan", "1986-01-28"),
    ("/the-presidency/presidential-speeches/june-12-1987-remarks-berlin-wall", "Reagan Berlin Wall Speech", "Ronald Reagan", "1987-06-12"),
    ("/the-presidency/presidential-speeches/january-28-1992-state-union-address", "George H.W. Bush State of the Union", "George H.W. Bush", "1992-01-28"),
    ("/the-presidency/presidential-speeches/january-23-1996-state-union-address", "Clinton State of the Union — Era of Big Government", "Bill Clinton", "1996-01-23"),
    ("/the-presidency/presidential-speeches/september-20-2001-address-joint-session-congress", "George W. Bush Address After 9/11", "George W. Bush", "2001-09-20"),
    ("/the-presidency/presidential-speeches/january-28-2003-state-union-address", "George W. Bush State of the Union 2003", "George W. Bush", "2003-01-28"),
    ("/the-presidency/presidential-speeches/january-27-2010-state-union-address", "Obama State of the Union 2010", "Barack Obama", "2010-01-27"),
    ("/the-presidency/presidential-speeches/january-25-2011-state-union-address", "Obama State of the Union 2011", "Barack Obama", "2011-01-25"),
    ("/the-presidency/presidential-speeches/january-20-2015-state-union-address", "Obama State of the Union 2015", "Barack Obama", "2015-01-20"),
    ("/the-presidency/presidential-speeches/february-5-2019-state-union-address", "Trump State of the Union 2019", "Donald Trump", "2019-02-05"),
    ("/the-presidency/presidential-speeches/march-7-2024-state-union-address", "Biden State of the Union 2024", "Joe Biden", "2024-03-07"),
    ("/the-presidency/presidential-speeches/march-4-2025-address-joint-session-congress", "Trump Address to Joint Session 2025", "Donald Trump", "2025-03-04"),
    ("/the-presidency/presidential-speeches/february-24-2026-state-union-address", "Trump State of the Union 2026", "Donald Trump", "2026-02-24"),
    ("/the-presidency/presidential-speeches/january-15-2025-farewell-address", "Biden Farewell Address", "Joe Biden", "2025-01-15"),
    ("/the-presidency/presidential-speeches/april-4-1968-remarks-assassination-martin-luther-king-jr", "RFK Remarks on MLK Assassination", "Robert F. Kennedy", "1968-04-04"),
    ("/the-presidency/presidential-speeches/july-2-1964-remarks-signing-civil-rights-act", "LBJ Remarks on Signing Civil Rights Act", "Lyndon B. Johnson", "1964-07-02"),
    ("/the-presidency/presidential-speeches/august-28-1963-march-washington", "MLK 'I Have a Dream' Speech", "Martin Luther King Jr.", "1963-08-28"),
    ("/the-presidency/presidential-speeches/january-20-1953-first-inaugural-address", "Eisenhower First Inaugural Address", "Dwight D. Eisenhower", "1953-01-20"),
    ("/the-presidency/presidential-speeches/may-25-1961-special-message-congress-urgent-national-needs", "JFK Man on the Moon Address to Congress", "John F. Kennedy", "1961-05-25"),
    ("/the-presidency/presidential-speeches/december-8-1941-pearl-harbor-address-nation", "FDR Pearl Harbor Address", "Franklin D. Roosevelt", "1941-12-08"),
    ("/the-presidency/presidential-speeches/november-19-1863-gettysburg-address", "Lincoln Gettysburg Address", "Abraham Lincoln", "1863-11-19"),
    ("/the-presidency/presidential-speeches/march-4-1865-second-inaugural-address", "Lincoln Second Inaugural Address", "Abraham Lincoln", "1865-03-04"),
    ("/the-presidency/presidential-speeches/january-6-2021-ellipse-speech", "Trump Ellipse Speech January 6", "Donald Trump", "2021-01-06"),
    ("/the-presidency/presidential-speeches/april-30-1975-address-nation-vietnam", "Ford Address on Vietnam", "Gerald Ford", "1975-04-30"),
    ("/the-presidency/presidential-speeches/april-3-1968-ive-been-mountaintop", "MLK 'I've Been to the Mountaintop'", "Martin Luther King Jr.", "1968-04-03"),
    ("/the-presidency/presidential-speeches/january-11-1989-farewell-address", "Reagan Farewell Address", "Ronald Reagan", "1989-01-11"),
    # Additional speeches
    ("/the-presidency/presidential-speeches/january-6-1941-state-union-address", "FDR Four Freedoms State of the Union", "Franklin D. Roosevelt", "1941-01-06"),
    ("/the-presidency/presidential-speeches/march-12-1947-address-congress-greece-turkey", "Truman Doctrine Address to Congress", "Harry S. Truman", "1947-03-12"),
    ("/the-presidency/presidential-speeches/june-11-1963-address-civil-rights", "JFK Civil Rights Address to the Nation", "John F. Kennedy", "1963-06-11"),
    ("/the-presidency/presidential-speeches/january-8-1964-state-union-address", "LBJ State of the Union — War on Poverty", "Lyndon B. Johnson", "1964-01-08"),
    ("/the-presidency/presidential-speeches/march-15-1965-special-message-congress-voting-rights", "LBJ Voting Rights Address — We Shall Overcome", "Lyndon B. Johnson", "1965-03-15"),
    ("/the-presidency/presidential-speeches/november-3-1969-address-nation-vietnam", "Nixon Silent Majority Speech", "Richard Nixon", "1969-11-03"),
    ("/the-presidency/presidential-speeches/january-20-1969-first-inaugural-address", "Nixon First Inaugural Address", "Richard Nixon", "1969-01-20"),
    ("/the-presidency/presidential-speeches/july-15-1979-crisis-confidence", "Carter Crisis of Confidence Speech", "Jimmy Carter", "1979-07-15"),
    ("/the-presidency/presidential-speeches/january-16-1991-address-nation-gulf-war", "George H.W. Bush Address on Gulf War", "George H.W. Bush", "1991-01-16"),
    ("/the-presidency/presidential-speeches/january-20-1993-first-inaugural-address", "Clinton First Inaugural Address", "Bill Clinton", "1993-01-20"),
    ("/the-presidency/presidential-speeches/august-17-1998-address-nation-testimony", "Clinton Address on Lewinsky Testimony", "Bill Clinton", "1998-08-17"),
    ("/the-presidency/presidential-speeches/january-20-2005-second-inaugural-address", "George W. Bush Second Inaugural Address", "George W. Bush", "2005-01-20"),
    ("/the-presidency/presidential-speeches/january-21-2013-second-inaugural-address", "Obama Second Inaugural Address", "Barack Obama", "2013-01-21"),
    ("/the-presidency/presidential-speeches/december-10-2009-remarks-accepting-nobel-peace-prize", "Obama Nobel Peace Prize Remarks", "Barack Obama", "2009-12-10"),
]


def curl_fetch(url: str) -> str:
    result = subprocess.run(
        [
            "curl", "-s", "-L",
            "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "-H", "Accept-Language: en-US,en;q=0.9",
            "-H", f"Referer: {BASE_URL}/",
            url,
        ],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout


def scrape_transcript(path: str) -> str:
    from bs4 import BeautifulSoup
    html = curl_fetch(BASE_URL + path)
    if not html.strip():
        return ""

    soup = BeautifulSoup(html, "html.parser")

    transcript_div = (
        soup.find("div", class_="transcript-inner") or
        soup.find("div", class_=lambda c: c and "transcript" in str(c).lower()) or
        soup.find("div", {"id": "transcript"})
    )

    if not transcript_div:
        # Fallback: largest text block on the page
        divs = soup.find_all("div")
        transcript_div = max(divs, key=lambda d: len(d.get_text()), default=None)

    if not transcript_div:
        return ""

    for tag in transcript_div(["script", "style", "aside", "nav"]):
        tag.decompose()

    text = " ".join(transcript_div.get_text(" ", strip=True).split())
    return text


def chunk_text(text: str) -> list[tuple[str, int]]:
    words = text.split()
    chunks = []
    step = CHUNK_WORDS - OVERLAP_WORDS
    char_offset = 0

    for start in range(0, len(words), step):
        window = words[start: start + CHUNK_WORDS]
        chunk_str = " ".join(window)
        if not words[start:]:
            break
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
        for i, (path, title, speaker, date) in enumerate(SPEECHES[:limit]):
            if i > 0:
                time.sleep(1)
            print(f"  Fetching: {title}...")
            text = scrape_transcript(path)

            if len(text.split()) < 100:
                print(f"    Skipped (too short — {len(text.split())} words)")
                continue

            transcript = Transcript(
                title=title,
                source="millercenter.org",
                source_url=BASE_URL + path,
                speaker=speaker,
                full_text=text,
                date=date,
            )
            db.add(transcript)
            db.flush()

            added_chunks = 0
            for i, (chunk_str, start_char) in enumerate(chunk_text(text)):
                if len(chunk_str.split()) < 20:
                    continue
                db.add(Chunk(
                    transcript_id=transcript.id,
                    chunk_index=i,
                    text=chunk_str,
                    start_char=start_char,
                ))
                added_chunks += 1

            db.commit()
            ingested += 1
            print(f"    OK — {len(text.split())} words, {added_chunks} chunks")

    finally:
        db.close()

    print(f"\nDone. {ingested}/{limit} transcripts ingested.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=len(SPEECHES))
    args = parser.parse_args()
    ingest(args.limit)
