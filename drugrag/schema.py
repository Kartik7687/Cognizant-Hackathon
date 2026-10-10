"""Shared chunk schema and citation helper. Every module codes against this."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Iterable


@dataclass
class Chunk:
    """One label section (or part of a long section) plus citation metadata."""

    chunk_id: str                 # unique, e.g. "metformin-<set_id>-contraindications-0"
    drug_name: str                # canonical generic name, lowercase, e.g. "metformin"
    section: str                  # human readable, e.g. "Contraindications"
    text: str                     # the passage that gets embedded and quoted
    aliases: list[str] = field(default_factory=list)  # brand names, e.g. ["glucophage"]
    set_id: str = ""              # DailyMed set id (stable id of the label)
    version: str = ""             # label version number
    effective_date: str = ""      # ISO date, e.g. "2024-05-01"
    section_code: str = ""         # LOINC code of the SPL section, e.g. "34070-3"
    page: str = "N/A"             # XML labels have no pages -> "N/A"; PDFs -> page number
    source_url: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Chunk":
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in names})


def load_chunks(path: str | Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(Chunk.from_dict(json.loads(line)))
    return chunks


def save_chunks(chunks: Iterable[Chunk], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")


def format_citation(c: Chunk) -> str:
    """Mentor's required Sources format: drug name, label version, section, page, effective date."""
    return (
        f"{c.drug_name.title()}, label version {c.version or 'n/a'}, "
        f"{c.section}, page {c.page or 'N/A'}, effective {c.effective_date or 'n/a'}"
    )


# --------------------------------------------------------------------------- validation
import re as _re

_DATE = _re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_CHUNK_CHARS = 1800   # bge-small truncates around 512 tokens (~2000 chars); longer text is silently cut
MIN_CHUNK_CHARS = 40


def validate_chunks(chunks: list[Chunk]) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Errors break retrieval or citations; warnings hurt quality."""
    errors: list[str] = []
    warns: list[str] = []
    seen: dict[str, int] = {}
    texts: dict[str, str] = {}
    for n, c in enumerate(chunks, start=1):
        tag = f"#{n} {c.chunk_id or '<no id>'}"
        if not c.chunk_id:
            errors.append(f"{tag}: empty chunk_id")
        elif c.chunk_id in seen:
            errors.append(f"{tag}: duplicate chunk_id (first seen at #{seen[c.chunk_id]})")
        else:
            seen[c.chunk_id] = n
        if not c.drug_name or c.drug_name != c.drug_name.strip().lower():
            errors.append(f"{tag}: drug_name must be non-empty, lowercase, stripped (got {c.drug_name!r})")
        if not c.section.strip():
            errors.append(f"{tag}: empty section")
        if not c.text.strip():
            errors.append(f"{tag}: empty text")
        elif len(c.text) < MIN_CHUNK_CHARS:
            warns.append(f"{tag}: very short text ({len(c.text)} chars)")
        elif len(c.text) > MAX_CHUNK_CHARS:
            warns.append(f"{tag}: long text ({len(c.text)} chars); split it or bge-small will truncate it")
        if c.aliases != [a.strip().lower() for a in c.aliases]:
            warns.append(f"{tag}: aliases should be lowercase and stripped")
        for fld in ("set_id", "version", "section_code"):
            if not getattr(c, fld):
                warns.append(f"{tag}: {fld} is empty (needed for the Sources line)")
        if not c.effective_date:
            warns.append(f"{tag}: effective_date is empty (needed for the Sources line)")
        elif not _DATE.match(c.effective_date):
            errors.append(f"{tag}: effective_date must be YYYY-MM-DD (got {c.effective_date!r})")
        if c.page != "N/A" and not str(c.page).isdigit():
            errors.append(f"{tag}: page must be 'N/A' or a page number (got {c.page!r})")
        key = c.text.strip().lower()
        if key and key in texts and texts[key] != c.chunk_id:
            warns.append(f"{tag}: identical text to {texts[key]} (duplicate labels? keep one label per drug)")
        texts.setdefault(key, c.chunk_id)
    return errors, warns
