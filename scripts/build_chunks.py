
"""Parse DailyMed XML labels into drugrag Chunk records."""

from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from drugrag.schema import Chunk, save_chunks

RAW_DIR = ROOT / "data" / "raw"
OUTPUT_FILE = ROOT / "data" / "chunks.jsonl"
SET_IDS = {
    "warfarin": "ba8b4ead-d080-91e7-e053-2995a90a82fe",
    "metformin": "c82a10fa-1e8e-46b6-890a-737de3f34ee1",
    "lisinopril": "c57e8bc8-ff50-431e-9c1a-384503584d02",
    "amlodipine": "b6f298ba-2d7e-4a3c-9edb-8b60aba716d6",
    "atorvastatin": "595ab888-6b55-4642-a32f-e8521821ed81",
}
BRAND_ALIASES = {
    "warfarin": ["Coumadin", "Jantoven"],
    "metformin": ["Glucophage", "Fortamet", "Glumetza"],
    "lisinopril": ["Zestril", "Prinivil"],
    "amlodipine": ["Norvasc"],
    "atorvastatin": ["Lipitor"],
}

TARGET_SECTIONS = {
    "INDICATIONS AND USAGE": "Indications and Usage",
    "DOSAGE AND ADMINISTRATION": "Dosage and Administration",
    "CONTRAINDICATIONS": "Contraindications",
    "WARNINGS AND PRECAUTIONS": "Warnings and Precautions",
    "ADVERSE REACTIONS": "Adverse Reactions",
    "DRUG INTERACTIONS": "Drug Interactions",
    "USE IN SPECIFIC POPULATIONS": "Use in Specific Populations",
}


def local_name(tag):
    return tag.split("}")[-1].lower()


def text_of(element):
    return " ".join(" ".join(element.itertext()).split())


def parse_label(xml_path):
    root = ET.parse(xml_path).getroot()

    set_id = SET_IDS.get(xml_path.stem.lower(), "")
    version = ""
    effective_date = ""

    for elem in root.iter():
        name = local_name(elem.tag)

        if name == "setid" and not set_id:
            set_id = (elem.text or "").strip()

        elif name == "versionnumber" and not version:
            version = (
                elem.attrib.get("value", "").strip()
                or (elem.text or "").strip()
            )

        elif name == "effectivetime" and not effective_date:
            effective_date = (
                elem.attrib.get("value", "").strip()
                or (elem.text or "").strip()
            )

    # Use the official DailyMed label page when a Set ID is available.
    source_url = (
        f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}"
        if set_id else ""
    )

    chunks = []
    seen = set()

    # In SPL XML, each section usually has a <section> element
    # containing a <title> and its narrative content.
    for section in root.iter():
        if local_name(section.tag) != "section":
            continue

        title_element = next(
            (child for child in section.iter()
             if local_name(child.tag) == "title"),
            None,
        )
        if title_element is None:
            continue

        title = text_of(title_element).upper().strip()
        title = re.sub(r"^\d+\s+", "", title)
        section_name = TARGET_SECTIONS.get(title)
        if not section_name:
            continue

        content_parts = []
        for child in section:
            if child is title_element:
                continue
            content = text_of(child)
            if content:
                content_parts.append(content)

        full_text = re.sub(r"\s+", " ", " ".join(content_parts)).strip()

        if len(full_text) < 40 or (section_name, full_text) in seen:
            continue
        seen.add((section_name, full_text))

        chunks.append(
            Chunk(
                chunk_id=f"{set_id or xml_path.stem}-{len(chunks) + 1}",
                drug_name=xml_path.stem.lower(),
                section=section_name,
                text=full_text,
                aliases=BRAND_ALIASES.get(xml_path.stem.lower(), []),
                set_id=set_id,
                version=version,
                effective_date=effective_date,
                section_code=title,
                page="N/A",
                source_url=source_url,
                
            )
        )

    return chunks


def main():
    all_chunks = []

    for xml_path in RAW_DIR.glob("*.xml"):
        try:
            chunks = parse_label(xml_path)
            print(f"{xml_path.name}: {len(chunks)} section chunks")
            all_chunks.extend(chunks)
        except (ET.ParseError, OSError) as error:
            print(f"Could not parse {xml_path.name}: {error}")

    save_chunks(all_chunks, OUTPUT_FILE)
    print(f"\nSaved {len(all_chunks)} chunks to: {OUTPUT_FILE}")

    if not all_chunks:
        print("No target sections found. We will inspect the XML structure next.")


if __name__ == "__main__":
    main()
