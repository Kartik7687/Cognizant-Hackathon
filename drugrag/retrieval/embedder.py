"""Swappable embedders. Switch models with one string; the index remembers which one built it.

    get_embedder("hash")        offline, numpy only (tests / CI / quick wiring checks)
    get_embedder("bge-small")   BAAI/bge-small-en-v1.5, 384-d, fast on CPU  (recommended default)
    get_embedder("bge-m3")      BAAI/bge-m3, 1024-d, best quality, slower
    get_embedder("minilm")      all-MiniLM-L6-v2, 384-d, fastest
    get_embedder("<hf id>")     any sentence-transformers model
"""
from __future__ import annotations

import zlib

import numpy as np

from .text import tokenize

HF_ALIASES = {
    "bge-small": "BAAI/bge-small-en-v1.5",
    "bge-m3": "BAAI/bge-m3",
    "minilm": "sentence-transformers/all-MiniLM-L6-v2",
}
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class Embedder:
    name: str
    dim: int

    def encode(self, texts: list[str], is_query: bool = False) -> np.ndarray:
        """Return L2-normalised float32 array of shape (len(texts), dim)."""
        raise NotImplementedError


class HashEmbedder(Embedder):
    """Feature-hashed bag of uni+bigrams. Not semantic; only for offline tests and wiring."""

    def __init__(self, dim: int = 2048):
        self.name = "hash"
        self.dim = dim

    def encode(self, texts: list[str], is_query: bool = False) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for r, text in enumerate(texts):
            toks = tokenize(text)
            feats = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
            for f in feats:
                out[r, zlib.crc32(f.encode("utf-8")) % self.dim] += 1.0
        out = np.log1p(out)
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.maximum(norms, 1e-9)


class SentenceTransformerEmbedder(Embedder):
    def __init__(self, name: str, batch_size: int = 32, device: str | None = None):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:  # pragma: no cover
            raise ImportError("Install it with: pip install sentence-transformers") from e
        self.name = name
        hf_id = HF_ALIASES.get(name, name)
        self.model = SentenceTransformer(hf_id, device=device)
        self.dim = int(self.model.get_sentence_embedding_dimension())
        self.batch_size = batch_size
        low = hf_id.lower()
        # bge v1.5 english models want an instruction on queries; bge-m3 does not.
        self.query_prefix = BGE_QUERY_PREFIX if ("bge" in low and "m3" not in low) else ""

    def encode(self, texts: list[str], is_query: bool = False) -> np.ndarray:
        if is_query and self.query_prefix:
            texts = [self.query_prefix + t for t in texts]
        emb = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 256,
        )
        return np.asarray(emb, dtype=np.float32)


def get_embedder(name: str) -> Embedder:
    if name == "hash":
        return HashEmbedder()
    return SentenceTransformerEmbedder(name)
