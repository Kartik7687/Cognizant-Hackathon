
"""Download official DailyMed drug label XML files."""

from pathlib import Path
import requests

BASE_URL = "https://dailymed.nlm.nih.gov/dailymed/services/v2"


DRUGS = {
    "warfarin": "ba8b4ead-d080-91e7-e053-2995a90a82fe",
    "metformin": "c82a10fa-1e8e-46b6-890a-737de3f34ee1",
    "lisinopril": "c57e8bc8-ff50-431e-9c1a-384503584d02",
    "amlodipine": "b6f298ba-2d7e-4a3c-9edb-8b60aba716d6",
    "atorvastatin": "595ab888-6b55-4642-a32f-e8521821ed81",
}



RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def download_label(drug_name, set_id):
    url = f"{BASE_URL}/spls/{set_id}.xml"
    output_path = RAW_DIR / f"{drug_name}.xml"

    print(f"Downloading {drug_name}...")
    print(f"Request URL: {url}")

    try:
        response = requests.get(url, timeout=30)
        print(f"HTTP status: {response.status_code}")
        response.raise_for_status()

        # Confirm that the response contains XML.
        if b"<" not in response.content[:500]:
            print("Response does not look like XML. File not saved.")
            print(response.text[:300])
            return

        RAW_DIR.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)

        print(f"SUCCESS! Saved to: {output_path}")
        print(f"File size: {len(response.content)} bytes")

    except requests.RequestException as error:
        print(f"DOWNLOAD FAILED: {error}")


def main():
    print("DailyMed label downloader started.")
    for drug_name, set_id in DRUGS.items():
        download_label(drug_name, set_id)
    print("Download script finished.")


if __name__ == "__main__":
    main()
