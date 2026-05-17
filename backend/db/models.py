from datetime import datetime, timezone
from sqlalchemy import Integer, String, Text, Float, DateTime, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(64))
    source_url: Mapped[str] = mapped_column(Text)
    speaker: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_text: Mapped[str] = mapped_column(Text)
    date: Mapped[str | None] = mapped_column(String(32), nullable=True)

    chunks: Mapped[list["Chunk"]] = relationship(back_populates="transcript")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    transcript_id: Mapped[int] = mapped_column(ForeignKey("transcripts.id"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    start_char: Mapped[int] = mapped_column(Integer)
    faiss_index_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    transcript: Mapped["Transcript"] = relationship(back_populates="chunks")
    matches: Mapped[list["Match"]] = relationship(back_populates="chunk")


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    text: Mapped[str] = mapped_column(Text)
    speaker: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    status: Mapped[str] = mapped_column(String(32), default="processing", nullable=False)

    matches: Mapped[list["Match"]] = relationship(back_populates="quote")
    summary: Mapped["Summary | None"] = relationship(back_populates="quote", uselist=False)
    fact_checks: Mapped[list["FactCheck"]] = relationship(back_populates="quote")


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"))
    chunk_id: Mapped[int] = mapped_column(ForeignKey("chunks.id"))
    similarity_score: Mapped[float] = mapped_column(Float)

    quote: Mapped["Quote"] = relationship(back_populates="matches")
    chunk: Mapped["Chunk"] = relationship(back_populates="matches")


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"), unique=True)
    summary_text: Mapped[str] = mapped_column(Text)
    model_used: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    quote: Mapped["Quote"] = relationship(back_populates="summary")


class FactCheck(Base):
    __tablename__ = "fact_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"), nullable=False)
    publisher: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    quote: Mapped["Quote"] = relationship(back_populates="fact_checks")
