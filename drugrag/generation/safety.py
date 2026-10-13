import re


EMERGENCY_MESSAGE = (
    "URGENT: This may be a medical emergency. "
    "Call 102 (ambulance) right now. You can also dial 112, "
    "India's national emergency number. "
    "If someone is with you, ask them to help and stay with the person. "
    "Do not wait for a chatbot response."
)


def _normalise(question):
    """Lower-case and tidy informal text so 'I m', 'im' and \"i'm\" all read as 'i am'."""
    text = (question or "").lower().strip()
    text = text.replace("\u2019", "'")
    text = re.sub(r"\bi\s*'\s*m\b|\bi\s+m\b|\bim\b", "i am", text)
    text = re.sub(r"\b(?:cant|can't)\b", "can't", text)
    return re.sub(r"\s+", " ", text)


def check_question(question):
    """
    Check whether the question describes a possible
    medical emergency involving the user or someone else.
    """

    if not question or not question.strip():
        return "Please enter a question."

    text = _normalise(question)

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
        r"\b(?:my\s+\w+|he|she|they|someone|somebody)\s+"
        r"(?:accidentally\s+)?(?:took|swallowed)\s+too\s+(?:many|much)\b",
        r"\b(?:i|my\s+\w+|he|she)\s+(?:took|swallowed|ate)\s+"
        r"(?:\d{2,}|several|a\s+handful\s+of|a\s+whole\s+bottle\s+of)\s*"
        r"(?:tablets?|pills?|capsules?)\b",
        r"\b(?:i|my\s+\w+|he|she)\s+(?:is|am|was)\s+not\s+breathing\b",
        # --- general emergencies (not only medicine overdoses) ---
        # "I am having a heart attack", "she is having a stroke", "I just had a heart attack"
        r"\b(?:i|we|he|she|they|someone|somebody|my\s+\w+)\s+"
        r"(?:am|is|are|was|think\s+i\s+am|think\s+he\s+is|think\s+she\s+is)?\s*"
        r"(?:just\s+)?(?:having|had)\s+(?:a\s+|an\s+)?"
        r"(?:heart\s+attack|stroke|cardiac\s+arrest|seizure|asthma\s+attack|"
        r"anaphylaxis|anaphylactic\s+shock|severe\s+allergic\s+reaction)\b(?!\s+(?:last|in|years?|ago))",
        r"\bthink\s+(?:i|he|she)\s+(?:am|is)\s+(?:having|dying)\b",
        r"\b(?:i|he|she|someone|somebody|my\s+\w+)\s+(?:am|is|are)?\s*(?:dying|going\s+to\s+die)\b",
        # chest pain happening now
        r"\b(?:i|he|she|someone|my\s+\w+)\s+(?:have|has|am\s+having|is\s+having|feel|feels|got|getting)\s+"
        r"(?:a\s+|some\s+|severe\s+|sharp\s+|crushing\s+|sudden\s+)*chest\s+(?:pain|tightness|pressure)\b",
        r"\bmy\s+chest\s+(?:hurts|is\s+hurting|is\s+tight|feels\s+tight|is\s+paining)\b",
        # accidents and injuries
        r"\b(?:i|we|he|she|they|someone|somebody|my\s+\w+)\s+(?:just\s+)?"
        r"(?:had|got\s+into|got\s+in|was\s+in|were\s+in|met\s+with)\s+(?:an?\s+)?"
        r"(?:accident|car\s+crash|road\s+accident|bike\s+accident|crash)\b",
        r"\b(?:accident|car\s+crash|road\s+accident)\b.*\b(?:injur\w+|hurt|bleeding|broken|fracture\w*)\b",
        r"\b(?:have|has|had|got|i\s+broke|broke|broken|fractured)\s+(?:broken|fractured|my|his|her|some|a)?\s*"
        r"(?:bones?|arm|leg|ribs?|neck|skull|hip|spine|back|wrist|ankle)\b"
        r"(?=.*\b(?:broke|broken|fracture\w*)\b)",
        r"\b(?:broke|broken|fractured|dislocated)\s+(?:some\s+|a\s+|my\s+|his\s+|her\s+)?"
        r"(?:bones?|arm|leg|ribs?|neck|skull|hip|spine|back|wrist|ankle)\b",
        # heavy bleeding, choking, collapse, poisoning
        r"\b(?:won'?t|will\s+not|can'?t|cannot)\s+stop\s+(?:the\s+)?bleeding\b",
        r"\bbleeding\s+(?:won'?t|will\s+not|does\s+not|doesn'?t)\s+stop\b",
        r"\b(?:i|he|she|they|someone|somebody|my\s+\w+)\s+(?:am|is|are|keeps?)?\s*(?:\w+\s+)?"
        r"bleeding\s+(?:heavily|badly|a\s+lot|profusely|non\s?stop)\b",
        r"\b(?:i|he|she|they|someone|somebody|my\s+\w+)\s+(?:am|is|are|was)\s+choking\b",
        r"\b(?:i|he|she|they|someone|somebody|my\s+\w+)\s+(?:just\s+)?"
        r"(?:fainted|collapsed|passed\s+out|is\s+unresponsive|am\s+unresponsive)\b",
        r"\b(?:i|he|she|they|someone|somebody|my\s+\w+)\s+(?:just\s+)?"
        r"(?:drank|swallowed|ate)\s+(?:some\s+)?(?:poison|bleach|pesticide|insecticide|"
        r"kerosene|acid|rat\s+poison)\b",
        r"\b(?:i|he|she|someone|my\s+\w+)\s+(?:am|is|are|has|have)\s+(?:\w+\s+)?"
        r"(?:severe|difficulty|trouble)\s+breathing\b",
        r"\bsudden\s+(?:weakness|numbness)\s+(?:on\s+one\s+side|in\s+(?:my\s+)?face)\b",
        r"\b(?:suffering|having)\s+(?:a\s+)?(?:heart\s+attack|stroke)\b",
    ]

    for pattern in emergency_patterns:
        if re.search(pattern, text):
            return EMERGENCY_MESSAGE

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
        r"\b(?:ok|okay|fine|safe)\s+for\s+me\s+to\b",
        r"\bhow\s+much\b.*\bcan\s+i\s+(?:give|take)\b",
        r"\bcan\s+i\s+(?:take|give)\s+\d+\b",
        r"\b(?:i'?m|i\s+am)\s+(?:pregnant|breastfeeding)\b",
        r"\bcan\s+i\s+(?:keep|continue)\s+taking\b",
        r"\bmy\s+(?:correct|right|exact)\s+(?:dose|dosage)\b",
        r"\bi\s+(?:am|weigh)\s+\d+\s*(?:kg|lbs?|pounds|years)\b",
        r"\b(?:my|i have)\s+(?:kidney|liver|heart)\s+(?:problems?|disease|failure)\b.*\bdose\b",
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
