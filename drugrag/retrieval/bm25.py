"""Dependency-free BM25 (Okapi) with an inverted index."""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Sequence

import numpy as np


class BM25:
    def __init__(self, docs: Sequence[Sequence[str]], k1: float = 1.5, b: float = 0.75):
        self.n = len(docs)
        self.k1, self.b = k1, b
        self.doc_len = np.array([len(d) for d in docs], dtype=np.float32)
        self.avgdl = float(self.doc_len.mean()) if self.n else 1.0
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for i, doc in enumerate(docs):
            for term, tf in Counter(doc).items():
                self.postings[term].append((i, tf))
        self.idf = {
            t: math.log(1.0 + (self.n - len(p) + 0.5) / (len(p) + 0.5))
            for t, p in self.postings.items()
        }

    def scores(self, query_tokens: Sequence[str]) -> np.ndarray:
        s = np.zeros(self.n, dtype=np.float32)
        for term in set(query_tokens):
            post = self.postings.get(term)
            if not post:
                continue
            idf = self.idf[term]
            for i, tf in post:
                norm = self.k1 * (1.0 - self.b + self.b * self.doc_len[i] / self.avgdl)
                s[i] += idf * tf * (self.k1 + 1.0) / (tf + norm)
        return s
