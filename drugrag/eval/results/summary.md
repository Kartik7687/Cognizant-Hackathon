# Evaluation summary

Gold questions: 62

## Retrieval ablation

| mode | n | P@1 | P@3 | P@5 | R@5 | Hit@1 | Hit@3 | Hit@5 | MRR | latency(s) |
|---|---|---|---|---|---|---|---|---|---|---|
| dense | 43 | 0.791 | 0.388 | 0.27 | 0.953 | 0.791 | 0.907 | 0.953 | 0.854 | 0.017 |
| bm25 | 43 | 0.581 | 0.279 | 0.2 | 0.779 | 0.581 | 0.721 | 0.791 | 0.664 | 0.001 |
| hybrid | 43 | 0.767 | 0.364 | 0.26 | 0.919 | 0.767 | 0.884 | 0.93 | 0.833 | 0.017 |
| hybrid_rerank | 43 | 0.744 | 0.364 | 0.256 | 0.919 | 0.744 | 0.814 | 0.93 | 0.806 | 4.942 |

Drug-detection accuracy: **1.000**

## Generation, citations and guardrails

### clinician mode

- answerable_n: 43
- answer_correctness_0_2_avg: 0.930
- answer_correct_pct (score=2): 0.047
- citation_present_rate: 0.721
- citation_accuracy: 0.732
- false_refusal_rate: 0.000
- unanswerable_n: 7
- not_found_rate_on_unanswerable: 0.429
- unsafe_n: 12
- refusal_rate_on_unsafe: 1.000
- avg_latency_s: 8.311

### patient mode

- answerable_n: 43
- answer_correctness_0_2_avg: 0.930
- answer_correct_pct (score=2): 0.093
- citation_present_rate: 0.349
- citation_accuracy: 0.933
- false_refusal_rate: 0.000
- unanswerable_n: 7
- not_found_rate_on_unanswerable: 0.429
- unsafe_n: 12
- refusal_rate_on_unsafe: 1.000
- avg_latency_s: 3.286
