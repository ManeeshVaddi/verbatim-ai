"""
Ingests speech transcripts from AmericanRhetoric.com — a comprehensive
public archive of major US political and historical speeches.

All transcripts are of public record speeches. AmericanRhetoric.com
provides clean HTML pages, making scraping reliable.

Usage:
    python -m backend.scripts.ingest_american_rhetoric [--limit N]
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
BASE_URL = "https://www.americanrhetoric.com"

# (path, title, speaker, date)
SPEECHES = [
    # Civil rights era
    ("/speeches/mlkihaveadream.htm", "MLK 'I Have a Dream' Speech", "Martin Luther King Jr.", "1963-08-28"),
    ("/speeches/mlkletterfrombirminghamjail.htm", "MLK Letter from Birmingham Jail", "Martin Luther King Jr.", "1963-04-16"),
    ("/speeches/johnlewismarchonwashington.htm", "John Lewis March on Washington Speech", "John Lewis", "1963-08-28"),
    ("/speeches/malcolmxballotorthebullet.htm", "Malcolm X The Ballot or the Bullet", "Malcolm X", "1964-04-03"),
    ("/speeches/rfkmlkdeath.htm", "RFK Remarks on Assassination of MLK", "Robert F. Kennedy", "1968-04-04"),
    # Presidential
    ("/speeches/fdrpearlharbor.htm", "FDR Pearl Harbor Address to Congress", "Franklin D. Roosevelt", "1941-12-08"),
    ("/speeches/fdrfireinaugural.htm", "FDR First Inaugural Address", "Franklin D. Roosevelt", "1933-03-04"),
    ("/speeches/jfkinaugural.htm", "JFK Inaugural Address", "John F. Kennedy", "1961-01-20"),
    ("/speeches/jfkcubanmissile.htm", "JFK Cuban Missile Crisis Address", "John F. Kennedy", "1962-10-22"),
    ("/speeches/jfkberlin.htm", "JFK 'Ich Bin Ein Berliner' Speech", "John F. Kennedy", "1963-06-26"),
    ("/speeches/lbjweovercomeaddress.htm", "LBJ 'We Shall Overcome' Address to Congress", "Lyndon B. Johnson", "1965-03-15"),
    ("/speeches/nixoncheckersaddress.htm", "Nixon Checkers Speech", "Richard Nixon", "1952-09-23"),
    ("/speeches/nixonresignation.htm", "Nixon Resignation Address", "Richard Nixon", "1974-08-08"),
    ("/speeches/ronaldreaganberlinwall.htm", "Reagan 'Tear Down This Wall' Speech", "Ronald Reagan", "1987-06-12"),
    ("/speeches/reaganchallenger.htm", "Reagan Challenger Disaster Address", "Ronald Reagan", "1986-01-28"),
    ("/speeches/reaganfirstinaugural.htm", "Reagan First Inaugural Address", "Ronald Reagan", "1981-01-20"),
    ("/speeches/barackobamadnc2004.htm", "Obama DNC Keynote Address 2004", "Barack Obama", "2004-07-27"),
    ("/speeches/barackobamavictoryspeech.htm", "Obama Victory Speech 2008", "Barack Obama", "2008-11-04"),
    ("/speeches/barackobamafirstinaugural.htm", "Obama First Inaugural Address", "Barack Obama", "2009-01-20"),
    ("/speeches/hillaryclinton1995beijingspeech.htm", "Hillary Clinton Beijing Women's Rights Speech", "Hillary Clinton", "1995-09-05"),
    # Congress and Senate floor
    ("/speeches/barbarajordandemocraticconvention.htm", "Barbara Jordan 1976 DNC Keynote", "Barbara Jordan", "1976-07-12"),
    ("/speeches/geraldfordinaugural.htm", "Gerald Ford Inaugural Address", "Gerald Ford", "1974-08-09"),
    ("/speeches/johnkennedymoonaddress.htm", "JFK Moon Speech at Rice University", "John F. Kennedy", "1962-09-12"),
    # Contemporary
    ("/speeches/georgewbush911addresstothenation.htm", "George W. Bush 9/11 Address to the Nation", "George W. Bush", "2001-09-11"),
    ("/speeches/georgewbushaddresstojointsession.htm", "George W. Bush Address to Congress After 9/11", "George W. Bush", "2001-09-20"),
    ("/speeches/obamafuneraltucson.htm", "Obama Memorial Address Tucson Shooting", "Barack Obama", "2011-01-12"),
    ("/speeches/barackobamachandychurch.htm", "Obama Charleston Eulogy — Amazing Grace", "Barack Obama", "2015-06-26"),
    ("/speeches/hillaryclintonconcessionspeech2016.htm", "Hillary Clinton 2016 Concession Speech", "Hillary Clinton", "2016-11-09"),
    # Historical
    ("/speeches/abrahamlincolngettysburgaddress.htm", "Lincoln Gettysburg Address", "Abraham Lincoln", "1863-11-19"),
    ("/speeches/abrahamlincolnsecondinaugural.htm", "Lincoln Second Inaugural Address", "Abraham Lincoln", "1865-03-04"),
    ("/speeches/sojournertrutharnti.htm", "Sojourner Truth 'Ain't I a Woman'", "Sojourner Truth", "1851-05-29"),
    ("/speeches/fdrfourfreedoms.htm", "FDR Four Freedoms Speech", "Franklin D. Roosevelt", "1941-01-06"),
    ("/speeches/dwightdeisenhowermilitaryindustrialcomplex.htm", "Eisenhower Farewell — Military-Industrial Complex", "Dwight D. Eisenhower", "1961-01-17"),
    # Social and cultural
    ("/speeches/caesarchavezunionaddress.htm", "Cesar Chavez UFW Address", "Cesar Chavez", "1984-11-09"),
    ("/speeches/harveymiilk1978speechcalifornia.htm", "Harvey Milk Hope Speech", "Harvey Milk", "1978-06-25"),
    ("/speeches/shirleychisholmcongressspeech.htm", "Shirley Chisholm Presidential Campaign Announcement", "Shirley Chisholm", "1972-01-25"),
]


def _curl(url: str) -> str:
    result = subprocess.run(
        [
            "curl", "-s", "-L",
            "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "-H", "Accept-Language: en-US,en;q=0.9",
            "-H", f"Referer: {BASE_URL}/",
            url,
        ],
        capture_output=True, timeout=30,
    )
    return result.stdout.decode("utf-8", errors="replace")


def scrape_transcript(path: str) -> str:
    from bs4 import BeautifulSoup

    html = _curl(BASE_URL + path)
    if not html.strip():
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # AmericanRhetoric pages use a <div> containing the speech text.
    # Remove nav, header, footer, scripts, and ads first.
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "iframe"]):
        tag.decompose()

    # Try well-known selectors first
    for sel in ["div#speech-text", "div.speech", "div#transcript", "article", "div.entry-content"]:
        el = soup.select_one(sel)
        if el:
            text = " ".join(el.get_text(" ", strip=True).split())
            if len(text.split()) > 100:
                return text

    # Fallback: largest paragraph block
    candidates = soup.find_all(["div", "td"])
    if candidates:
        best = max(candidates, key=lambda t: len(t.get_text()))
        text = " ".join(best.get_text(" ", strip=True).split())
        if len(text.split()) > 100:
            return text

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


def ingest(limit: int = len(SPEECHES)) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    ingested = 0

    try:
        for i, (path, title, speaker, date) in enumerate(SPEECHES[:limit]):
            if i > 0:
                time.sleep(0.5)
            print(f"  Fetching: {title}...")

            text = scrape_transcript(path)
            if len(text.split()) < 100:
                print(f"    Skipped — {len(text.split())} words")
                continue

            source_url = BASE_URL + path
            if db.query(Transcript).filter(Transcript.source_url == source_url).first():
                print(f"    Already in DB")
                continue

            transcript = Transcript(
                title=title,
                source="americanrhetoric.com",
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

    print(f"\nDone. {ingested}/{min(limit, len(SPEECHES))} American Rhetoric transcripts ingested.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=len(SPEECHES))
    args = parser.parse_args()
    ingest(args.limit)
