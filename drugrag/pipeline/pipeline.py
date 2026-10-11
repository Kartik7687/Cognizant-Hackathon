
"""Run the DailyMed drug-documentation data pipeline."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run_step(description, script, *args):
    print(f"\n{'=' * 50}", flush=True)
    print(description, flush=True)
    print("=" * 50, flush=True)

    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *args],
        cwd=ROOT,
        check=True,
    )


def main():
    # Step 1: Download the drug labels.
    run_step(
        "Step 1: Download DailyMed labels",
        "download_labels.py",
    )

    # Step 2: Build the raw chunks.
    run_step(
        "Step 2: Build JSONL chunks",
        "build_chunks.py",
    )

    raw_file = ROOT / "data" / "chunks.jsonl"
    clean_file = ROOT / "data" / "chunks_clean.jsonl"

    if not raw_file.exists():
        raise FileNotFoundError(f"Raw chunks not found: {raw_file}")

    # Step 3: Clean and standardize the chunks.
    run_step(
        "Step 3: Post-process chunks",
        "postprocess_chunks.py",
        "--in", str(raw_file),
        "--out", str(clean_file),
        "--max-chars", "1500",
    )

    if not clean_file.exists():
        raise FileNotFoundError(
            f"Cleaned chunks not found: {clean_file}"
        )

    # Step 4: Validate the cleaned dataset.
    run_step(
        "Step 4: Validate cleaned chunks",
        "validate_chunks.py",
        str(clean_file),
    )

    print("\nPipeline completed successfully!", flush=True)
    print(f"Clean dataset: {clean_file}", flush=True)


if __name__ == "__main__":
    main()
