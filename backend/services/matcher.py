import os
import numpy as np
import faiss
from dataclasses import dataclass

_index: faiss.IndexFlatIP | None = None
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "./data/faiss_index.bin")
SIMILARITY_THRESHOLD = 0.25


@dataclass
class ChunkMatch:
    faiss_index_id: int
    similarity_score: float


def load_index() -> faiss.IndexFlatIP:
    global _index
    if _index is None:
        if not os.path.exists(FAISS_INDEX_PATH):
            raise FileNotFoundError(
                f"FAISS index not found at {FAISS_INDEX_PATH}. "
                "Run scripts/build_index.py first."
            )
        _index = faiss.read_index(FAISS_INDEX_PATH)
    return _index


def search(vec: np.ndarray, k: int = 5) -> list[ChunkMatch]:
    index = load_index()
    if index.ntotal == 0:
        return []

    query = vec.reshape(1, -1)
    scores, ids = index.search(query, min(k, index.ntotal))

    results = []
    for score, idx in zip(scores[0], ids[0]):
        if idx == -1:
            continue
        if float(score) >= SIMILARITY_THRESHOLD:
            results.append(ChunkMatch(faiss_index_id=int(idx), similarity_score=float(score)))
    return results
