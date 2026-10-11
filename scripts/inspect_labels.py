
import xml.etree.ElementTree as ET
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

FILES = [
    "valsartan.xml",
]


def local_name(tag):
    return tag.split("}")[-1].lower()


for filename in FILES:
    path = RAW_DIR / filename

    print(f"\n{'=' * 70}")
    print(f"FILE: {filename}")
    print("=" * 70)

    if not path.exists():
        print("FILE NOT FOUND")
        continue

    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as error:
        print(f"INVALID XML: {error}")
        continue

    section_count = 0

    for section in root.iter():
        if local_name(section.tag) != "section":
            continue

        # Read this section's direct title and code elements.
        title = ""
        code_value = ""
        code_display = ""

        for child in section:
            tag = local_name(child.tag)

            if tag == "title":
                title = " ".join(" ".join(child.itertext()).split())

            elif tag == "code":
                code_value = child.attrib.get("code", "")
                code_display = child.attrib.get("displayName", "")

        if title or code_value or code_display:
            section_count += 1
            print(
                f"Title: {title or '[NO TITLE]'}\n"
                f"  LOINC code: {code_value or '[NO CODE]'}\n"
                f"  Code display: {code_display or '[NO DISPLAY]'}"
            )

    print(f"\nTotal sections found: {section_count}")
