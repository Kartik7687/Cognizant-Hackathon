# Evaluation summary

- Total gold questions: 62
- Answerable questions evaluated: 43
- Unsafe questions in gold set: 12

## Retrieval ablation

| Mode | n | P@1 | P@3 | P@5 | R@5 | Hit@1 | Hit@3 | Hit@5 | MRR | Latency (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| dense | 43 | 0.767 | 0.380 | 0.274 | 0.953 | 0.767 | 0.884 | 0.953 | 0.837 | 0.030 |
| bm25 | 43 | 0.558 | 0.287 | 0.205 | 0.779 | 0.558 | 0.721 | 0.791 | 0.652 | 0.001 |
| hybrid | 43 | 0.744 | 0.357 | 0.265 | 0.919 | 0.744 | 0.860 | 0.930 | 0.816 | 0.027 |
| hybrid_rerank | 43 | 0.442 | 0.302 | 0.223 | 0.837 | 0.442 | 0.744 | 0.837 | 0.597 | 8.351 |

Drug-detection accuracy: **1.000**

## Generation and guardrail evaluation
