"""Stopgap clean-up of chunks.jsonl, for output that was already produced.

Fixes only what can be fixed from the chunks themselves:
  - effective_date YYYYMMDD -> YYYY-MM-DD
  - brand-name aliases (lowercase) and generic names for drugs downloaded under a brand
  - drops Principal Display Panel chunks (carton text, no medical content)
  - splits chunks longer than MAX_CHARS at sentence boundaries
  - regenerates readable, unique, stable chunk_ids

What it cannot fix (needs the raw XML, see the parser notes): missing sections, boxed warnings,
LOINC section codes, subsection headings, and the choice of which label was downloaded.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import replace

from ..schema import Chunk
from .aliases import BRAND_ALIASES, RENAME_DRUG

MAX_CHARS = 1500
MIN_CHARS = 40
DROP_SECTIONS = {"Principal Display Panel"}

_SENT_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\[•])")


def iso_date(value: str) -> str:
    v = (value or "").strip()
    if re.fullmatch(r"\d{8}", v):
        return f"{v[:4]}-{v[4:6]}-{v[6:]}"
    return v


def split_text(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    """Pack whole sentences into parts of at most max_chars (hard-splits a single over-long sentence)."""
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = []
    cur = ""
    for sent in _SENT_BREAK.split(text):
        while len(sent) > max_chars:  # table dumps and lists often have no sentence breaks
            if cur:
                parts.append(cur)
                cur = ""
            cut = sent.rfind(" ", 0, max_chars)
            if cut < max_chars // 2:
                cut = max_chars
            parts.append(sent[:cut].strip())
            sent = sent[cut:].lstrip()
        if not sent:
            continue
        if cur and len(cur) + 1 + len(sent) > max_chars:
            parts.append(cur)
            cur = sent
        else:
            cur = f"{cur} {sent}".strip()
    if cur:
        parts.append(cur)
    return _merge_tiny(parts)


def _merge_tiny(parts: list[str]) -> list[str]:
    """Fold any part shorter than MIN_CHARS into its neighbour (may exceed the limit slightly)."""
    merged: list[str] = []
    carry = ""
    for p in parts:
        p = f"{carry} {p}".strip() if carry else p
        carry = ""
        if len(p) < MIN_CHARS and merged:
            merged[-1] = f"{merged[-1]} {p}"
        elif len(p) < MIN_CHARS:
            carry = p  # leading tiny part: prepend to the next one
        else:
            merged.append(p)
    if carry:
        merged.append(carry)
    return merged


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def postprocess(chunks: list[Chunk], max_chars: int = MAX_CHARS) -> list[Chunk]:
    out: list[Chunk] = []
    counter: dict[tuple[str, str], int] = defaultdict(int)
    for c in chunks:
        if c.section in DROP_SECTIONS:
            continue
        drug = RENAME_DRUG.get(c.drug_name, c.drug_name).strip().lower()
        aliases = sorted({a.strip().lower() for a in [*c.aliases, *BRAND_ALIASES.get(drug, [])]} - {drug})
        for part in split_text(c.text, max_chars):
            key = (c.set_id or drug, c.section)
            k = counter[key]
            counter[key] += 1
            out.append(
                replace(
                    c,
                    chunk_id=f"{_slug(drug)}-{(c.set_id or 'noset')[:8]}-{_slug(c.section)}-{k}",
                    drug_name=drug,
                    aliases=aliases,
                    text=part,
                    effective_date=iso_date(c.effective_date),
                )
            )
    return out
