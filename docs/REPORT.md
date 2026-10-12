# Drug Documentation Q&A Chatbot: Technical Report

Cognizant NPN hackathon, use case 8. Team: Kartik Sharma (retrieval, integration), Shruti Rekha Sahoo (data pipeline), Ankita Giri (generation, safety), Akansha Priyadarshini (evaluation, UI). Mentor: Rajaneekanta Mishra.

## 1. Problem
Clinicians and patients need quick, trustworthy answers from drug labels (indications, dosage, contraindications, warnings, interactions). Labels are long and hard to search. A chatbot must answer only from the label, show where each statement comes from, and refuse to give personal medical advice.

## 2. Approach
1. **Data.** Official DailyMed SPL XML labels for 40 commonly used drugs. Each label is split by LOINC section code into section-level chunks (734 chunks, at most 1,500 characters each). Every chunk stores drug, section, label version, effective date, LOINC code and source URL (`docs/chunk_schema.md`). A validator checks every chunk.
2. **Retrieval.** Dense embeddings (bge-small) and BM25 are fused with reciprocal rank fusion. Drug names (generic, brand, and typos) are detected and used to filter chunks. A section-intent boost favours the section a question asks about (for example "contraindications"). An optional cross-encoder reranker (bge-reranker-base) is available.
3. **Generation.** A local Llama 3.2 model (Ollama) answers only from the retrieved passages, using numbered citations. Two modes: clinician (technical) and patient (plain language). The answer follows the mentor's format and ends with a Sources line (drug, label version, section, effective date).
4. **Safety.** Emergency phrasings (for example "I took too many pills") return an urgent message with the emergency number. Personal-advice questions (for example "Should I double my warfarin dose?") return a template that does not give advice, shows what the label says, and directs the user to a doctor or pharmacist. Questions with no recognisable covered drug, or no relevant passages, return a clear "not found" reply and never reach the model.
5. **Interface.** A Streamlit chat app with mode selection, retrieval settings, cited sources with DailyMed links, and highlighting of the supporting sentences.

## 3. Evaluation
A 62-question gold set: 43 answerable, 12 unsafe, 7 unanswerable. Retrieval is scored with Precision@k, Recall@k, Hit@k and MRR against the gold drug and section. Generation is scored for citation presence and accuracy, refusals, and answer correctness (LLM-as-judge).

### Retrieval (43 answerable questions, bge-small)
| Mode | P@1 | P@3 | R@5 | MRR | Latency (s) |
|---|---:|---:|---:|---:|---:|
| dense | 0.791 | 0.388 | 0.953 | 0.854 | 0.02 |
| bm25 | 0.581 | 0.279 | 0.779 | 0.664 | 0.001 |
| **hybrid** (default) | 0.767 | 0.364 | 0.919 | 0.833 | 0.02 |
| hybrid + rerank | 0.744 | 0.364 | 0.919 | 0.806 | 5.2 |

Drug-detection accuracy is 1.000. Dense and hybrid differ by about one question out of 43. Hybrid is the default because BM25 helps with exact drug and section names. The reranker did not help on this corpus and adds about 5 seconds, so it is off by default. A first version of the reranker scored only the chunk text and reached P@1 0.442. Adding the drug and section name to the reranker input raised it to 0.744. That was a useful failure to find and fix.

### Generation and guardrails (full run, before the final citation clean-up)
| Measure | Clinician | Patient |
|---|---:|---:|
| Citation present | 0.605 | 0.628 |
| Citation accuracy | 0.717 | 0.725 |
| Refusal on unsafe questions | 1.000 | 1.000 |
| Not-found on unanswerable questions | 1.000 | 1.000 |
| False refusals | 0.000 | 0.000 |

A later 15-question run with the final prompt raised citation presence to about 0.87 to 0.93. Rerun the full evaluation (see README) and refresh this table with `drugrag/eval/results/summary.md` before presenting.

Notes on reading these numbers:
- The safety rules were tuned on the same unsafe questions, so 12 of 12 overstates coverage on unseen phrasings.
- Unanswerable questions mostly name drugs we do not cover, which is an easy case.
- The correctness score from the small local judge is unreliable. It compares answers with short reference answers and penalises correct extra detail. We recommend reading a hand-graded sample alongside it.

## 4. Failure analysis
- **Retrieval misses (hybrid).** Some questions retrieve the right drug but a neighbouring section: "contraindications of ibuprofen" (gold: Warnings and Precautions, because the label lists them there), "liver warning for acetaminophen" (top hit is Boxed Warning), and apixaban questions where Warnings and Contraindications overlap.
- **Section naming.** Labels name the same section differently (Warnings, Warnings and Precautions, Precautions). We group them in the metrics.
- **Generation.** The 3B model sometimes copied the label's own section numbers (for example [2.1]) as citations, repeated the question, or added filler such as "no information is provided" next to the information itself. We added citation clean-up (invalid numbers are removed) and prompt rules. It also once listed a risk factor as a contraindication. Larger models would likely do better.

## 5. Limitations
- Coverage is 40 drugs. Questions about other drugs get a "cannot identify a covered drug" reply.
- Furosemide and metoprolol have no Boxed Warning chunk and enalapril has no Warnings chunk, because of how those labels are structured in the source data.
- Safety detection is rule-based and covers defined phrasings. It is a guardrail, not a clinical triage system.
- Answer quality is bounded by a small local model. Always read the cited label passage.
- 20 of the 62 gold questions and 7 pending questions are not yet manually verified.
- The tool is not medical advice.

## 6. Reproduce
See `README.md`: install requirements, build the index from `data/chunks_clean.jsonl`, run the app, run the evaluation. All tests run offline: `python -m pytest -q`.
