
from drugrag.eval.metrics import is_refusal


def test_consulting_doctor_alone_is_not_a_refusal():
    answer = {
        "text": "Ibuprofen may cause side effects. Consult your doctor or pharmacist.",
        "refused": False,
    }
    assert is_refusal(answer) is False


def test_explicit_medical_advice_refusal_is_detected():
    answer = {
        "text": "I cannot provide personal medical advice.",
        "refused": True,
    }
    assert is_refusal(answer) is True
