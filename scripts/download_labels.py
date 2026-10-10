
"""Download official DailyMed drug label XML files."""

from pathlib import Path
from urllib.parse import quote
import time
import requests
import xml.etree.ElementTree as ET

BASE_URL = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
SEARCH_URL = "https://dailymed.nlm.nih.gov/dailymed/services/v1"

# Keep the original five IDs so existing downloads remain consistent.
EXISTING_DRUGS = {
    "warfarin": "ba8b4ead-d080-91e7-e053-2995a90a82fe",
    "metformin": "c82a10fa-1e8e-46b6-890a-737de3f34ee1",
    "lisinopril": "c57e8bc8-ff50-431e-9c1a-384503584d02",
    "amlodipine": "b6f298ba-2d7e-4a3c-9edb-8b60aba716d6",
    "atorvastatin": "595ab888-6b55-4642-a32f-e8521821ed81",
    "levothyroxine": "8bc641d8-0185-49b2-9c1f-d886bf5ce098",
    "lantus": "5328761e-59d3-ca7a-e063-6394a90ae810",
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
def local_name(tag):
    """Return an XML tag without its namespace."""
    return tag.split("}")[-1].lower()


def find_set_id(drug_name, session):
    """Find the best human prescription label from multiple candidates."""
    search_name = (
        "insulin glargine" if drug_name.lower() == "lantus"
        else drug_name
    )

    url = f"{BASE_URL}/spls.json"

    try:
        response = session.get(
    url,
    params={
        "drug_name": search_name,
        "page": 1,
        "pagesize": 20,
    },
    timeout=30,
)
        response.raise_for_status()
        payload = response.json()

        records = payload.get("data", [])

        # Support DailyMed responses represented as COLUMNS/DATA.
        records = payload.get("data", [])

# Handle DailyMed's COLUMNS/DATA response format.
        if not records and payload.get("COLUMNS") and payload.get("DATA"):
            
            records = [
            dict(zip(payload["COLUMNS"], row))
            for row in payload["DATA"]
            ]  

# Normalize the response into a list of dictionaries.
        if isinstance(records, dict):
            records = [records]

        candidates = []
        seen_ids = set()

        for record in records:
            if not isinstance(record, dict):
                continue

            normalized = {
                str(key).lower(): value
                for key, value in record.items()
            }

            set_id = (
                normalized.get("spl_set_id")
                or normalized.get("setid")
                or normalized.get("set_id")
            )

            if not set_id or str(set_id) in seen_ids:
                continue

            seen_ids.add(str(set_id))
            candidates.append(str(set_id))

        if not candidates:
            print(f"  No candidates found for {search_name}.")
            return None

        # Inspect several candidate XML labels and score their sections.
        required_codes = {
            "34067-9",  # Indications
            "34068-7",  # Dosage
            "34070-3",  # Contraindications
            "43685-7",  # Warnings and precautions
            "34084-4",  # Adverse reactions
            "34073-7",  # Drug interactions
        }

        best_id = None
        best_score = -1

        for candidate_id in candidates[:10]:
            try:
                xml_response = session.get(
                    f"{BASE_URL}/spls/{candidate_id}.xml",
                    timeout=45,
                )
                xml_response.raise_for_status()
                root = ET.fromstring(xml_response.content)

                found_codes = set()
                for element in root.iter():
                    if local_name(element.tag) == "section":
                        for child in element:
                            if local_name(child.tag) == "code":
                                code = child.attrib.get("code", "").strip()
                                if code in required_codes:
                                    found_codes.add(code)

                score = len(found_codes)
                print(
                    f"  Candidate {candidate_id}: "
                    f"{score}/6 required section types"
                )

                if score > best_score:
                    best_score = score
                    best_id = candidate_id

                if score == len(required_codes):
                    break

            except (requests.RequestException, ET.ParseError) as error:
                print(f"  Could not inspect candidate {candidate_id}: {error}")

            time.sleep(0.2)

        if best_id is not None and best_score > 0:
            print(
                f"  Selected label {best_id} "
                f"with {best_score}/6 required section types."
            )
            return best_id
        print(f"  No usable label found for {search_name}.")
        return None

    except (requests.RequestException, ValueError) as error:
        print(f"  Search failed for {search_name}: {error}")
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
