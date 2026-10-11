from dataclasses import dataclass, field
import re

import ollama

from ..schema import format_citation
from ..retrieval.retrieve import format_context
from .prompts import get_prompt
from .safety import check_question, check_advice, check_answer


@dataclass
class Answer:
    query: str
    mode: str
    text: str
    sources: list[str] = field(default_factory=list)
    refused: bool = False
    not_found: bool = False


NOT_FOUND_PATTERNS = [
    r"not found in (the |this |these )?(label|labels|provided|context)",
    r"(does not|doesn't|do not) (contain|mention|include|state|specify)",
    r"no (information|mention|data) (is |was )?(found|available|provided)",
    r"could not find",
    r"couldn'?t find",
]


def detect_not_found(text: str) -> bool:
    """Return True when the answer indicates missing information."""
    if not text:
        return False

    text = text.lower()
    return any(
        re.search(pattern, text)
        for pattern in NOT_FOUND_PATTERNS
    )


def answer(query, hits, mode="patient") -> Answer:
    """
    Generate a drug information answer using retrieved
    drug-label passages and the Ollama LLM.
    """

    safety_message = check_question(query)

    if safety_message:
        return Answer(
            query=query,
            mode=mode,
            text=safety_message + "\n\nSources: None",
            sources=[],
            refused=True,
            not_found=False,
        )

    hits = hits or []

    sources = []
    for hit in hits:
        citation = format_citation(hit.chunk)
        if citation not in sources:
            sources.append(citation)

    advice_message = check_advice(query)

    if advice_message:
        if hits:
            label_context = format_context(hits)
            text = (
                advice_message
                + "\n\nWhat the available label information says:\n"
                + label_context
            )
        else:
            text = (
                advice_message
                + "\n\nI could not find relevant information in the "
                "drug labels I have available."
            )

        text += "\n\nSources: " + (
            "; ".join(sources)
            if sources
            else "No relevant label passages found"
        )

        return Answer(
            query=query,
            mode=mode,
            text=text,
            sources=sources,
            refused=True,
            not_found=not bool(hits),
        )

    if not hits:
        text = (
            "Direct answer: I could not find this drug or relevant "
            "information in the drug labels I have available. "
            "This does not mean the drug has no prescribing information.\n\n"
            "What to do next: Consult a doctor or pharmacist for "
            "reliable information.\n\n"
            "Sources: No relevant label passages found"
        )

        return Answer(
            query=query,
            mode=mode,
            text=text,
            sources=[],
            refused=False,
            not_found=True,
        )

    context = format_context(hits)

    prompt = get_prompt(
        mode=mode,
        context=context,
        question=query,
    )

    response = ollama.chat(
        model="llama3.2",
        messages=[
            {
                "role": "system",
                "content": (
                    "Use only the supplied drug-label passages. "
                    "Do not invent medical facts or contradict the evidence. "
                    "Do not add unsupported medical risks. "
                    "Distinguish information in the supplied passages "
                    "from information that has not been established. "
                    "Do not claim the entire drug label excludes a risk "
                    "unless the full label was checked. "
                    "Use the headings: Direct answer, What the prescribing "
                    "information says, Important safety information, "
                    "and What to do next, where appropriate. "
                    "Cite supporting passages using numbered references "
                    "such as [1] and [2]. "
                    "If the evidence is insufficient, say so clearly. "
                    "For general drug interaction questions, explain what "
                    "the supplied label passages say instead of refusing "
                    "solely because the question starts with 'Can I'. "
                    "Do not make an individualized treatment decision."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        options={"temperature": 0.1},
    )

    generated_text = response["message"]["content"]
    generated_text = check_answer(generated_text)

    # The evaluator reads this Boolean flag before checking answer text.
    not_found = detect_not_found(generated_text)

    generated_text += "\n\nSources: " + "; ".join(sources)

    return Answer(
        query=query,
        mode=mode,
        text=generated_text,
        sources=sources,
        refused=False,
        not_found=not_found,
    )
