"""Write the mock chunks to data/mock_chunks.jsonl."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from drugrag.mock_data import mock_chunks  # noqa: E402
from drugrag.schema import save_chunks  # noqa: E402

if __name__ == "__main__":
    out = ROOT / "data" / "mock_chunks.jsonl"
    chunks = mock_chunks()
    save_chunks(chunks, out)
    print(f"wrote {len(chunks)} mock chunks to {out}")
