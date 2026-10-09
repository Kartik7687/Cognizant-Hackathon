"""The retrieval entry point everyone else calls.

    r = Retriever.from_dir("index/bge-small", reranker="bge-reranker-base")
    res = r.retrieve("Can I take ibuprofen with warfarin?", mode="hybrid_rerank", top_k=5)
    for h in res.hits: print(h.rank, h.score, h.chunk.drug_name, h.chunk.section)

Modes (these are the rows of the ablation table):
    dense          cosine similarity on embeddings
    bm25           keyword scoring
    hybrid         dense + BM25 fused with reciprocal rank fusion (RRF), plus a small section-intent boost
    hybrid_rerank  top hybrid candidates re-scored by a cross-encoder
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np

from ..schema import Chunk, format_citation
from .drug_detect import DrugDetector
from .embedder import Embedder, get_embedder
from .index import Index
from .rerank import Reranker, get_reranker
from .text import tokenize

MODES = ("dense", "bm25", "hybrid", "hybrid_rerank")
RRF_K = 60
SECTION_BOOST = 0.003  # about a 5-10 rank jump in RRF terms; switch off with section_boost=False

# (regexes matched on the lower-cased query, substrings of the section names they point to)
_SECTION_INTENTS: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    ((r"\bdos", r"\badminister", r"\bhow much\b", r"\bhow often\b", r"\bmg\b", r"\btitrat"), ("dosage",)),
    ((r"\bcontraindic", r"\bshould not (use|take)", r"\bmust not\b", r"\bnever (use|take)", r"\bwho can ?not\b"),
     ("contraindications",)),
    ((r"\binteract", r"\btogether\b", r"\bcombin", r"\balong with\b", r"\bmix\b"), ("interactions",)),
    ((r"\bwarning", r"\bprecaution", r"\bboxed\b", r"\bmonitor", r"\bdanger", r"\bcareful"), ("warnings",)),
    ((r"\bside effect", r"\badverse", r"\breaction", r"\bsymptom"), ("adverse",)),
    ((r"\bused for\b", r"\buse for\b", r"\bindicat", r"\btreat", r"\bwhat is .* for\b", r"\bpurpose\b"),
     ("indications",)),
]


@dataclass
class Hit:
    chunk: Chunk
    score: float
    rank: int  # 1-based

    def to_dict(self) -> dict:
        return {"rank": self.rank, "score": self.score, "citation": format_citation(self.chunk),
                **self.chunk.to_dict()}


@dataclass
class RetrievalResult:
    query: str
    mode: str
    detected_drugs: list[str]
    hits: list[Hit]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"query": self.query, "mode": self.mode, "detected_drugs": self.detected_drugs,
                "notes": self.notes, "hits": [h.to_dict() for h in self.hits]}


def format_context(hits: list[Hit]) -> str:
    """Numbered context block for the LLM prompt, so it can cite [1], [2], ..."""
    blocks = []
    for h in hits:
        c = h.chunk
        blocks.append(f"[{h.rank}] {format_citation(c)}\n{c.text}")
    return "\n\n".join(blocks)


def _top(scores: np.ndarray, k: int, positive_only: bool = False) -> np.ndarray:
    valid = np.isfinite(scores)
    if positive_only:
        valid &= scores > 0
    idx = np.flatnonzero(valid)
    if len(idx) == 0:
        return idx
    if len(idx) > k:
        idx = idx[np.argpartition(-scores[idx], k - 1)[:k]]
    return idx[np.argsort(-scores[idx], kind="stable")]


class Retriever:
    def __init__(self, index: Index, embedder: Embedder, reranker: Reranker | None = None):
        if embedder.name != index.embedder_name:
            raise ValueError(
                f"Index was built with '{index.embedder_name}' but embedder is '{embedder.name}'. "
                "Rebuild the index or load the matching embedder."
            )
        self.index, self.embedder, self.reranker = index, embedder, reranker
        self.detector = DrugDetector(index.chunks)

    @classmethod
    def from_dir(cls, index_dir: str, embedder: str | None = None, reranker: str | None = None) -> "Retriever":
        idx = Index.load(index_dir)
        return cls(idx, get_embedder(embedder or idx.embedder_name), get_reranker(reranker))

    # ------------------------------------------------------------------ helpers
    def _section_intent(self, query: str, n_drugs: int) -> set[str]:
        q = query.lower()
        wanted: set[str] = set()
        for patterns, sections in _SECTION_INTENTS:
            if any(re.search(p, q) for p in patterns):
                wanted.update(sections)
        if n_drugs >= 2:
            wanted.add("interactions")
        return wanted

    def _boost(self, idx: int, wanted: set[str]) -> float:
        sec = self.index.chunks[idx].section.lower()
        # word-start match: "indications" must not hit "contraindications"
        return SECTION_BOOST if any(re.search(r"\b" + w, sec) for w in wanted) else 0.0

    # --------------------------------------------------------------------- main
    def retrieve(
        self,
        query: str,
        mode: str = "hybrid_rerank",
        top_k: int = 5,
        drugs: list[str] | None = None,
        section_boost: bool = True,
        candidate_k: int = 30,
    ) -> RetrievalResult:
        """drugs=None auto-detects drug names in the query; drugs=[] disables the drug filter."""
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        notes: list[str] = []
        detected = self.detector.detect(query) if drugs is None else [d.lower() for d in drugs]

        n = len(self.index)
        mask = np.isin(self.index.drug_arr, detected) if detected else np.ones(n, dtype=bool)
        if detected and not mask.any():
            notes.append(f"drugs {detected} are not in the index; searched all drugs instead")
            mask = np.ones(n, dtype=bool)
            detected = []

        want_dense = mode in ("dense", "hybrid", "hybrid_rerank")
        want_bm25 = mode in ("bm25", "hybrid", "hybrid_rerank")
        k = max(candidate_k, top_k)

        dense_scores = bm25_scores = None
        dense_top = bm25_top = np.array([], dtype=int)
        if want_dense:
            q_vec = self.embedder.encode([query], is_query=True)[0]
            dense_scores = self.index.embeddings @ q_vec
            dense_scores = np.where(mask, dense_scores, -np.inf)
            dense_top = _top(dense_scores, k)
        if want_bm25:
            bm25_scores = self.index.bm25.scores(tokenize(query))
            bm25_scores = np.where(mask, bm25_scores, -np.inf)
            bm25_top = _top(bm25_scores, k, positive_only=True)

        if mode == "dense":
            ranked = [(int(i), float(dense_scores[i])) for i in dense_top[:top_k]]
        elif mode == "bm25":
            ranked = [(int(i), float(bm25_scores[i])) for i in bm25_top[:top_k]]
        else:
            fused: dict[int, float] = {}
            for order in (dense_top, bm25_top):
                for r, i in enumerate(order, start=1):
                    fused[int(i)] = fused.get(int(i), 0.0) + 1.0 / (RRF_K + r)
            if section_boost:
                wanted = self._section_intent(query, len(detected))
                if wanted:
                    for i in fused:
                        fused[i] += self._boost(i, wanted)
            ordered = sorted(fused.items(), key=lambda kv: -kv[1])
            if mode == "hybrid_rerank":
                if self.reranker is None:
                    notes.append("no reranker configured; returned hybrid results")
                    ranked = ordered[:top_k]
                else:
                    cand = ordered[:candidate_k]
                    ce = self.reranker.score(query, [self.index.chunks[i].text for i, _ in cand])
                    ranked = sorted(((i, float(s)) for (i, _), s in zip(cand, ce)), key=lambda kv: -kv[1])[:top_k]
            else:
                ranked = ordered[:top_k]

        hits = [Hit(self.index.chunks[i], s, r) for r, (i, s) in enumerate(ranked, start=1)]
        return RetrievalResult(query, mode, detected, hits, notes)
