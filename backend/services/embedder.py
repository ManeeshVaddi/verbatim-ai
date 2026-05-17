import numpy as np
from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None
MODEL_NAME = "all-MiniLM-L6-v2"


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed(text: str) -> np.ndarray:
    vec = get_model().encode([text], normalize_embeddings=True)
    return vec[0].astype(np.float32)


def embed_batch(texts: list[str]) -> np.ndarray:
    vecs = get_model().encode(texts, normalize_embeddings=True, batch_size=64, show_progress_bar=True)
    return vecs.astype(np.float32)
