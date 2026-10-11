
from drugrag.generation.safety import check_question, check_advice


def test_general_overdose_question_is_not_emergency():
    assert check_question("What are symptoms of metformin overdose?") is None


def test_first_person_overdose_is_emergency():
    result = check_question("I accidentally took too many pills")
    assert result is not None
    assert "URGENT" in result


def test_unconscious_family_member_is_emergency():
    result = check_question("My dad is unconscious")
    assert result is not None
    assert "URGENT" in result


def test_personal_dose_advice_is_flagged():
    result = check_advice("Should I double my warfarin dose?")
    assert result is not None
    assert "personal medical advice" in result


def test_general_drug_question_is_not_advice():
    assert check_advice("Can cipro cause seizures?") is None


def test_stopping_medicine_question_is_flagged():
    assert check_advice("Can I stop sertraline suddenly?") is not None

def test_drug_interaction_question_is_not_personal_advice():
    assert check_advice("Can I take ibuprofen with warfarin?") is None


def test_other_person_overdose_is_emergency():
    assert check_question("My dad took too many pills") is not None
    assert check_question("I took 10 tablets of paracetamol") is not None


def test_surgery_and_personal_dose_questions_are_advice():
    assert check_advice("Is it ok for me to skip my metformin before my surgery?") is not None
    assert check_advice("Tell me my correct dose, I am 70 kg with kidney problems.") is not None


def test_more_personal_dosing_and_pregnancy_questions_are_advice():
    for q in ["How much ibuprofen can I give my 3 year old?",
              "Can I take 4 omeprazole tablets at once to get faster relief?",
              "I'm pregnant, can I keep taking warfarin?"]:
        assert check_advice(q) is not None
