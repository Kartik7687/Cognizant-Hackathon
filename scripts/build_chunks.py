
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



# Match official DailyMed section codes, not section title wording.
TARGET_SECTIONS = {
    "34067-9": "Indications and Usage",
    "34068-7": "Dosage and Administration",
    "34070-3": "Contraindications",
    "43685-7": "Warnings and Precautions",
    "34084-4": "Adverse Reactions",
    "34073-7": "Drug Interactions",
    "43684-0": "Use in Specific Populations",
    "34069-5": "How Supplied",
    "43678-2": "Dosage Forms and Strengths",
    "34066-1": "Boxed Warning",
    "34088-5": "Overdosage",
    "34089-3": "Description",
    "34090-1": "Clinical Pharmacology",
    "43680-8": "Nonclinical Toxicology",
    "34092-7": "Clinical Studies",
    "34076-0": "Patient Counseling Information",
    "34071-1": "Warnings",
    "34067-9": "Indications and Usage",
    "34068-7": "Dosage and Administration",
    "50569-3": "Ask Doctor",
    "50567-7": "When Using",
    "50566-9": "Stop Use",
}



def local_name(tag):
    """Remove the XML namespace and normalize the tag."""
    return tag.split("}")[-1].lower()


def text_of(element):
    """Extract readable text from an XML element."""
    return " ".join(" ".join(element.itertext()).split())


def section_text_without_nested_sections(element):
    """Extract text while excluding nested sections and excerpts."""
    parts = []

    def walk(node):
        for child in node:
            tag = local_name(child.tag)

            if tag in {"section", "excerpt"}:
                continue

            if child.text:
                parts.append(child.text)

            walk(child)

            if child.tail:
                parts.append(child.tail)

    walk(element)
    return " ".join(" ".join(parts).split())

def normalize_date(value):
    value = (value or "").strip()

    # Convert YYYYMMDD to YYYY-MM-DD
    if re.fullmatch(r"\d{8}", value):
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"

    # Keep dates already in YYYY-MM-DD format
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value

    return ""


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

    return set_id, version, normalize_date(effective_date)


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

        title = text_of(title_element).upper().strip() if title_element is not None else ""
        title = re.sub(r"^\d+(?:\.\d+)*\s+", "", title)
        
        # Read the official LOINC code from this section's direct <code> element.
        code_element = next(
            (
                child for child in section
                if local_name(child.tag) == "code"
            ),
            None,
        )

        section_code = (
            code_element.attrib.get("code", "").strip()
            if code_element is not None
            else ""
        )

        section_name = TARGET_SECTIONS.get(section_code)

        if not section_name:
            has_parent_section = any(
                local_name(parent.tag) == "section"
                for parent in root.iter()
                if section in list(parent)
            )

            if not has_parent_section and title:
                print(
                    f"  Unmatched top-level title in "
                    f"{xml_path.name}: {title} "
                    f"(LOINC code: {section_code or 'missing'})"
                )
            continue

        if not section_name:
            continue

        content_parts = []

        for child in section:
            if child is title_element:
                continue
            if local_name(child.tag) == "section":
                continue
            content = section_text_without_nested_sections(child)
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
                section_code=section_code,
                page="N/A",
                source_url=source_url,
            )
        )
    
    
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

