"""MOCK label chunks (5 drugs x 6 sections) so every teammate can code before the real pipeline lands.

These are short paraphrases for wiring and tests ONLY. They are not medical information and must never
appear in the demo or the evaluation. Real chunks come from the DailyMed pipeline (drugrag/pipeline).
"""
from __future__ import annotations

from .schema import Chunk

SECTIONS = {
    "Indications and Usage": "34067-9",
    "Dosage and Administration": "34068-7",
    "Contraindications": "34070-3",
    "Warnings and Precautions": "43685-7",
    "Adverse Reactions": "34084-4",
    "Drug Interactions": "34073-7",
}

_DRUGS: dict[str, dict] = {
    "metformin": {
        "aliases": ["glucophage"],
        "Indications and Usage": "Metformin hydrochloride tablets are indicated as an adjunct to diet and exercise to improve glycemic control in adults and pediatric patients 10 years of age and older with type 2 diabetes mellitus.",
        "Dosage and Administration": "Adults: the recommended starting dose is 500 mg orally twice a day or 850 mg once a day, given with meals. Increase the dose in increments of 500 mg weekly based on tolerability. The maximum daily dose is 2550 mg.",
        "Contraindications": "Metformin is contraindicated in patients with severe renal impairment (eGFR below 30 mL/min/1.73 m2), known hypersensitivity to metformin, and acute or chronic metabolic acidosis, including diabetic ketoacidosis.",
        "Warnings and Precautions": "Lactic acidosis: postmarketing cases of metformin-associated lactic acidosis have resulted in death. Risk factors include renal impairment, age 65 years or older, radiological studies with contrast, surgery, hypoxic states, excessive alcohol intake, and hepatic impairment.",
        "Adverse Reactions": "The most common adverse reactions (incidence above 5%) are diarrhea, nausea, vomiting, flatulence, asthenia, indigestion, abdominal discomfort, and headache.",
        "Drug Interactions": "Carbonic anhydrase inhibitors such as topiramate may increase the risk of lactic acidosis. Drugs that reduce metformin clearance, such as ranolazine, dolutegravir, and cimetidine, may increase metformin levels. Alcohol potentiates the effect of metformin on lactate metabolism.",
    },
    "warfarin": {
        "aliases": ["coumadin", "jantoven"],
        "Indications and Usage": "Warfarin sodium is indicated for prophylaxis and treatment of venous thrombosis and pulmonary embolism, for thromboembolic complications associated with atrial fibrillation and cardiac valve replacement, and to reduce the risk of death and recurrent myocardial infarction.",
        "Dosage and Administration": "Individualize the dose based on the patient's INR. Initial dosing is commonly 2 mg to 5 mg once daily, then adjusted according to INR monitoring. The target INR for most indications is 2.0 to 3.0.",
        "Contraindications": "Warfarin is contraindicated in pregnancy except in women with mechanical heart valves, in patients with hemorrhagic tendencies or blood dyscrasias, after recent surgery of the central nervous system or eye, in unsupervised patients with conditions such as dementia, and with known hypersensitivity to warfarin.",
        "Warnings and Precautions": "Boxed warning: warfarin can cause major or fatal bleeding. Perform regular monitoring of INR in all treated patients. Drugs, dietary changes, and other factors affect INR levels achieved with warfarin therapy.",
        "Adverse Reactions": "Fatal and nonfatal hemorrhage from any tissue or organ is the most serious risk. Other adverse reactions include necrosis of skin and other tissues, purple toes syndrome, and hypersensitivity reactions.",
        "Drug Interactions": "Concomitant use of NSAIDs such as ibuprofen, aspirin, antiplatelet drugs, and other anticoagulants increases the risk of bleeding. Inhibitors or inducers of CYP2C9, 1A2 and 3A4 can alter warfarin exposure and INR. Increased intake of vitamin K rich foods can reduce the anticoagulant effect.",
    },
    "ibuprofen": {
        "aliases": ["advil", "motrin"],
        "Indications and Usage": "Ibuprofen tablets are indicated for relief of the signs and symptoms of rheumatoid arthritis and osteoarthritis, for relief of mild to moderate pain, and for treatment of primary dysmenorrhea.",
        "Dosage and Administration": "For mild to moderate pain, 400 mg every 4 to 6 hours as necessary. Do not exceed 3200 mg total daily dose. Use the lowest effective dose for the shortest duration consistent with individual treatment goals.",
        "Contraindications": "Ibuprofen is contraindicated in patients with known hypersensitivity to ibuprofen, in patients who have experienced asthma, urticaria, or allergic-type reactions after taking aspirin or other NSAIDs, and in the setting of coronary artery bypass graft (CABG) surgery.",
        "Warnings and Precautions": "Boxed warning: NSAIDs cause an increased risk of serious cardiovascular thrombotic events, including myocardial infarction and stroke, and of serious gastrointestinal bleeding, ulceration, and perforation, which can be fatal. Avoid use in late pregnancy because of the risk of premature closure of the fetal ductus arteriosus.",
        "Adverse Reactions": "Common adverse reactions include nausea, dyspepsia, abdominal pain, heartburn, diarrhea, headache, dizziness, and rash.",
        "Drug Interactions": "Concomitant use with warfarin or other anticoagulants increases the risk of serious bleeding. NSAIDs may diminish the antihypertensive effect of ACE inhibitors and diuretics, and may increase lithium and methotrexate levels. Concomitant use with aspirin increases gastrointestinal bleeding risk.",
    },
    "amoxicillin": {
        "aliases": ["amoxil"],
        "Indications and Usage": "Amoxicillin is indicated for infections due to susceptible bacteria, including infections of the ear, nose, and throat, genitourinary tract, skin, and lower respiratory tract, and for Helicobacter pylori eradication in combination therapy.",
        "Dosage and Administration": "Adults and pediatric patients weighing 40 kg or more: 500 mg every 12 hours or 250 mg every 8 hours for mild to moderate infections; 875 mg every 12 hours or 500 mg every 8 hours for severe infections. Dosing in infants under 3 months is based on body weight.",
        "Contraindications": "Amoxicillin is contraindicated in patients who have experienced a serious hypersensitivity reaction, such as anaphylaxis or Stevens-Johnson syndrome, to amoxicillin or to other beta-lactam antibacterial drugs, including penicillins and cephalosporins.",
        "Warnings and Precautions": "Serious and occasionally fatal hypersensitivity reactions have been reported. Clostridioides difficile-associated diarrhea has been reported with nearly all antibacterial agents. Prescribing amoxicillin without a proven or strongly suspected bacterial infection is unlikely to benefit the patient and increases the risk of drug-resistant bacteria.",
        "Adverse Reactions": "The most frequently reported adverse reactions are diarrhea, rash, vomiting, and nausea.",
        "Drug Interactions": "Probenecid decreases renal tubular secretion of amoxicillin and may increase blood levels. Concomitant use with allopurinol increases the incidence of rash. Concomitant use with oral anticoagulants may prolong prothrombin time or increase INR, so monitor appropriately.",
    },
    "atorvastatin": {
        "aliases": ["lipitor"],
        "Indications and Usage": "Atorvastatin calcium is indicated to reduce the risk of myocardial infarction, stroke, and revascularization procedures in adults with multiple risk factors for coronary heart disease, and as an adjunct to diet to reduce LDL-C in adults with primary hyperlipidemia.",
        "Dosage and Administration": "The recommended starting dose is 10 mg or 20 mg once daily, and the dosage range is 10 mg to 80 mg once daily, taken at any time of day with or without food. Adjust dosage based on LDL-C response at intervals of 4 weeks or more.",
        "Contraindications": "Atorvastatin is contraindicated in patients with acute liver failure or decompensated cirrhosis, and in patients with hypersensitivity to atorvastatin or any excipients in the formulation.",
        "Warnings and Precautions": "Myopathy and rhabdomyolysis: atorvastatin may cause myopathy. Risk factors include age 65 or greater, uncontrolled hypothyroidism, renal impairment, and concomitant use with certain drugs. Discontinue if markedly elevated creatine kinase levels occur or myopathy is suspected. Assess liver enzymes before initiating therapy.",
        "Adverse Reactions": "The most common adverse reactions (incidence of 2% or more) are nasopharyngitis, arthralgia, diarrhea, pain in extremity, and urinary tract infection.",
        "Drug Interactions": "Concomitant use with strong CYP3A4 inhibitors such as clarithromycin, itraconazole, and ritonavir-containing regimens, or with cyclosporine, gemfibrozil, or fibrates increases the risk of myopathy and rhabdomyolysis. Limit the atorvastatin dose when co-administered with clarithromycin or itraconazole.",
    },
}


def mock_chunks() -> list[Chunk]:
    chunks: list[Chunk] = []
    for drug, spec in _DRUGS.items():
        for section, code in SECTIONS.items():
            slug = section.lower().replace(" ", "-")
            chunks.append(
                Chunk(
                    chunk_id=f"{drug}-mock-{slug}-0",
                    drug_name=drug,
                    section=section,
                    text=spec[section],
                    aliases=list(spec["aliases"]),
                    set_id=f"MOCK-{drug}",
                    version="1",
                    effective_date="2024-01-01",
                    section_code=code,
                    page="N/A",
                    source_url="MOCK",
                )
            )
    return chunks
