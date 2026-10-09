"""Find which drug(s) a question is about, so retrieval can filter to them.

Wrong-drug answers are the worst failure in this domain, so this runs before any search.
Matches generic names and brand aliases (longest n-gram first), then falls back to fuzzy
matching for typos ("metfromin"). Names come from the index itself, so no extra lexicon file.
"""
from __future__ import annotations

import difflib
from typing import Iterable

from ..schema import Chunk
from .text import words

FUZZY_MIN_LEN = 6
FUZZY_CUTOFF = 0.82


class DrugDetector:
    def __init__(self, chunks: Iterable[Chunk]):
        self.surface_to_drug: dict[str, str] = {}
        for c in chunks:
            for surface in (c.drug_name, *c.aliases):
                key = " ".join(words(surface))
                if key:
                    self.surface_to_drug.setdefault(key, c.drug_name)
        self.max_ngram = max((len(k.split()) for k in self.surface_to_drug), default=1)
        self._fuzzy_pool = [k for k in self.surface_to_drug if " " not in k and len(k) >= FUZZY_MIN_LEN]

    def detect(self, query: str) -> list[str]:
        toks = words(query)
        used = [False] * len(toks)
        found: list[str] = []

        def add(drug: str) -> None:
            if drug not in found:
                found.append(drug)

        for n in range(min(self.max_ngram, len(toks)), 0, -1):
            for i in range(len(toks) - n + 1):
                if any(used[i : i + n]):
                    continue
                drug = self.surface_to_drug.get(" ".join(toks[i : i + n]))
                if drug:
                    add(drug)
                    for j in range(i, i + n):
                        used[j] = True

        for i, tok in enumerate(toks):
            if used[i] or len(tok) < FUZZY_MIN_LEN:
                continue
            match = difflib.get_close_matches(tok, self._fuzzy_pool, n=1, cutoff=FUZZY_CUTOFF)
            if match:
                add(self.surface_to_drug[match[0]])
                used[i] = True
        return found
