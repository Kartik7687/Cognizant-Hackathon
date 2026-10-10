# Chunk schema (v2): the contract between all four modules

One chunk = one passage from one label section. `data\chunks.jsonl` holds one JSON object per line.
Defined in `drugrag/schema.py`; check any file with `python scripts\validate_chunks.py data\chunks.jsonl`.

## Fields

| Field | Required | Type | Example | Used by |
|---|---|---|---|---|
| `chunk_id` | yes | str, unique | `metformin-1a2b3c4d-contraindications-0` | eval gold set, citations |
| `drug_name` | yes | str, lowercase generic | `metformin` | drug filter, Sources |
| `aliases` | no | list[str], lowercase | `["glucophage"]` | drug detection (brand names) |
| `section` | yes | str | `Contraindications` | section boost, Sources |
| `section_code` | yes* | str (LOINC) | `34070-3` | Sources, eval |
| `text` | yes | str | passage text | embedding, BM25, LLM context |
| `set_id` | yes* | str | DailyMed set id | Sources, dedupe |
| `version` | yes* | str | `12` | Sources ("label version") |
| `effective_date` | yes* | `YYYY-MM-DD` | `2024-05-01` | Sources |
| `page` | no | `"N/A"` or digits | `N/A` (XML), `7` (PDF) | Sources |
| `source_url` | no | str | DailyMed link | UI "view label" |

\* Not needed for retrieval to run, but the mentor's Sources line is `drug name, label version, section, page,
effective date`, so the validator warns when they are empty.

## Example line

```json
{"chunk_id": "metformin-1a2b3c4d-contraindications-0", "drug_name": "metformin", "aliases": ["glucophage"], "section": "Contraindications", "section_code": "34070-3", "text": "Metformin is contraindicated in patients with severe renal impairment (eGFR below 30 mL/min/1.73 m2)...", "set_id": "1a2b3c4d-0000-0000-0000-000000000000", "version": "12", "effective_date": "2024-05-01", "page": "N/A", "source_url": "https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=1a2b3c4d-0000-0000-0000-000000000000"}
```

## Rules for the data pipeline (Shruti)

1. **`drug_name`**: lowercase generic name without the salt ("metformin", not "Metformin Hydrochloride"). Combination
   products join generics with " and " ("amoxicillin and clavulanate potassium" becomes `amoxicillin and clavulanate`).
   Put brand names and the salt form in `aliases`. One spelling per drug across the whole file, because the drug filter
   matches on it exactly.
2. **One label per drug.** DailyMed has many near-identical manufacturer labels per drug. Keep the latest human
   prescription label for each drug; otherwise the top results fill up with duplicate passages. The validator warns on
   identical text.
3. **Chunk by section**, using the SPL section LOINC codes: Indications `34067-9`, Dosage and Administration `34068-7`,
   Contraindications `34070-3`, Warnings and Precautions `43685-7`, Adverse Reactions `34084-4`, Drug Interactions `34073-7`.
   Also worth keeping: Boxed Warning `34066-1`, Use in Specific Populations `43684-0`, Overdosage `34088-5`,
   Clinical Pharmacology `34090-1`.
4. **Keep chunks under about 1,800 characters.** `bge-small` cuts input at roughly 512 tokens, so longer text is
   silently truncated and the dropped part can never be retrieved. Split long sections (Adverse Reactions often is)
   at paragraph or sub-section boundaries into `...-0`, `...-1`, ... with the same `section`. Repeat the sub-section
   heading at the start of each part. Do not make chunks shorter than 40 characters.
5. **`chunk_id`** = `{drug_name}-{set_id first 8 chars}-{section slug}-{part number}`. It must be unique and stable
   across re-runs, because Akansha's gold set refers to it.
6. **Tables** (dosing tables, adverse reaction rates): convert each row to a sentence or keep the table as plain
   text with column headers repeated, so numbers stay attached to their meaning.
7. **`page`**: `"N/A"` for XML. Only PDF-derived chunks get a number.
8. Plain text only: strip XML tags, footnote markers and repeated whitespace.

## Changes from v1

Added `set_id`, `version`, `effective_date`, `section_code`, `page`, `source_url`, `aliases` and the validator.
Nothing was removed, so mock data and tests keep working.

## Checking your output

```
python scripts\validate_chunks.py data\chunks.jsonl
```

It prints counts and chunk-length stats, then errors (must fix: duplicate ids, non-lowercase drug names, bad dates,
empty text) and warnings (should fix: missing version/date, over-long or duplicate text). Exit code 1 means errors.
