"""Tokenisation shared by BM25, the hash embedder and the drug detector."""
from __future__ import annotations

import re

_TOKEN = re.compile(r"[a-z0-9]+")

# Small on purpose: negations ("no", "not") and units ("mg") must survive.
STOPWORDS = frozenset(
    "a an the of and or to in on for with is are was be can i my me should what which how "
    "does do it this that at by from as if".split()
)


def words(text: str) -> list[str]:
    """Lower-cased alphanumeric tokens, stopwords kept."""
    return _TOKEN.findall(text.lower())


def tokenize(text: str) -> list[str]:
    """Lower-cased alphanumeric tokens with stopwords removed."""
    return [t for t in words(text) if t not in STOPWORDS]
