"""Try retrieval from the command line (this is also the Checkpoint 1 demo).

    python scripts\\demo_retrieve.py --index index\\mock "contraindications of metformin"
    python scripts\\demo_retrieve.py --index index\\mock --compare "Can I take ibuprofen with warfarin?"
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drugrag.retrieval.retrieve import MODES, Retriever  # noqa: E402
from drugrag.schema import format_citation  # noqa: E402


def show(res, snippet: int) -> None:
    drugs = ", ".join(res.detected_drugs) or "none (no drug filter)"
    print(f"\n[{res.mode}]  detected drugs: {drugs}")
    for note in res.notes:
        print(f"  note: {note}")
    for h in res.hits:
        text = h.chunk.text.replace("\n", " ")
        print(f"  {h.rank}. score={h.score:.4f}  {format_citation(h.chunk)}")
        print(f"     {text[:snippet]}{'...' if len(text) > snippet else ''}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("queries", nargs="+")
    ap.add_argument("--index", required=True)
    ap.add_argument("--embedder", default=None, help="defaults to the one the index was built with")
    ap.add_argument("--reranker", default="none", help="none | bge-reranker-base | overlap (offline, lexical only)")
    ap.add_argument("--mode", default="hybrid", choices=MODES)
    ap.add_argument("--compare", action="store_true", help="show all four modes")
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--snippet", type=int, default=110)
    args = ap.parse_args()

    retriever = Retriever.from_dir(args.index, embedder=args.embedder, reranker=args.reranker)
    for q in args.queries:
        print(f"\n=== {q}")
        for mode in (MODES if args.compare else (args.mode,)):
            show(retriever.retrieve(q, mode=mode, top_k=args.top_k), args.snippet)


if __name__ == "__main__":
    main()
