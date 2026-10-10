r"""Clean an existing chunks.jsonl (stopgap until the parser itself is fixed).

    python scripts\postprocess_chunks.py --in data\chunks.jsonl --out data\chunks_clean.jsonl
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drugrag.pipeline.postprocess import MAX_CHARS, postprocess  # noqa: E402
from drugrag.schema import load_chunks, save_chunks, validate_chunks  # noqa: E402

CORE = ("indications", "dosage", "contraindications", "warnings", "adverse", "interactions")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-chars", type=int, default=MAX_CHARS)
    args = ap.parse_args()

    before = load_chunks(args.src)
    after = postprocess(before, args.max_chars)
    save_chunks(after, args.out)

    e0, w0 = validate_chunks(before)
    e1, w1 = validate_chunks(after)
    print(f"chunks: {len(before)} -> {len(after)}")
    print(f"validator before: {len(e0)} errors, {len(w0)} warnings")
    print(f"validator after:  {len(e1)} errors, {len(w1)} warnings")
    for m in e1[:10]:
        print("ERROR:", m)

    by_drug: dict[str, set[str]] = {}
    for c in after:
        by_drug.setdefault(c.drug_name, set()).add(c.section.lower())
    weak = []
    for d, secs in sorted(by_drug.items()):
        hit = [k for k in CORE if any(k in s for s in secs)]
        if len(hit) < 3:
            weak.append(f"{d} ({len(hit)}/6 core sections)")
    if weak:
        print("\nNEEDS ATTENTION (fewer than 3 of 6 core sections, so answers will be missing or wrong):")
        print("  " + "\n  ".join(weak))
    print("\nchunk length after:", sorted(len(c.text) for c in after)[len(after) // 2], "median,",
          max(len(c.text) for c in after), "max")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
