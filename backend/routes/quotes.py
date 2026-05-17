from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from ..db.database import get_db
from ..db import crud
from ..services import embedder, matcher, summarizer, factcheck
from ..limiter import limiter

router = APIRouter(prefix="/api/quotes", tags=["quotes"])

MAX_QUOTE_CHARS = 1000


class QuoteSubmit(BaseModel):
    text: str
    speaker: str | None = None

    @field_validator("text")
    @classmethod
    def text_not_empty_or_huge(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Quote text cannot be empty")
        if len(v) > MAX_QUOTE_CHARS:
            raise ValueError(f"Quote must be under {MAX_QUOTE_CHARS} characters")
        return v


class FactCheckOut(BaseModel):
    publisher: str
    rating: str
    url: str
    summary: str


class MatchOut(BaseModel):
    transcript_title: str
    source_url: str
    excerpt: str
    similarity: float
    speech_date: str | None = None
    speech_speaker: str | None = None


class QuoteResult(BaseModel):
    quote_id: int
    status: str
    quote_text: str | None = None
    speaker: str | None = None
    match: MatchOut | None = None
    summary: str | None = None
    fact_checks: list[FactCheckOut] = []


def _run_pipeline(quote_id: int, text: str, speaker: str | None) -> None:
    from ..db.database import SessionLocal
    db = SessionLocal()
    try:
        vec = embedder.embed(text)
        hits = matcher.search(vec, k=5)

        if not hits:
            print(f"No FAISS hits for quote {quote_id} (similarity below threshold)")
            crud.update_quote_status(db, quote_id, "no_match")
            return

        best = hits[0]
        chunk = db.query(crud.Chunk).filter(crud.Chunk.faiss_index_id == best.faiss_index_id).first()
        if not chunk:
            print(f"Chunk not found for faiss_index_id {best.faiss_index_id}")
            crud.update_quote_status(db, quote_id, "no_match")
            return

        crud.create_match(db, quote_id=quote_id, chunk_id=chunk.id, score=best.similarity_score)

        transcript = chunk.transcript
        summary_text = summarizer.summarize(
            quote_text=text,
            speaker=speaker,
            excerpt=chunk.text,
            source_title=transcript.title,
            source_url=transcript.source_url,
        )
        crud.create_summary(db, quote_id=quote_id, text=summary_text, model=summarizer.MODEL)

        checks = factcheck.fetch_fact_checks(text, speaker)
        for c in checks:
            crud.create_fact_check(
                db,
                quote_id=quote_id,
                publisher=c.publisher,
                rating=c.rating,
                url=c.url,
                summary=c.summary,
            )

        crud.update_quote_status(db, quote_id, "complete")
        print(f"Pipeline complete for quote {quote_id} — similarity {best.similarity_score:.2f}")
    except Exception as exc:
        import traceback
        print(f"Pipeline error for quote {quote_id}: {exc}")
        traceback.print_exc()
        crud.update_quote_status(db, quote_id, "error")
    finally:
        db.close()


@router.post("", response_model=QuoteResult, status_code=202)
@limiter.limit("10/hour")
def submit_quote(request: Request, body: QuoteSubmit, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    quote = crud.create_quote(db, text=body.text, speaker=body.speaker)
    background_tasks.add_task(_run_pipeline, quote.id, body.text, body.speaker)
    return QuoteResult(quote_id=quote.id, status="processing", quote_text=body.text, speaker=body.speaker)


@router.get("/{quote_id}", response_model=QuoteResult)
def get_quote(quote_id: int, db: Session = Depends(get_db)):
    quote = crud.get_quote(db, quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    status = quote.status

    if status in ("processing", "no_match", "error"):
        return QuoteResult(
            quote_id=quote.id,
            status=status,
            quote_text=quote.text,
            speaker=quote.speaker,
        )

    best_match = sorted(quote.matches, key=lambda m: m.similarity_score, reverse=True)[0]
    chunk = best_match.chunk
    transcript = chunk.transcript

    match_out = MatchOut(
        transcript_title=transcript.title,
        source_url=transcript.source_url,
        excerpt=chunk.text,
        similarity=round(best_match.similarity_score, 3),
        speech_date=transcript.date,
        speech_speaker=transcript.speaker,
    )

    summary_text = quote.summary.summary_text if quote.summary else None

    stored_checks = crud.get_fact_checks(db, quote_id)
    fact_checks_out = [
        FactCheckOut(
            publisher=c.publisher or "",
            rating=c.rating or "",
            url=c.url or "",
            summary=c.summary or "",
        )
        for c in stored_checks
    ]

    return QuoteResult(
        quote_id=quote.id,
        status="complete",
        quote_text=quote.text,
        speaker=quote.speaker,
        match=match_out,
        summary=summary_text,
        fact_checks=fact_checks_out,
    )
