
"""Download official DailyMed drug label XML files."""

from pathlib import Path
from urllib.parse import quote
import time
import requests

BASE_URL = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
SEARCH_URL = "https://dailymed.nlm.nih.gov/dailymed/services/v1"

# Keep the original five IDs so existing downloads remain consistent.
EXISTING_DRUGS = {
    "warfarin": "ba8b4ead-d080-91e7-e053-2995a90a82fe",
    "metformin": "c82a10fa-1e8e-46b6-890a-737de3f34ee1",
    "lisinopril": "c57e8bc8-ff50-431e-9c1a-384503584d02",
    "amlodipine": "b6f298ba-2d7e-4a3c-9edb-8b60aba716d6",
    "atorvastatin": "595ab888-6b55-4642-a32f-e8521821ed81",
}

# 40 unique generic drug names in total.
DRUG_NAMES = [
    "warfarin",
    "metformin",
    "lisinopril",
    "amlodipine",
    "atorvastatin",
    "amoxicillin",
    "azithromycin",
    "ibuprofen",
    "acetaminophen",
    "omeprazole",
    "losartan",
    "hydrochlorothiazide",
    "levothyroxine",
    "albuterol",
    "sertraline",
    "gabapentin",
    "prednisone",
    "doxycycline",
    "cephalexin",
    "ciprofloxacin",
    "fluoxetine",
    "pantoprazole",
    "famotidine",
    "furosemide",
    "carvedilol",
    "metoprolol",
    "clopidogrel",
    "apixaban",
    "ondansetron",
    "lantus",
    "naproxen",
    "cetirizine",
    "loratadine",
    "montelukast",
    "escitalopram",
    "prednisolone",
    "enalapril",
    "spironolactone",
    "rosuvastatin",
    "valsartan",
]

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def find_set_id(drug_name, session):
    """Search DailyMed for a label and return its SPL set ID."""
    url = (
        f"{SEARCH_URL}/drugname/"
        f"{quote(drug_name, safe='')}/spls.json"
    )

    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        payload = response.json()

        # DailyMed responses may represent results as objects or
        # as COLUMNS/DATA arrays, so handle both forms.
        records = payload.get("data", [])

        if records and isinstance(records[0], dict):
            for record in records:
                set_id = (
                    record.get("spl_set_id")
                    or record.get("setid")
                    or record.get("set_id")
                )
                if set_id:
                    return str(set_id)

        columns = payload.get("COLUMNS", [])
        rows = payload.get("DATA", [])
        if columns and rows:
            normalized_columns = [
                str(column).lower() for column in columns
            ]
            for row in rows:
                record = dict(zip(normalized_columns, row))
                set_id = (
                    record.get("spl_set_id")
                    or record.get("setid")
                    or record.get("set_id")
                )
                if set_id:
                    return str(set_id)

        print(f"  No label found in search results for {drug_name}.")
        return None

    except (requests.RequestException, ValueError) as error:
        print(f"  Search failed for {drug_name}: {error}")
        return None


def download_label(drug_name, set_id, session):
    """Download one label's XML file."""
    url = f"{BASE_URL}/spls/{set_id}.xml"
    output_path = RAW_DIR / f"{drug_name.replace(' ', '_')}.xml"

    print(f"\nDownloading {drug_name}...")
    try:
        response = session.get(url, timeout=45)
        response.raise_for_status()

        # Avoid saving an error page instead of XML.
        if b"<" not in response.content[:500]:
            print(f"  Invalid XML response for {drug_name}.")
            return False

        RAW_DIR.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)

        print(f"  Saved: {output_path.name}")
        print(f"  Size: {len(response.content):,} bytes")
        return True

    except requests.RequestException as error:
        print(f"  Download failed for {drug_name}: {error}")
        return False


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    successful = 0
    failed = []

    print(f"Starting DailyMed download for {len(DRUG_NAMES)} drugs.")

    with requests.Session() as session:
        session.headers.update(
            {"User-Agent": "DrugDocumentationChatbot/1.0"}
        )

        for drug_name in DRUG_NAMES:
            # Use known IDs for the original five drugs.
            set_id = EXISTING_DRUGS.get(drug_name)

            # Find IDs automatically for the remaining drugs.
            if not set_id:
                print(f"\nSearching DailyMed for {drug_name}...")
                set_id = find_set_id(drug_name, session)
                time.sleep(0.2)

            if not set_id:
                failed.append(drug_name)
                continue

            if download_label(drug_name, set_id, session):
                successful += 1
            else:
                failed.append(drug_name)

            # Be considerate of the public service.
            time.sleep(0.2)

    print("\n" + "=" * 45)
    print(f"Downloads successful: {successful}/{len(DRUG_NAMES)}")
    print(f"Downloads failed: {len(failed)}")

    if failed:
        print("Please retry or investigate these drugs:")
        for drug_name in failed:
            print(f"  - {drug_name}")

    print(f"\nXML files are saved in: {RAW_DIR}")
    print("Download script finished.")


if __name__ == "__main__":
    main()
