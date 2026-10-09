
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

BRAND_ALIASES = {
    "warfarin": ["Coumadin", "Jantoven"],
    "metformin": ["Glucophage", "Fortamet", "Glumetza"],
    "lisinopril": ["Zestril", "Prinivil"],
    "amlodipine": ["Norvasc"],
    "atorvastatin": ["Lipitor"],
}


TARGET_SECTIONS = {
    "INDICATIONS AND USAGE": "Indications and Usage",
    "INDICATIONS & USAGE": "Indications and Usage",
    "DOSAGE AND ADMINISTRATION": "Dosage and Administration",
    "CONTRAINDICATIONS": "Contraindications",
    "WARNINGS AND PRECAUTIONS": "Warnings and Precautions",
    "WARNINGS": "Warnings",
    "WARNINGS AND CAUTIONS": "Warnings and Cautions",
    "ADVERSE REACTIONS": "Adverse Reactions",
    "DRUG INTERACTIONS": "Drug Interactions",
    "USE IN SPECIFIC POPULATIONS": "Use in Specific Populations",
    "DIRECTIONS": "Directions",
    "DO NOT USE": "Contraindications",
    "ASK A DOCTOR BEFORE USE IF": "Warnings",
    "ASK A DOCTOR OR PHARMACIST BEFORE USE IF YOU ARE": "Warnings",
    "WHEN USING THIS PRODUCT": "Warnings",
    "STOP USE AND ASK A DOCTOR IF": "Warnings",
    "OTHER INFORMATION": "Other Information",
    "INACTIVE INGREDIENTS": "Inactive Ingredients",
    "PRINCIPAL DISPLAY PANEL": "Principal Display Panel",
    "DRUG FACTS": "Drug Facts",
}


def local_name(tag):
    """Remove the XML namespace and normalize the tag."""
    return tag.split("}")[-1].lower()


def text_of(element):
    """Extract readable text from an XML element."""
    return " ".join(" ".join(element.itertext()).split())


def get_metadata(root):
    """Read the official label metadata from SPL XML."""
    set_id = ""
    version = ""
    effective_date = ""

    for elem in root.iter():
        name = local_name(elem.tag)

        if name == "setid" and not set_id:
            set_id = (
                elem.attrib.get("root", "").strip()
                or (elem.text or "").strip()
            )

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

    return set_id, version, effective_date


def parse_label(xml_path):
    root = ET.parse(xml_path).getroot()

    # Filenames use underscores for drug names containing spaces.
    drug_name = xml_path.stem.lower().replace("_", " ")

    set_id, version, effective_date = get_metadata(root)

    source_url = (
        f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm"
        f"?setid={set_id}"
        if set_id else ""
    )

    chunks = []
    seen = set()

    for section in root.iter():
        if local_name(section.tag) != "section":
            continue

        # Find this section's direct title, avoiding a title belonging
        # to a nested subsection.
        title_element = next(
            (
                child for child in section
                if local_name(child.tag) == "title"
            ),
            None,
        )

        if title_element is None:
            continue

        title = text_of(title_element).upper().strip()
        title = re.sub(r"^\d+(?:\.\d+)*\s+", "", title)

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

        full_text = re.sub(
            r"\s+", " ", " ".join(content_parts)
        ).strip()

        if len(full_text) < 40:
            continue

        duplicate_key = (section_name, full_text)
        if duplicate_key in seen:
            continue
        seen.add(duplicate_key)

        # Use the actual Set ID where available for traceability.
        chunk_prefix = set_id or xml_path.stem

        chunks.append(
            Chunk(
                chunk_id=f"{chunk_prefix}-{len(chunks) + 1}",
                drug_name=drug_name,
                section=section_name,
                text=full_text,
                aliases=BRAND_ALIASES.get(drug_name, []),
                set_id=set_id,
                version=version,
                effective_date=effective_date,
                section_code=title,
                page="N/A",
                source_url=source_url,
            )
        )
    
    # Fallback: retain useful text when no recognized sections were found.
    if not chunks:
        parts = []

        for element in root.iter():
            if local_name(element.tag) == "text":
                content = text_of(element)
                if content and len(content) >= 40:
                    parts.append(content)

        fallback_text = re.sub(
            r"\s+", " ", " ".join(dict.fromkeys(parts))
        ).strip()

        if fallback_text:
            chunks.append(
                Chunk(
                    chunk_id=f"{set_id or xml_path.stem}-fallback-1",
                    drug_name=drug_name,
                    section="Product Information",
                    text=fallback_text[:12000],
                    aliases=BRAND_ALIASES.get(drug_name, []),
                    set_id=set_id,
                    version=version,
                    effective_date=effective_date,
                    section_code="PRODUCT_INFORMATION",
                    page="N/A",
                    source_url=source_url,
                )
            )

    return chunks


def main():
    all_chunks = []
    drug_count = 0

    if not RAW_DIR.exists():
        print(f"Raw data directory not found: {RAW_DIR}")
        return

    xml_files = sorted(RAW_DIR.glob("*.xml"))

    print(f"Found {len(xml_files)} XML files.")

    for xml_path in xml_files:
        try:
            chunks = parse_label(xml_path)
            print(f"{xml_path.name}: {len(chunks)} section chunks")

            if chunks:
                drug_count += 1
                all_chunks.extend(chunks)
            else:
                print(
                    f"  Warning: no matching sections found "
                    f"in {xml_path.name}"
                )

        except (ET.ParseError, OSError, ValueError) as error:
            print(f"Could not parse {xml_path.name}: {error}")

    save_chunks(all_chunks, OUTPUT_FILE)

    print("\n" + "=" * 45)
    print(f"XML files found: {len(xml_files)}")
    print(f"Labels producing chunks: {drug_count}")
    print(f"Total chunks created: {len(all_chunks)}")
    print(f"Output saved to: {OUTPUT_FILE}")

    if not all_chunks:
        print("No chunks were generated. Check the XML structure.")


if __name__ == "__main__":
 main()

