"""Rerankers. A cross-encoder reads (query, passage) together and fixes the order of the top candidates."""
from __future__ import annotations

from .text import tokenize

CE_ALIASES = {
    "bge-reranker-base": "BAAI/bge-reranker-base",
    "bge-reranker-v2-m3": "BAAI/bge-reranker-v2-m3",
}


class Reranker:
    name: str

    def score(self, query: str, texts: list[str]) -> list[float]:
        raise NotImplementedError


class OverlapReranker(Reranker):
    """Offline stand-in: fraction of query terms (plus bigrams) found in the passage."""

    name = "overlap"

    def score(self, query: str, texts: list[str]) -> list[float]:
        q = tokenize(query)
        qset = set(q)
        qbi = set(zip(q, q[1:]))
        out = []
        for t in texts:
            toks = tokenize(t)
            tset, tbi = set(toks), set(zip(toks, toks[1:]))
            uni = len(qset & tset) / max(len(qset), 1)
            bi = len(qbi & tbi) / max(len(qbi), 1)
            out.append(uni + 0.5 * bi)
        return out


class CrossEncoderReranker(Reranker):
    def __init__(self, name: str = "bge-reranker-base", device: str | None = None):
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as e:  # pragma: no cover
            raise ImportError("Install it with: pip install sentence-transformers") from e
        self.name = name
        self.model = CrossEncoder(CE_ALIASES.get(name, name), device=device)

    def score(self, query: str, texts: list[str]) -> list[float]:
        return [float(s) for s in self.model.predict([(query, t) for t in texts])]


def get_reranker(name: str | None) -> Reranker | None:
    if not name or name == "none":
        return None
    if name == "overlap":
        return OverlapReranker()
    return CrossEncoderReranker(name)
