"""Index = chunks + dense embeddings + BM25. Persisted as chunks.jsonl, embeddings.npy, meta.json.

A plain numpy matrix is enough here: 30k chunks x 384-d is ~46 MB and a matrix-vector product takes
milliseconds, with exact search and trivial metadata filtering. Swap in Chroma/FAISS only if the
corpus grows by orders of magnitude.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ..schema import Chunk, load_chunks, save_chunks
from .bm25 import BM25
from .embedder import Embedder
from .text import tokenize


def embedding_text(c: Chunk) -> str:
    """Prefix the drug and section so a bare 'Contraindications' chunk still knows whose it is."""
    return f"{c.drug_name} - {c.section}\n{c.text}"


def bm25_text(c: Chunk) -> str:
    return " ".join([c.drug_name, *c.aliases, c.section, c.text])


class Index:
    def __init__(self, chunks: list[Chunk], embeddings: np.ndarray, embedder_name: str):
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings differ in length")
        self.chunks = chunks
        self.embeddings = embeddings.astype(np.float32, copy=False)
        self.embedder_name = embedder_name
        self.drug_arr = np.array([c.drug_name for c in chunks])
        self.bm25 = BM25([tokenize(bm25_text(c)) for c in chunks])

    def __len__(self) -> int:
        return len(self.chunks)

    @classmethod
    def build(cls, chunks: list[Chunk], embedder: Embedder, batch_size: int = 128) -> "Index":
        texts = [embedding_text(c) for c in chunks]
        parts = [embedder.encode(texts[i : i + batch_size]) for i in range(0, len(texts), batch_size)]
        emb = np.vstack(parts) if parts else np.zeros((0, embedder.dim), dtype=np.float32)
        return cls(chunks, emb, embedder.name)

    def save(self, directory: str | Path) -> None:
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        save_chunks(self.chunks, d / "chunks.jsonl")
        np.save(d / "embeddings.npy", self.embeddings)
        meta = {
            "embedder": self.embedder_name,
            "dim": int(self.embeddings.shape[1]) if len(self.embeddings) else 0,
            "n_chunks": len(self.chunks),
            "n_drugs": int(len(set(self.drug_arr.tolist()))),
        }
        (d / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, directory: str | Path) -> "Index":
        d = Path(directory)
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        return cls(load_chunks(d / "chunks.jsonl"), np.load(d / "embeddings.npy"), meta["embedder"])
