def check_question(question):
    """
    Check whether the user's question describes
    a possible medical emergency.
    """

    if not question or not question.strip():
        return "Please enter a question."

    text = question.lower()

    emergency_keywords = [
        "overdose",
        "took too many pills",
        "too many pills",
        "too many ibuprofen pills",
        "took too much ibuprofen",
        "accidentally took too much",
        "can't breathe",
        "cannot breathe",
        "difficulty breathing",
        "trouble breathing",
        "unconscious",
        "seizure"
    ]

    for keyword in emergency_keywords:
        if keyword in text:
            return (
                "URGENT: This may be a medical emergency. "
                "Contact your local emergency service immediately. "
                "In India, call 112. Do not wait for a chatbot response."
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
