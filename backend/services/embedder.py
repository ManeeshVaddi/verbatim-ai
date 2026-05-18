import numpy as np
from fastembed import TextEmbedding

_model: TextEmbedding | None = None
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def get_model() -> TextEmbedding:
    global _model
    if _model is None:
        _model = TextEmbedding(model_name=MODEL_NAME)
    return _model


def embed(text: str) -> np.ndarray:
    vecs = list(get_model().embed([text]))
    return np.array(vecs[0], dtype=np.float32)


def embed_batch(texts: list[str]) -> np.ndarray:
    vecs = list(get_model().embed(texts))
    return np.array(vecs, dtype=np.float32)
