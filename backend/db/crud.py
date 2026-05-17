from sqlalchemy.orm import Session
from .models import Quote, Match, Summary, Chunk, Transcript, FactCheck


def create_quote(db: Session, text: str, speaker: str | None) -> Quote:
    q = Quote(text=text, speaker=speaker)
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def get_quote(db: Session, quote_id: int) -> Quote | None:
    return db.query(Quote).filter(Quote.id == quote_id).first()


def create_match(db: Session, quote_id: int, chunk_id: int, score: float) -> Match:
    m = Match(quote_id=quote_id, chunk_id=chunk_id, similarity_score=score)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def create_summary(db: Session, quote_id: int, text: str, model: str) -> Summary:
    s = Summary(quote_id=quote_id, summary_text=text, model_used=model)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def get_chunk_with_transcript(db: Session, chunk_id: int) -> Chunk | None:
    return db.query(Chunk).filter(Chunk.id == chunk_id).first()


def get_all_chunks(db: Session) -> list[Chunk]:
    return db.query(Chunk).order_by(Chunk.faiss_index_id).all()


def upsert_chunk_faiss_id(db: Session, chunk_id: int, faiss_id: int) -> None:
    db.query(Chunk).filter(Chunk.id == chunk_id).update({"faiss_index_id": faiss_id})
    db.commit()


def update_quote_status(db: Session, quote_id: int, status: str) -> None:
    db.query(Quote).filter(Quote.id == quote_id).update({"status": status})
    db.commit()


def create_fact_check(db: Session, quote_id: int, publisher: str, rating: str, url: str, summary: str) -> FactCheck:
    fc = FactCheck(quote_id=quote_id, publisher=publisher, rating=rating, url=url, summary=summary)
    db.add(fc)
    db.commit()
    return fc


def get_fact_checks(db: Session, quote_id: int) -> list[FactCheck]:
    return db.query(FactCheck).filter(FactCheck.quote_id == quote_id).all()
