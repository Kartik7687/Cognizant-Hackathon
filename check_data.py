import json, collections as c
rows = [json.loads(l) for l in open("data/chunks_clean.jsonl", encoding="utf-8")]
print(len(rows), "chunks")
print("Fields:", list(rows[0].keys()))
print("\nDrugs:", sorted({r["drug_name"] for r in rows}))
print("\nSections:")
for s, n in c.Counter(r["section"] for r in rows).most_common():
    print(f"  {n:4d}  {s}")