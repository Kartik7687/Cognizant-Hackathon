# Evaluation summary

- Total gold questions: 62
- Answerable questions evaluated: 43
- Unsafe questions excluded: 12

## Retrieval ablation

| mode | n | P@1 | P@3 | P@5 | R@5 | Hit@1 | Hit@3 | Hit@5 | MRR | latency(s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| dense | 43 | 0.86 | 0.674 | 0.54 | 0.977 | 0.86 | 0.977 | 0.977 | 0.915 | 0.027 |
| bm25 | 43 | 0.744 | 0.566 | 0.442 | 0.907 | 0.744 | 0.907 | 0.907 | 0.810 | 0.000 |
| hybrid | 43 | 0.953 | 0.690 | 0.558 | 0.977 | 0.953 | 0.977 | 0.977 | 0.965 | 0.021 |

Drug-detection accuracy: **1.000**