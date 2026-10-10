"""Brand and alternative names for the 40 drugs in the first download.

Patients ask for "Tylenol", "Zoloft" or "Plavix", not the generic name. Without an alias the drug filter finds
no drug, searches every label, and can answer from the wrong one. Keys are the generic `drug_name` used in
chunks.jsonl; values are lowercase. Extend this when you add drugs.
"""

BRAND_ALIASES: dict[str, list[str]] = {
    "warfarin": ["coumadin", "jantoven"],
    "metformin": ["glucophage", "fortamet", "glumetza"],
    "lisinopril": ["zestril", "prinivil", "qbrelis"],
    "amlodipine": ["norvasc"],
    "atorvastatin": ["lipitor"],
    "amoxicillin": ["amoxil", "moxatag"],
    "azithromycin": ["zithromax", "z-pak"],
    "ibuprofen": ["advil", "motrin"],
    "acetaminophen": ["tylenol", "paracetamol", "apap"],
    "omeprazole": ["prilosec"],
    "losartan": ["cozaar"],
    "hydrochlorothiazide": ["microzide", "hctz"],
    "levothyroxine": ["synthroid", "levoxyl", "unithroid", "euthyrox"],
    "albuterol": ["proventil", "ventolin", "proair", "salbutamol"],
    "sertraline": ["zoloft"],
    "gabapentin": ["neurontin"],
    "prednisone": ["deltasone", "rayos"],
    "doxycycline": ["vibramycin", "doryx"],
    "cephalexin": ["keflex"],
    "ciprofloxacin": ["cipro"],
    "fluoxetine": ["prozac", "sarafem"],
    "pantoprazole": ["protonix"],
    "famotidine": ["pepcid"],
    "furosemide": ["lasix"],
    "carvedilol": ["coreg"],
    "metoprolol": ["lopressor", "toprol-xl"],
    "clopidogrel": ["plavix"],
    "apixaban": ["eliquis"],
    "ondansetron": ["zofran"],
    "insulin glargine": ["lantus", "basaglar", "toujeo"],
    "naproxen": ["naprosyn", "aleve", "anaprox"],
    "cetirizine": ["zyrtec"],
    "loratadine": ["claritin"],
    "montelukast": ["singulair"],
    "escitalopram": ["lexapro"],
    "prednisolone": ["orapred", "millipred"],
    "enalapril": ["vasotec"],
    "spironolactone": ["aldactone"],
    "rosuvastatin": ["crestor"],
    "valsartan": ["diovan"],
}

# Downloaded under a brand name; chunks should use the generic name (brand goes to aliases).
RENAME_DRUG: dict[str, str] = {"lantus": "insulin glargine"}
