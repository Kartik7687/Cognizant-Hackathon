"""Embed chunks and save an index.

    python scripts\\build_index.py --chunks data\\mock_chunks.jsonl --out index\\mock --embedder hash
    python scripts\\build_index.py --chunks data\\chunks.jsonl --out index\\bge-small --embedder bge-small
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drugrag.retrieval.embedder import get_embedder  # noqa: E402
from drugrag.retrieval.index import Index  # noqa: E402
from drugrag.schema import load_chunks  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chunks", required=True, help="chunks.jsonl produced by the data pipeline")
    ap.add_argument("--out", required=True, help="output index directory")
    ap.add_argument("--embedder", default="hash", help="hash | bge-small | bge-m3 | minilm | <hf model id>")
    args = ap.parse_args()

    chunks = load_chunks(args.chunks)
    print(f"loaded {len(chunks)} chunks, {len({c.drug_name for c in chunks})} drugs")
    embedder = get_embedder(args.embedder)
    t0 = time.time()
    index = Index.build(chunks, embedder)
    index.save(args.out)
    print(f"built index with '{embedder.name}' ({embedder.dim}-d) in {time.time() - t0:.1f}s -> {args.out}")


if __name__ == "__main__":
    main()
