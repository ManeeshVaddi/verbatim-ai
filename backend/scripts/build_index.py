"""
Loads all chunks from SQLite, generates sentence-transformer embeddings,
and writes a FAISS IndexFlatIP to disk.

Must be run after ingest_congress.py.

Usage:
    python -m backend.scripts.build_index
"""

import os
import sys
import numpy as np
import faiss
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
load_dotenv()

from backend.db.database import SessionLocal
from backend.db import crud
from backend.services.embedder import embed_batch

FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "./backend/data/faiss_index.bin")


def build() -> None:
    db = SessionLocal()
    try:
        chunks = crud.get_all_chunks(db)
        if not chunks:
            print("No chunks found. Run ingest_congress.py first.")
            sys.exit(1)

        print(f"Embedding {len(chunks)} chunks...")
        texts = [c.text for c in chunks]
        vectors = embed_batch(texts)

        dim = vectors.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(vectors)

        os.makedirs(os.path.dirname(FAISS_INDEX_PATH), exist_ok=True)
        faiss.write_index(index, FAISS_INDEX_PATH)
        print(f"FAISS index written: {FAISS_INDEX_PATH} ({index.ntotal} vectors, dim={dim})")

        # Store faiss_index_id on each chunk (position in index = insertion order)
        for faiss_id, chunk in enumerate(chunks):
            crud.upsert_chunk_faiss_id(db, chunk_id=chunk.id, faiss_id=faiss_id)

        print("Chunk faiss_index_id values updated in DB.")
    finally:
        db.close()


if __name__ == "__main__":
    build()
