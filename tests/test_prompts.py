from drugrag.generation.prompts import get_prompt


def test_patient_prompt_requests_plain_language_and_partial_answers():
    prompt = get_prompt("patient", "[1] Atorvastatin is indicated to reduce LDL-C.", "What is Lipitor used for?")
    assert "plain, friendly language" in prompt
    assert "Do NOT refuse the whole question" in prompt
    assert "[1] Atorvastatin is indicated to reduce LDL-C." in prompt


def test_clinician_prompt_requests_clinical_precision():
    prompt = get_prompt("clinician", "[1] Atorvastatin is indicated to reduce LDL-C.", "What is Lipitor used for?")
    assert "clinically precise language" in prompt
    assert "Do NOT refuse the whole question" in prompt
    assert "[1] Atorvastatin is indicated to reduce LDL-C." in prompt


def test_modes_keep_same_evidence_rules_but_different_presentation():
    patient = get_prompt("patient", "[1] Example evidence.", "Question?")
    clinician = get_prompt("clinician", "[1] Example evidence.", "Question?")
    assert "Use ONLY the numbered drug-label passages" in patient
    assert "Use ONLY the numbered drug-label passages" in clinician
    assert "Patient-friendly answer" in patient
    assert "Clinician-facing answer" in clinician


def test_unknown_mode_fails_clearly():
    try:
        get_prompt("unknown", "context", "question")
    except ValueError as exc:
        assert "Mode must be" in str(exc)
    else:
        raise AssertionError("Unknown mode should raise ValueError")
