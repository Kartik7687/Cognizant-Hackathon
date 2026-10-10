
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from drugrag.eval import metrics as M  # noqa: E402

HERE = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", default=str(ROOT / "data" / "chunks_clean.jsonl"))
    ap.add_argument("--gold", default=str(HERE / "gold_set.json"))
    ap.add_argument("--out", default=str(HERE / "results"))
    ap.add_argument("--chars", type=int, default=900, help="label text characters shown per chunk")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    chunks = [json.loads(l) for l in open(args.chunks, encoding="utf-8") if l.strip()]
    gold = [g for g in json.loads(Path(args.gold).read_text(encoding="utf-8"))]

    by_drug = defaultdict(list)
    for c in chunks:
        by_drug[M.norm(c["drug_name"])].append(c)

    # ---- coverage matrix
    sections = sorted({c["section"] for c in chunks})
    with (out / "coverage.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["drug"] + sections)
        for d in sorted(by_drug):
            counts = [sum(1 for c in by_drug[d] if c["section"] == s) for s in sections]
            w.writerow([d] + counts)

    # ---- validate
    problems, review = [], []
    n_ok = 0
    for g in gold:
        if not g.get("answerable", True) or g.get("unsafe") or not g.get("gold_section"):
            continue
        ok_all = True
        review.append(f"## {g['id']}  [{g.get('type')}]  verified={g.get('verified')}\n"
                      f"**Q:** {g['question']}\n\n**Gold answer (yours):** {g.get('gold_answer')}\n")
        for d in M.as_list(g["drug"]):
            dn = M.norm(d)
            if dn not in by_drug:
                problems.append(f"- {g['id']}: drug '{d}' is NOT in the chunks file. Question: {g['question']}")
                ok_all = False
                continue
            match = [c for c in by_drug[dn]
                     if any(M.section_matches(c["section"], s) for s in M.as_list(g["gold_section"]))]
            if not match:
                have = sorted({c["section"] for c in by_drug[dn]})
                problems.append(f"- {g['id']}: '{d}' has no chunk in {M.as_list(g['gold_section'])}. "
                                f"Sections it does have: {have}. Question: {g['question']}")
                ok_all = False
                continue
            review.append(f"**Label text for {d} ({len(match)} chunk(s), showing first):**\n"
                          f"> section: {match[0]['section']}, version {match[0].get('version')}\n\n"
                          f"```\n{match[0]['text'][:args.chars]}\n```\n")
        n_ok += ok_all
        review.append("---\n")

    n_checked = sum(1 for g in gold if g.get("answerable", True) and not g.get("unsafe") and g.get("gold_section"))
    head = [f"# Gold set validation\n", f"Checked {n_checked} answerable questions: "
            f"**{n_ok} OK**, **{n_checked - n_ok} with problems**.\n"]
    (out / "gold_validation.md").write_text(
        "\n".join(head + (problems or ["All answerable questions have matching chunks."])), encoding="utf-8")
    (out / "gold_review.md").write_text("# Gold answer review (compare with real label text)\n\n"
                                        + "\n".join(review), encoding="utf-8")
    print("\n".join(head))
    print("\n".join(problems) if problems else "All answerable questions have matching chunks.")
    print(f"\nWrote: {out/'gold_validation.md'}\n       {out/'gold_review.md'}\n       {out/'coverage.csv'}")


if __name__ == "__main__":
    main()
