"""Generation and safety (owner: Ankita).

Contract:
    answer(query: str, hits: list[Hit], mode: "clinician" | "patient") -> Answer
Use drugrag.retrieval.format_context(hits) to build the numbered context for the prompt, and
drugrag.schema.format_citation(chunk) for the Sources line. Output follows the mentor's 5-part format:
Direct answer / What the prescribing information says / Important safety information /
What to do next / Sources.
"""
