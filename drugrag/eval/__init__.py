"""Evaluation (owner: Akansha).

Retrieval ablation loop (rows of the results table):
    for mode in drugrag.retrieval.MODES:
        res = retriever.retrieve(q, mode=mode, top_k=5)   # compare res.hits[i].chunk.chunk_id with the gold chunk/section
Also run with section_boost=False and drugs=[] (filter off) to show what each component adds.
"""
