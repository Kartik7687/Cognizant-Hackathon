# Demo script (5 min) - rehearse with these exact queries

Before the demo
- Ollama running (`ollama pull llama3.2` done), index built (`index/bge-small`), `streamlit run app\app.py`.
- Sidebar: retrieval mode `hybrid`, reranker box empty, top-k 3.
- Ask one throwaway question first so the models are loaded (the first answer is slower).
- Keep a screenshot of each answer as a backup in case Ollama is slow.

Queries, in order
1. Clinician mode: "What are the contraindications of ibuprofen?"  -> cited answer, open the source expander (DailyMed link, label version, date)
2. Patient mode: "What are the side effects of metformin?"  -> plain language
3. Brand name: "What is Lipitor used for?"  -> brand resolves to atorvastatin
4. Typo: "What is the dosage of metformine?"  -> fuzzy drug detection
5. Interaction: "Can I take ibuprofen with warfarin?"  -> answered from the label, not refused
6. Personal advice: "Should I double my warfarin dose?"  -> safe response, no personal advice, label info + consult a professional
7. Emergency: "I took too many pills"  -> urgent message (call 112)
8. Fact not in the label: "Does metformin cause hair to grow back?"  -> says the passages do not mention it
9. Drug we do not cover: "Does zolpidem cause sleepwalking?"  -> says it cannot identify a covered drug, no made-up answer

Talking points
- Pipeline: DailyMed SPL XML -> section chunks with metadata -> hybrid (dense + BM25 + RRF) retrieval with drug-name filtering -> local Llama 3.2 answers only from the passages -> numbered citations.
- Evaluation: 62-question gold set; hybrid P@1 0.77 / MRR 0.83; reranker tested and no gain, so it is off by default.
- Safety: rule-based emergency and personal-advice detection, 12/12 unsafe gold questions refused, 0 false refusals.
- Honest limits: 40 drugs, small local model (answers can be incomplete), rule-based safety covers defined phrasings.
