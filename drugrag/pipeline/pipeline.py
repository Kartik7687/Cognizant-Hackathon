
"""Run the DailyMed drug-documentation data pipeline."""

import subprocess
import sys
from pathlib import Path

# Project root: the folder containing drugrag, scripts, and data.
ROOT = Path(__file__).resolve().parents[2]


def run_step(description, script):
    print(f"\n{'=' * 50}", flush=True)
    print(description, flush=True)
    print("=" * 50, flush=True)

    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)],
        cwd=ROOT,
        check=True,
    )


def main():
    run_step("Step 1: Download DailyMed labels", "download_labels.py")
    run_step("Step 2: Build JSONL chunks", "build_chunks.py")

    output_file = ROOT / "data" / "chunks.jsonl"
    if not output_file.exists():
        raise FileNotFoundError(f"Expected output not found: {output_file}")

    print(f"\nPipeline completed successfully!", flush=True)
    print(f"Output: {output_file}", flush=True)


if __name__ == "__main__":
    main()
