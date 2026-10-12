
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

# Clearly unrelated requests that should not enter drug-label generation.
OUT_OF_SCOPE_PATTERNS = [
    r"\bgun\b",
    r"\bweapon(s)?\b",
    r"\bweather\b",
    r"\bwrite\s+(me\s+)?a\s+poem\b",
    r"\bsolve\s+(this\s+)?math(s)?\b",
]


# Symptom questions need a safe response, not a guessed drug recommendation.
SYMPTOM_PATTERNS = [
    r"\bcold\b",
    r"\bfever\b",
    r"\bcough\b",
    r"\bheadache\b",
    r"\bsore throat\b",
    r"\brunny nose\b",
    r"\bbody ache(s)?\b",
    r"\bnausea\b",
    r"\bvomit(ing)?\b",
]


# These are warning signs in generated text, not a complete medical safety filter.
UNSAFE_INSTRUCTION_PATTERNS = [
    r"\bdiscontinue\b.{0,100}\bimmediately\b",
    r"\bstop taking\b",
    r"\bdouble your dose\b",
    r"\bincrease your dose\b",
    r"\bchange your dose\b",
    r"\bstart taking\b",
]


def clean_citations(text, n_sources):
    """Keep only valid [1]..[n] citations and remove label section numbers."""
    def fix(match):
        keep = []
        for token in re.findall(r"\d+(?:\.\d+)?", match.group(1)):
            if (
                "." not in token
                and 1 <= int(token) <= n_sources
                and int(token) not in keep
            ):
                keep.append(int(token))
        return "".join(f"[{number}]" for number in keep)

    return re.sub(
        r"\[(\d+(?:\.\d+)?(?:\s*,\s*\d+(?:\.\d+)?)*)\]",
        fix,
        text,
    )


def question_names_a_drug(query, hits):
    """Check whether the query mentions a retrieved drug name or alias."""
    import difflib

    names = set()

    for hit in hits:
        chunk = hit.chunk
        for name in [chunk.drug_name, *(chunk.aliases or [])]:
            names.update(
                word
                for word in re.findall(r"[a-z0-9]+", (name or "").lower())
                if len(word) > 3
            )

    words = [
        word
        for word in re.findall(r"[a-z0-9]+", (query or "").lower())
        if len(word) > 3
    ]

    return any(
        difflib.get_close_matches(word, names, n=1, cutoff=0.8)
        for word in words
    )


def is_out_of_scope(query):
    """Identify obvious requests unrelated to drug information."""
    text = (query or "").lower().strip()
    return any(re.search(pattern, text) for pattern in OUT_OF_SCOPE_PATTERNS)


def is_symptom_question(query):
    """Identify common symptom-based requests for safe handling."""
    text = (query or "").lower().strip()
    return any(re.search(pattern, text) for pattern in SYMPTOM_PATTERNS)


def detect_not_found(text):
    """Return True when an answer indicates missing information."""
    if not text:
        return False

    text = text.lower()
    return any(re.search(pattern, text) for pattern in NOT_FOUND_PATTERNS)


def _shorten(text, limit=900):
    """Shorten long context at a word boundary."""
    if len(text) <= limit:
        return text

    return text[:limit].rsplit(" ", 1)[0] + " ..."


def _unique_sources(hits):
    """Return unique source citations in retrieval order."""
    sources = []

    for hit in hits:
        citation = format_citation(hit.chunk)
        if citation not in sources:
            sources.append(citation)

    return sources


def _safe_answer(query, mode, text, refused=False, not_found=False, sources=None):
    """Build a consistent Answer object."""
    return Answer(
        query=query,
        mode=mode,
        text=text,
        sources=sources or [],
        refused=refused,
        not_found=not_found,
    )


def answer(query, hits, mode="patient") -> Answer:
    """Generate a drug-information answer grounded in retrieved label passages."""

    # 1. Check for emergencies before any generation.
    safety_message = check_question(query)

    if safety_message:
        return _safe_answer(
            query,
            mode,
            safety_message,
            refused=True,
        )

    hits = hits or []
    query_text = (query or "").strip()

    if not query_text:
        return _safe_answer(
            query,
            mode,
            "Please enter a question.",
            not_found=True,
        )

    # 2. Clearly unrelated requests should not use drug labels or the LLM.
    if is_out_of_scope(query_text):
        return _safe_answer(
            query,
            mode,
            "This assistant answers questions about drug documentation. "
            "Please ask a question about a specific medicine or its prescribing information.",
            not_found=True,
        )

    # 3. Do not recommend medicines for symptoms without clinical assessment.
    if is_symptom_question(query_text):
        return _safe_answer(
            query,
            mode,
            "I can't diagnose the cause of your symptoms or recommend a "
            "specific medicine for you. A doctor or pharmacist can help "
            "you choose appropriate care. Seek urgent medical help if you "
            "have difficulty breathing, chest pain, confusion, or severe "
            "or rapidly worsening symptoms.",
            refused=True,
        )

    # 4. Do not make individualized medication decisions.
    advice_message = check_advice(query_text)

    if advice_message:
        return _safe_answer(
            query,
            mode,
            advice_message,
            refused=True,
        )

    # 5. No retrieved evidence means no LLM call and no invented sources.
    if not hits:
        return _safe_answer(
            query,
            mode,
            "I could not find relevant information in the drug labels "
            "available to this assistant. This does not mean the drug has "
            "no prescribing information. Please consult a doctor or pharmacist.",
            not_found=True,
        )

    # 6. Prevent unrelated retrieved passages from being treated as evidence.
    if not question_names_a_drug(query_text, hits):
        return _safe_answer(
            query,
            mode,
            "I couldn't identify a medicine relevant to your question. "
            "This assistant answers questions about drug documentation. "
            "Please name a medicine covered by the available labels.",
            not_found=True,
        )

    # 7. Generate an answer using only the retrieved documentation.
    context = format_context(hits)

    prompt = get_prompt(
        mode=mode,
        context=context,
        question=query_text,
    )

    import ollama

    response = ollama.chat(
        model="llama3.2",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful drug-documentation assistant. "
                    "Use only the supplied passages. Do not invent facts, "
                    "dosages, contraindications, interactions, or warnings. "
                    "Never tell a patient to stop, start, or change a medicine "
                    "based on your own judgment. Do not make an individualized "
                    "treatment decision. Distinguish supported facts from "
                    "missing evidence. Cite factual claims using the supplied "
                    "passage numbers, such as [1] and [2]. Never use label "
                    "section numbers as citations. If the passages do not "
                    "answer the question, say that the evidence is insufficient."
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

    # 8. If output contains a high-risk treatment instruction, use a safe
    # fallback instead of displaying that instruction.
    if any(
        re.search(pattern, generated_text, re.IGNORECASE | re.DOTALL)
        for pattern in UNSAFE_INSTRUCTION_PATTERNS
    ):
        generated_text = (
            "I couldn't produce a sufficiently safe answer from the "
            "available passages. Do not change or stop a prescribed "
            "medicine based only on this chatbot response. Please consult "
            "your doctor or pharmacist for guidance."
        )

    # 9. Keep source references only for the drug-related answer.
    sources = _unique_sources(hits)
    not_found = detect_not_found(generated_text)

    generated_text += "\n\nSources: " + "; ".join(sources)

    return _safe_answer(
        query,
        mode,
        generated_text,
        not_found=not_found,
        sources=sources,
    )
