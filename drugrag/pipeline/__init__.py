"""Data pipeline (owner: Shruti).

Contract: produce data/chunks.jsonl where every line is a drugrag.schema.Chunk as JSON
(drug_name lowercase generic, brand names in `aliases`, set_id/version/effective_date/section_code filled).
Build the index with:  python scripts\\build_index.py --chunks data\\chunks.jsonl --out index\\bge-small --embedder bge-small
"""
