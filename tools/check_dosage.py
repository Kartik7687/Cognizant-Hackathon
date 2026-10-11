
import json
from pathlib import Path

path = Path("data/chunks.jsonl")
drugs = {"apixaban", "atorvastatin"}

for drug in sorted(drugs):
    print(f"\nDrug: {drug}")
    count = 0

    with path.open(encoding="utf-8") as file:
        for line in file:
            chunk = json.loads(line)

            if (
                chunk.get("drug_name", "").lower() == drug
                and chunk.get("section_code") == "34068-7"
            ):
                print(
                    "Dosage section found:",
                    chunk.get("section"),
                    "| Chunk:",
                    chunk.get("chunk_id"),
                )
                count += 1

    print("Dosage chunks:", count)
