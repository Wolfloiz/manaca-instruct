| run | protocol | category | n | mean | full_rate | n1 | n05 | n0 | n_null |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| qlora-v2 | blind | grammar_correction | 16 | 0.438 | 0.375 | 6 | 2 | 8 | 0 |
| qlora-v2 | blind | classification | 16 | 0.250 | 0.250 (4/16 correct) | 4 | 0 | 12 | 0 |
| qlora-v2 | blind | rewriting | 16 | 0.062 | 0.000 | 0 | 2 | 14 | 0 |
| qlora-v2 | blind | summarization | 16 | 0.062 | 0.000 | 0 | 2 | 14 | 0 |
| qlora-v2 | blind | simplification | 16 | 0.094 | 0.000 | 0 | 3 | 13 | 0 |
| qlora-v2 | blind | grupo_b | 24 | 0.333 | 0.083 | 2 | 12 | 10 | 0 |
| qlora-v2-split | blind | grammar_correction | 16 | 0.344 | 0.312 | 5 | 1 | 10 | 0 |
| qlora-v2-split | blind | classification | 16 | 0.188 | 0.188 (3/16 correct) | 3 | 0 | 13 | 0 |
| qlora-v2-split | blind | rewriting | 16 | 0.062 | 0.000 | 0 | 2 | 14 | 0 |
| qlora-v2-split | blind | summarization | 16 | 0.156 | 0.000 | 0 | 5 | 11 | 0 |
| qlora-v2-split | blind | simplification | 16 | 0.062 | 0.000 | 0 | 2 | 14 | 0 |
| qlora-v2-split | blind | grupo_b | 24 | 0.271 | 0.042 | 1 | 11 | 12 | 0 |

### qlora-v2 → qlora-v2-split

| category | improved | worsened | tied | not comparable |
|---|---:|---:|---:|---:|
| grammar_correction | 4 | 6 | 6 | 0 |
| classification | 0 | 1 | 15 | 0 |
| rewriting | 1 | 1 | 14 | 0 |
| summarization | 3 | 0 | 13 | 0 |
| simplification | 1 | 2 | 13 | 0 |
| grupo_b | 3 | 6 | 15 | 0 |

Files: eval/results/qlora-v2-blind.jsonl, eval/results/qlora-v2-split-blind.jsonl

Means include partial credit (0.5); `full_rate` counts only answers graded 1.
