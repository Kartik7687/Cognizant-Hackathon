from dataclasses import dataclass, field

import ollama

from ..schema import format_citation
from ..retrieval.retrieve import format_context
from .prompts import get_prompt
from .safety import check_question, check_answer


@dataclass
class Answer:
    query: str
    mode: str
    text: str
    sources: list[str] = field(default_factory=list)


def answer(query, hits, mode="patient") -> Answer:
    """
    Generate a drug information answer using
    retrieved label passages and the Ollama LLM.
    """

    # Step 1: Validate the question and check for emergencies
    safety_message = check_question(query)

    if safety_message:
        return Answer(
            query=query,
            mode=mode,
            text=safety_message,
            sources=[]
        )

    # Step 2: Handle cases where no documentation was retrieved
    if not hits:
        return Answer(
            query=query,
            mode=mode,
            text=(
                "Direct answer: I could not find enough information "
                "in the available drug documentation.\n\n"
                "What to do next: Please consult a doctor or pharmacist."
            ),
            sources=[]
        )

    # Step 3: Prepare retrieved passages and citations
    context = format_context(hits)

    sources = []
    for hit in hits:
        citation = format_citation(hit.chunk)
        if citation not in sources:
            sources.append(citation)

    # Step 4: Create the prompt for the LLM
    prompt = get_prompt(
        mode=mode,
        context=context,
        question=query
    )

    
    response = ollama.chat(
        model="llama3.2",
        messages=[
            {
                "role": "system",
                "content": (
                    "Use only the supplied drug-label passages. "
"Do not invent medical facts. "
"Never contradict the supplied drug-label evidence. "
"Distinguish the label's permitted directions from exceeding "
"the maximum recommended dose. "
"If the label permits a specific dose under stated conditions, "
"explain those conditions accurately. "
"When a label allows two capsules under stated conditions, "
"report those conditions accurately instead of saying two "
"capsules are never allowed. "
"Do not imply that taking extra medicine will make it work faster. "
"Do not say the label lacks dosing information when the supplied "
"passages contain dosing instructions. "

"Do not add medical risks unless they are supported by the supplied "
"passages, and distinguish label-supported facts from uncertainty. "
"If a retrieved passage does not mention a risk, say only that the "
"provided passages do not mention it. Do not claim the entire drug "
"label excludes that risk unless the full label was checked. "
"Structure the response using these headings: "
"Direct answer, What the prescribing information "
"says, Important safety information, What to do next. "
"Cite supporting passages using their numbered "
"references, such as [1] and [2]. "
"If the evidence is insufficient, say so clearly."
                ),
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        options={"temperature": 0.1}
    )

    
    generated_text = response["message"]["content"]
    generated_text = check_answer(generated_text)

    
    return Answer(
        query=query,
        mode=mode,
        text=generated_text,
        sources=sources
    )