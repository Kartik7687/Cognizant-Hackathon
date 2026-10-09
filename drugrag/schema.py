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
