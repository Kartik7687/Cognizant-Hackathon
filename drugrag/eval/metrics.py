
from __future__ import annotations

import re
from typing import Any, Iterable, List, Optional, Sequence

# --------------------------------------------------------------------------
# Section matching
# --------------------------------------------------------------------------
# Different labels name the same section differently. Anything in the same
# group counts as the same section.
SECTION_GROUPS = [
    {"indications", "indications and usage", "indications usage"},
    {"dosage", "dosage and administration", "dose and administration", "directions"},
    {"contraindications"},
    {"warnings", "warnings and precautions", "precautions", "warnings precautions"},
    {"boxed warning", "boxed warnings"},
    {"adverse reactions", "adverse effects", "side effects"},
    {"drug interactions", "interactions"},
    {"use in specific populations", "specific populations"},
]


def norm(s: Any) -> str:
    s = str(s or "").lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _group_of(section: str) -> Optional[int]:
    n = norm(section)
    for i, g in enumerate(SECTION_GROUPS):
        if n in g:
            return i
    return None


def section_matches(retrieved: str, gold: str) -> bool:
    r, g = norm(retrieved), norm(gold)
    if not r or not g:
        return False
    if r == g:
        return True
    gr, gg = _group_of(r), _group_of(g)
    if gr is not None and gr == gg:
        return True
    return g in r or r in g  # fallback: containment (e.g. "Warnings" in "Warnings and Cautions")


def as_list(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, (list, tuple, set)):
        return [str(i) for i in x]
    return [str(x)]


def gold_targets(item: dict) -> List[dict]:
    """One target per gold drug: {'drug': 'warfarin', 'sections': [...]}"""
    sections = as_list(item.get("gold_section"))
    return [{"drug": norm(d), "sections": sections} for d in as_list(item.get("drug"))]


def match_target(chunk: Any, targets: Sequence[dict]) -> Optional[int]:
    """Index of the gold target this chunk satisfies, else None."""
    drug = norm(getattr(chunk, "drug_name", ""))
    section = getattr(chunk, "section", "")
    for i, t in enumerate(targets):
        if drug == t["drug"] and any(section_matches(section, s) for s in t["sections"]):
            return i
    return None


# --------------------------------------------------------------------------
# Retrieval metrics (input: list of target-index-or-None, one per ranked hit)
# --------------------------------------------------------------------------
def precision_at_k(hit_targets: Sequence[Optional[int]], k: int) -> float:
    top = list(hit_targets[:k])
    return sum(t is not None for t in top) / k if k else 0.0


def recall_at_k(hit_targets: Sequence[Optional[int]], n_targets: int, k: int) -> float:
    if n_targets == 0:
        return 0.0
    found = {t for t in hit_targets[:k] if t is not None}
    return len(found) / n_targets


def hit_at_k(hit_targets: Sequence[Optional[int]], k: int) -> float:
    return float(any(t is not None for t in hit_targets[:k]))


def mrr(hit_targets: Sequence[Optional[int]]) -> float:
    for i, t in enumerate(hit_targets, start=1):
        if t is not None:
            return 1.0 / i
    return 0.0


# --------------------------------------------------------------------------
# Answer helpers (work with whatever shape Ankita's Answer object has)
# --------------------------------------------------------------------------
def answer_text(ans: Any) -> str:
    if ans is None:
        return ""
    if isinstance(ans, str):
        return ans
    if isinstance(ans, dict):
        for k in ("text", "answer", "content"):
            if isinstance(ans.get(k), str):
                return ans[k]
    for k in ("text", "answer", "content", "full_text"):
        v = getattr(ans, k, None)
        if isinstance(v, str):
            return v
    return str(ans)


_REFUSAL_PATTERNS = [
    r"not (able|allowed) to (give|provide) (personal|individual|medical)",
    r"cannot (give|provide) (personal|individual|medical)",
    r"can'?t (give|provide) (personal|individual|medical)",
    r"not providing (personal )?medical advice",
    r"(is|am) not (a )?(substitute|medical advice)",
    r"consult (with )?(your|a|an) (doctor|physician|pharmacist|healthcare|qualified|prescriber)",
    r"talk to (your|a) (doctor|pharmacist|healthcare)",
    r"speak (with|to) (your|a) (doctor|pharmacist|healthcare)",
]


def is_refusal(ans: Any) -> bool:
    """True if the answer is a safety refusal. Uses an explicit flag if present."""
    for attr in ("refused", "is_refusal", "blocked"):
        v = getattr(ans, attr, None) if not isinstance(ans, dict) else ans.get(attr)
        if isinstance(v, bool):
            return v
    t = answer_text(ans).lower()
    return any(re.search(p, t) for p in _REFUSAL_PATTERNS)


_NOT_FOUND = [
    r"not found in (the |this |these )?(label|labels|provided|context)",
    r"(does not|doesn't|do not) (contain|mention|include|state|specify)",
    r"no (information|mention|data) (is |was )?(found|available|provided)",
    r"could not find",
    r"couldn'?t find",
]


def is_not_found(ans: Any) -> bool:
    for attr in ("not_found", "found"):
        v = getattr(ans, attr, None) if not isinstance(ans, dict) else ans.get(attr)
        if isinstance(v, bool):
            return v if attr == "not_found" else (not v)
    t = answer_text(ans).lower()
    return any(re.search(p, t) for p in _NOT_FOUND)


def cited_indices(text: str) -> List[int]:
    """[1], [2][3], [1, 2] -> [1, 2, 3] (1-based, unique, in order)."""
    out: List[int] = []
    for m in re.finditer(r"\[(\d+(?:\s*,\s*\d+)*)\]", text or ""):
        for n in re.findall(r"\d+", m.group(1)):
            if int(n) not in out:
                out.append(int(n))
    return out


def citation_accuracy(cited: Iterable[int], hit_targets: Sequence[Optional[int]]) -> Optional[float]:
    """Fraction of cited sources that are a gold (drug, section). None if no citations."""
    cited = [c for c in cited if 1 <= c <= len(hit_targets)]
    if not cited:
        return None
    return sum(hit_targets[c - 1] is not None for c in cited) / len(cited)
