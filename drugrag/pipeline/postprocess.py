
"""Clean and split existing drug documentation chunks."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import replace

from ..schema import Chunk
from .aliases import BRAND_ALIASES, RENAME_DRUG

MAX_CHARS = 1500
MIN_CHARS = 40
DROP_SECTIONS = {"Principal Display Panel"}

_SENT_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\[(•])")


def iso_date(value: str) -> str:
    value = (value or "").strip()
    if re.fullmatch(r"\d{8}", value):
        return f"{value[:4]}-{value[4:6]}-{value[6:]}"
    return value


def split_text(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    """Split text into non-empty chunks within the character limit."""
    text = (text or "").strip()
    if not text or max_chars < 1:
        return []

    parts: list[str] = []
    current = ""

    for sentence in _SENT_BREAK.split(text):
        sentence = sentence.strip()
        if not sentence:
            continue

        while len(sentence) > max_chars:
            if current:
                parts.append(current)
                current = ""

            cut = sentence.rfind(" ", 0, max_chars + 1)
            if cut <= 0:
                cut = max_chars

            parts.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()

        if not sentence:
            continue

        if current and len(current) + 1 + len(sentence) > max_chars:
            parts.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()

    if current:
        parts.append(current)

    return _merge_tiny(parts, max_chars)


def _merge_tiny(
    parts: list[str], max_chars: int = MAX_CHARS
) -> list[str]:
    """Merge short fragments into a neighbour without exceeding max_chars."""
    parts = [(p or "").strip() for p in parts]
    parts = [p for p in parts if p]

    # Tiny fragments merge backwards into the previous part when it fits.
    merged: list[str] = []
    for part in parts:
        if merged and len(part) < MIN_CHARS:
            combined = f"{merged[-1]} {part}"
            if len(combined) <= max_chars:
                merged[-1] = combined
                continue
        merged.append(part)

    # A tiny fragment that cannot merge whole is rebalanced with its
    # neighbour by moving the cut to a word boundary near the middle.
    i = 0
    while i < len(merged):
        if len(merged[i]) < MIN_CHARS and len(merged) >= 2:
            j = i + 1 if i + 1 < len(merged) else i - 1
            a, b = sorted((i, j))
            combined = f"{merged[a]} {merged[b]}"
            if len(combined) <= max_chars:
                merged[a:b + 1] = [combined]
                i = max(a, 0)
                continue
            cut = _balanced_cut(combined, max_chars)
            if cut:
                merged[a], merged[b] = combined[:cut].strip(), combined[cut:].strip()
        i += 1

    return merged


def _balanced_cut(text: str, max_chars: int) -> int:
    """Space index closest to the middle that leaves both halves valid, or 0."""
    best, best_gap = 0, None
    for m in re.finditer(r"\s", text):
        k = m.start()
        left, right = k, len(text) - k - 1
        if MIN_CHARS <= left <= max_chars and MIN_CHARS <= right <= max_chars:
            gap = abs(left - right)
            if best_gap is None or gap < best_gap:
                best, best_gap = k, gap
    return best


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def postprocess(
    chunks: list[Chunk], max_chars: int = MAX_CHARS
) -> list[Chunk]:
    out: list[Chunk] = []
    counter: dict[tuple[str, str], int] = defaultdict(int)

    for chunk in chunks:
        if chunk.section in DROP_SECTIONS:
            continue

        original_drug = (chunk.drug_name or "").strip().lower()
        drug = RENAME_DRUG.get(original_drug, original_drug).strip().lower()

        aliases = sorted({
            alias.strip().lower()
            for alias in [
                *(chunk.aliases or []),
                *BRAND_ALIASES.get(drug, []),
            ]
            if alias and alias.strip()
        } - {drug})

        if not (chunk.text or "").strip():
            continue

        parts = split_text(chunk.text, max_chars)

        # Discard short fragments only if they can be merged safely.
        if len(parts) >= 2 and len(parts[-1]) < MIN_CHARS:
            combined = f"{parts[-2]} {parts[-1]}"
            if len(combined) <= max_chars:
                parts[-2] = combined
                parts.pop()

        for part in parts:
            part = (part or "").strip()

            # Never save empty chunks.
            if not part:
                continue

            # A tiny fragment must not become a standalone chunk.
            if len(part) < MIN_CHARS:
                continue

            key = (chunk.set_id or drug, chunk.section)
            index = counter[key]
            counter[key] += 1

            out.append(
                replace(
                    chunk,
                    chunk_id=(
                        f"{_slug(drug)}-"
                        f"{(chunk.set_id or 'noset')[:8]}-"
                        f"{_slug(chunk.section)}-{index}"
                    ),
                    drug_name=drug,
                    aliases=aliases,
                    text=part,
                    effective_date=iso_date(chunk.effective_date),
                )
            )

    return out
