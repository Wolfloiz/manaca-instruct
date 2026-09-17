| run | protocol | category | n | mean | full_rate | n1 | n05 | n0 | n_null |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| qlora-v2 | blind | grammar_correction | 16 | 0.094 | 0.000 | 0 | 3 | 13 | 0 |
| qlora-v2 | blind | classification | 16 | 0.250 | 0.250 (4/16 correct) | 4 | 0 | 12 | 0 |
| qlora-v2 | blind | rewriting | 16 | 0.062 | 0.000 | 0 | 2 | 14 | 0 |
| qlora-v2 | blind | summarization | 16 | 0.062 | 0.000 | 0 | 2 | 14 | 0 |
| qlora-v2 | blind | simplification | 16 | 0.094 | 0.000 | 0 | 3 | 13 | 0 |
| qlora-v2 | blind | grupo_b | 24 | 0.333 | 0.083 | 2 | 12 | 10 | 0 |
| qlora-v3a | blind | grammar_correction | 16 | 0.031 | 0.000 | 0 | 1 | 15 | 0 |
| qlora-v3a | blind | classification | 16 | 0.625 | 0.625 (10/16 correct) | 10 | 0 | 6 | 0 |
| qlora-v3a | blind | rewriting | 16 | 0.094 | 0.000 | 0 | 3 | 13 | 0 |
| qlora-v3a | blind | summarization | 16 | 0.094 | 0.000 | 0 | 3 | 13 | 0 |
| qlora-v3a | blind | simplification | 16 | 0.188 | 0.000 | 0 | 6 | 10 | 0 |
| qlora-v3a | blind | grupo_b | 24 | 0.500 | 0.333 | 8 | 8 | 8 | 0 |
| qlora-v3b | blind | grammar_correction | 16 | 0.031 | 0.000 | 0 | 1 | 15 | 0 |
| qlora-v3b | blind | classification | 16 | 0.750 | 0.750 (12/16 correct) | 12 | 0 | 4 | 0 |
| qlora-v3b | blind | rewriting | 16 | 0.125 | 0.125 | 2 | 0 | 14 | 0 |
| qlora-v3b | blind | summarization | 16 | 0.156 | 0.000 | 0 | 5 | 11 | 0 |
| qlora-v3b | blind | simplification | 16 | 0.219 | 0.062 | 1 | 5 | 10 | 0 |
| qlora-v3b | blind | grupo_b | 24 | 0.438 | 0.333 | 8 | 5 | 11 | 0 |
| qlora-v3c | blind | grammar_correction | 16 | 0.094 | 0.000 | 0 | 3 | 13 | 0 |
| qlora-v3c | blind | classification | 16 | 0.625 | 0.625 (10/16 correct) | 10 | 0 | 6 | 0 |
| qlora-v3c | blind | rewriting | 16 | 0.125 | 0.062 | 1 | 2 | 13 | 0 |
| qlora-v3c | blind | summarization | 16 | 0.125 | 0.000 | 0 | 4 | 12 | 0 |
| qlora-v3c | blind | simplification | 16 | 0.156 | 0.125 | 2 | 1 | 13 | 0 |
| qlora-v3c | blind | grupo_b | 24 | 0.458 | 0.333 | 8 | 6 | 10 | 0 |
| qlora-v3b-rp11 | blind | grammar_correction | 16 | 0.375 | 0.188 | 3 | 6 | 7 | 0 |
| qlora-v3b-rp11 | blind | classification | 16 | 0.750 | 0.750 (12/16 correct) | 12 | 0 | 4 | 0 |
| qlora-v3b-rp11 | blind | rewriting | 16 | 0.219 | 0.188 | 3 | 1 | 12 | 0 |
| qlora-v3b-rp11 | blind | summarization | 16 | 0.375 | 0.188 | 3 | 6 | 7 | 0 |
| qlora-v3b-rp11 | blind | simplification | 16 | 0.344 | 0.188 | 3 | 5 | 8 | 0 |
| qlora-v3b-rp11 | blind | grupo_b | 24 | 0.438 | 0.292 | 7 | 7 | 10 | 0 |
| official-instruct | blind | grammar_correction | 16 | 0.125 | 0.000 | 0 | 4 | 12 | 0 |
| official-instruct | blind | classification | 16 | 0.250 | 0.250 (4/16 correct) | 4 | 0 | 12 | 0 |
| official-instruct | blind | rewriting | 16 | 0.000 | 0.000 | 0 | 0 | 16 | 0 |
| official-instruct | blind | summarization | 16 | 0.031 | 0.000 | 0 | 1 | 15 | 0 |
| official-instruct | blind | simplification | 16 | 0.031 | 0.000 | 0 | 1 | 15 | 0 |
| official-instruct | blind | grupo_b | 24 | 0.333 | 0.125 | 3 | 10 | 11 | 0 |

### qlora-v2 → qlora-v3a

| category | improved | worsened | tied | not comparable |
|---|---:|---:|---:|---:|
| grammar_correction | 0 | 2 | 14 | 0 |
| classification | 8 | 2 | 6 | 0 |
| rewriting | 1 | 0 | 15 | 0 |
| summarization | 2 | 1 | 13 | 0 |
| simplification | 5 | 2 | 9 | 0 |
| grupo_b | 7 | 1 | 16 | 0 |

### qlora-v3a → qlora-v3b

| category | improved | worsened | tied | not comparable |
|---|---:|---:|---:|---:|
| grammar_correction | 1 | 1 | 14 | 0 |
| classification | 5 | 3 | 8 | 0 |
| rewriting | 2 | 2 | 12 | 0 |
| summarization | 4 | 2 | 10 | 0 |
| simplification | 3 | 3 | 10 | 0 |
| grupo_b | 2 | 5 | 17 | 0 |

### qlora-v3b → qlora-v3c

| category | improved | worsened | tied | not comparable |
|---|---:|---:|---:|---:|
| grammar_correction | 2 | 0 | 14 | 0 |
| classification | 1 | 3 | 12 | 0 |
| rewriting | 2 | 2 | 12 | 0 |
| summarization | 1 | 2 | 13 | 0 |
| simplification | 2 | 5 | 9 | 0 |
| grupo_b | 3 | 2 | 19 | 0 |

### qlora-v3b → qlora-v3b-rp11

| category | improved | worsened | tied | not comparable |
|---|---:|---:|---:|---:|
| grammar_correction | 8 | 0 | 8 | 0 |
| classification | 0 | 0 | 16 | 0 |
| rewriting | 2 | 0 | 14 | 0 |
| summarization | 8 | 3 | 5 | 0 |
| simplification | 5 | 3 | 8 | 0 |
| grupo_b | 5 | 6 | 13 | 0 |

### qlora-v2 → qlora-v3b-rp11

| category | improved | worsened | tied | not comparable |
|---|---:|---:|---:|---:|
| grammar_correction | 8 | 2 | 6 | 0 |
| classification | 9 | 1 | 6 | 0 |
| rewriting | 4 | 1 | 11 | 0 |
| summarization | 8 | 1 | 7 | 0 |
| simplification | 8 | 2 | 6 | 0 |
| grupo_b | 8 | 5 | 11 | 0 |

Files: eval/results/qlora-v2-blind.jsonl, eval/results/qlora-v3a-blind.jsonl, eval/results/qlora-v3b-blind.jsonl, eval/results/qlora-v3c-blind.jsonl, eval/results/qlora-v3b-rp11-blind.jsonl, eval/results/official-instruct-blind.jsonl

Means include partial credit (0.5); `full_rate` counts only answers graded 1.
