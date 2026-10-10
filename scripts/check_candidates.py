
import time
import requests
import xml.etree.ElementTree as ET

BASE_URL = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json"

REQUIRED_CODES = {
    "34067-9",  # Indications and Usage
    "34068-7",  # Dosage and Administration
    "34070-3",  # Contraindications
    "43685-7",  # Warnings and Precautions
    "34084-4",  # Adverse Reactions
    "34073-7",  # Drug Interactions
}


def local_name(tag):
    return tag.split("}")[-1].lower()


def get_codes(session, set_id):
    url = (
        "https://dailymed.nlm.nih.gov/dailymed/services/v2/"
        f"spls/{set_id}.xml"
    )
    response = session.get(url, timeout=60)
    response.raise_for_status()
    root = ET.fromstring(response.content)

    codes = set()
    for section in root.iter():
        if local_name(section.tag) == "section":
            for child in section:
                if local_name(child.tag) == "code":
                    code = child.attrib.get("code", "").strip()
                    if code in REQUIRED_CODES:
                        codes.add(code)

    return codes


def check_drug(session, drug_name, search_name=None):
    search_name = search_name or drug_name
    print(f"\n{'=' * 60}\nDrug: {drug_name}\n{'=' * 60}")

    response = session.get(
        BASE_URL,
        params={"drug_name": search_name, "page": 1, "pagesize": 20},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    columns = payload.get("columns", payload.get("COLUMNS", []))
    rows = payload.get("data", payload.get("DATA", []))

    if rows and isinstance(rows[0], list) and columns:
        candidates = [dict(zip(columns, row)) for row in rows]
    else:
        candidates = rows

    if not candidates:
        print("No candidates returned by DailyMed.")
        return

    results = []
    seen = set()

    for item in candidates:
        if not isinstance(item, dict):
            continue

        title = item.get("title", item.get("TITLE", ""))
        set_id = (
            item.get("setid")
            or item.get("SETID")
            or item.get("spl_set_id")
            or item.get("set_id")
        )

        if not set_id or set_id in seen:
            continue
        seen.add(set_id)

        if any(word in title.upper() for word in (
            "REMEDYREPACK", "REPACKAGER"
        )):
            print(f"Skipping likely repackager: {title}")
            continue

        try:
            codes = get_codes(session, set_id)
            score = len(codes & REQUIRED_CODES)
            results.append((score, title, set_id))
            print(f"{score}/6 | {title}\nSet ID: {set_id}")
        except (requests.RequestException, ET.ParseError) as error:
            print(f"Could not inspect {set_id}: {error}")

        time.sleep(0.2)

    if results:
        results.sort(key=lambda result: result[0], reverse=True)
        print("\nRanked candidates (highest section count first):")
        for score, title, set_id in results:
            print(f"{score}/6 | {title} | {set_id}")
        print("\nBest section-count candidate:")
        print(results[0][1])
        print("Set ID:", results[0][2])
        print("Section score:", results[0][0], "/6")
    else:
        print("No usable candidates could be inspected.")


with requests.Session() as session:
    check_drug(session, "levothyroxine")
    check_drug(session, "lantus", "Lantus")
