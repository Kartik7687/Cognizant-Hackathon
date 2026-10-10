
import requests
from download_labels import EXISTING_DRUGS, download_label

DRUGS_TO_UPDATE = ["levothyroxine", "lantus"]

with requests.Session() as session:
    session.headers.update({
        "User-Agent": "DrugDocumentationChatbot/1.0"
    })

    for drug in DRUGS_TO_UPDATE:
        set_id = EXISTING_DRUGS[drug]
        print(f"\nUpdating {drug} with label {set_id}")

        success = download_label(drug, set_id, session)

        if not success:
            print(f"FAILED: {drug}")
        else:
            print(f"SUCCESS: {drug}")
