r"""Check a chunks.jsonl against the schema before building an index.

    python scripts\validate_chunks.py data\chunks.jsonl
Exit code is 1 if there are errors, so it can gate the pipeline.
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drugrag.schema import load_chunks, validate_chunks  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("chunks")
    ap.add_argument("--max-show", type=int, default=15, help="max messages to print per level")
    args = ap.parse_args()

    chunks = load_chunks(args.chunks)
    errors, warns = validate_chunks(chunks)
    drugs = Counter(c.drug_name for c in chunks)
    sections = Counter(c.section for c in chunks)
    lengths = sorted(len(c.text) for c in chunks)
    print(f"{len(chunks)} chunks, {len(drugs)} drugs, {len(sections)} distinct sections")
    if lengths:
        print(f"chunk length (chars): min {lengths[0]}, median {lengths[len(lengths) // 2]}, max {lengths[-1]}")
    print("sections:", ", ".join(f"{s} ({n})" for s, n in sections.most_common(12)))
    for label, msgs in (("ERROR", errors), ("WARN", warns)):
        for m in msgs[: args.max_show]:
            print(f"{label}: {m}")
        if len(msgs) > args.max_show:
            print(f"{label}: ... and {len(msgs) - args.max_show} more")
    print(f"\n{len(errors)} errors, {len(warns)} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
