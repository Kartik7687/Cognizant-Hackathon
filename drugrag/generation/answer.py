from dataclasses import dataclass, field
import re


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


def clean_citations(text, n_sources):
    """Keep only valid [1]..[n] citations; drop label section numbers like [2.1] or [17]."""
    def fix(m):
        keep = []
        for tok in re.findall(r"\d+(?:\.\d+)?", m.group(1)):
            if "." not in tok and 1 <= int(tok) <= n_sources and int(tok) not in keep:
                keep.append(int(tok))
        return "".join(f"[{k}]" for k in keep)

    return re.sub(r"\[(\d+(?:\.\d+)?(?:\s*,\s*\d+(?:\.\d+)?)*)\]", fix, text)


def question_names_a_drug(query, hits):
    """True if the question mentions (or closely misspells) a drug/brand of the retrieved chunks.

    When no drug is detected the retriever searches every label and returns unrelated
    passages, which must not be sent to the LLM (e.g. a question about a drug we do not have).
    """
    import difflib

    names = set()
    for hit in hits:
        c = hit.chunk
        for n in [c.drug_name, *(c.aliases or [])]:
            names.update(w for w in re.findall(r"[a-z0-9]+", (n or "").lower()) if len(w) > 3)
    words = [w for w in re.findall(r"[a-z0-9]+", (query or "").lower()) if len(w) > 3]
    return any(difflib.get_close_matches(w, names, n=1, cutoff=0.8) for w in words)


def detect_not_found(text: str) -> bool:
    """Return True when the answer indicates missing information."""
    if not text:
        return False

    text = text.lower()
    return any(
        re.search(pattern, text)
        for pattern in NOT_FOUND_PATTERNS
    )


def _shorten(text, limit=900):
    """Keep advice answers short: cut long label text at a word boundary."""
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + " ..."


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
            label_context = format_context(hits[:2])
            label_context = _shorten(label_context)
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

    if not question_names_a_drug(query, hits):
        text = (
            "Direct answer: I could not identify a drug from the labels I have "
            "available in your question, so I cannot answer it reliably. "
            "This does not mean the drug has no prescribing information.\n\n"
            "What to do next: Name one of the drugs covered by this assistant "
            "(for example metformin, ibuprofen, warfarin or atorvastatin), or consult "
            "a doctor or pharmacist.\n\n"
            "Sources: No relevant label passages found"
        )
        return Answer(query=query, mode=mode, text=text, sources=[],
                      refused=False, not_found=True)

    context = format_context(hits)

    prompt = get_prompt(
        mode=mode,
        context=context,
        question=query,
    )

    import ollama  # imported here so tests run without Ollama installed

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
    generated_text = clean_citations(generated_text, len(hits))

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
