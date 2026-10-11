# Demo script (5 min) - rehearse with these exact queries

Setup before: Ollama running, index built, app open, models warmed up (ask one throwaway question first).

1. Normal, clinician mode: "What are the contraindications of ibuprofen?"  -> shows citations + source expander
2. Same drug, patient mode: "What are the side effects of metformin?"  -> plain language
3. Brand name: "What is Lipitor used for?"  -> brand resolves to atorvastatin
4. Typo: "dosage of metformine"  -> fuzzy drug detection
5. Unsafe advice: "Should I double my warfarin dose?"  -> safe response, no personal advice
6. Emergency: "I took too many pills"  -> URGENT message
7. Not in label: "Does metformin cause hair to grow back?"  -> says label doesn't mention it
8. Drug not in corpus: ask about a drug we don't have -> "not in the labels I have"

Talking points: why hybrid (BM25 + dense) + rerank, eval table (dense .860 -> hybrid .953 P@1),
citations from DailyMed with label version/date, safety design, known limits (40 drugs, local LLM).
Keep a screenshot of each answer as backup in case Ollama is slow.
