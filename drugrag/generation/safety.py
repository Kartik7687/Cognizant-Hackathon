import re


def check_question(question):
    """
    Check whether the question describes a possible
    medical emergency involving the user or someone else.
    """

    if not question or not question.strip():
        return "Please enter a question."

    text = question.lower().strip()

    emergency_patterns = [
        r"\bi\s+(?:accidentally\s+)?took\s+too\s+many\b",
        r"\bi\s+took\s+too much\b",
        r"\bi\s+overdosed\b",
        r"\bi\s+(?:can't|cannot|can not)\s+breathe\b",
        r"\bi\s+am\s+having\s+trouble\s+breathing\b",
        r"\bi\s+am\s+unconscious\b",
        r"\bmy\s+(?:dad|mom|mum|mother|father|parent|"
        r"friend|child|son|daughter|husband|wife|partner)"
        r"\s+(?:is|was|has become)\s+unconscious\b",
        r"\b(?:someone|somebody)\s+(?:is|has become)\s+unconscious\b",
        r"\bmy\s+(?:dad|mom|mum|mother|father|parent|"
        r"friend|child|son|daughter|husband|wife|partner)"
        r"\s+(?:is|has been)\s+having\s+(?:a\s+)?seizure\b",
        r"\bi\s+am\s+having\s+(?:a\s+)?seizure\b",
    ]

    for pattern in emergency_patterns:
        if re.search(pattern, text):
            return (
                "URGENT: This may be a medical emergency. "
                "Contact your local emergency service immediately. "
                "In India, call 112. Do not wait for a chatbot response."
            )

    return None


def check_advice(question):
    """
    Flag requests for individualized medical decisions,
    such as changing a dose or stopping a medicine.

    General drug-information and interaction questions are
    not refused just because they use 'Can I', 'Could I',
    or 'May I'.
    """

    if not question or not question.strip():
        return None

    text = question.lower().strip()

    advice_patterns = [
        r"\bshould i\b",
        r"\bwhat dose should i\b",
        r"\bhow much should i take\b",
        r"\bwhat dosage should i\b",
        r"\bhow many pills should i take\b",
        r"\bwhat dose do i need\b",
        r"\bcan i stop\b",
        r"\bshould i stop\b",
        r"\bcan i increase\b",
        r"\bshould i increase\b",
        r"\bcan i reduce\b",
        r"\bshould i reduce\b",
        r"\bcan i double\b",
        r"\bshould i double\b",
        r"\bcan i skip\b",
        r"\bshould i skip\b",
        r"\bis it safe for me\b",
    ]

    for pattern in advice_patterns:
        if re.search(pattern, text):
            return (
                "I can't provide personal medical advice or decide "
                "what dose is right for you. I can summarize what "
                "the available drug label says, but the label may "
                "not account for your individual circumstances. "
                "Please consult your doctor or pharmacist before "
                "changing a dose or stopping a medicine."
            )

    return None


def check_answer(answer):
    """
    Check whether the generated answer is empty.
    """

    if not answer or not answer.strip():
        return (
            "I could not generate a reliable answer from the "
            "available drug documentation. Please consult "
            "a doctor or pharmacist."
        )

    return answer
