| run | protocol | category | n | mean | full_rate | n1 | n05 | n0 | n_null |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| qlora-v3b-dev | blind | grammar_correction | 10 | 0.150 | 0.100 | 1 | 1 | 8 | 0 |
| qlora-v3b-dev | blind | classification | 10 | 0.100 | 0.100 (1/10 correct) | 1 | 0 | 9 | 0 |
| qlora-v3b-dev | blind | rewriting | 10 | 0.200 | 0.100 | 1 | 2 | 7 | 0 |
| qlora-v3b-dev | blind | summarization | 10 | 0.200 | 0.100 | 1 | 2 | 7 | 0 |
| qlora-v3b-dev | blind | simplification | 10 | 0.150 | 0.100 | 1 | 1 | 8 | 0 |
| qlora-v3b-dev-rp11 | blind | grammar_correction | 10 | 0.250 | 0.200 | 2 | 1 | 7 | 0 |
| qlora-v3b-dev-rp11 | blind | classification | 10 | 0.300 | 0.300 (3/10 correct) | 3 | 0 | 7 | 0 |
| qlora-v3b-dev-rp11 | blind | rewriting | 10 | 0.450 | 0.400 | 4 | 1 | 5 | 0 |
| qlora-v3b-dev-rp11 | blind | summarization | 10 | 0.350 | 0.200 | 2 | 3 | 5 | 0 |
| qlora-v3b-dev-rp11 | blind | simplification | 10 | 0.350 | 0.200 | 2 | 3 | 5 | 0 |

### qlora-v3b-dev → qlora-v3b-dev-rp11

| category | improved | worsened | tied | not comparable |
|---|---:|---:|---:|---:|
| grammar_correction | 2 | 0 | 8 | 0 |
| classification | 2 | 0 | 8 | 0 |
| rewriting | 4 | 1 | 5 | 0 |
| summarization | 2 | 0 | 8 | 0 |
| simplification | 4 | 0 | 6 | 0 |

Files: eval/results/qlora-v3b-dev-blind.jsonl, eval/results/qlora-v3b-dev-rp11-blind.jsonl

Means include partial credit (0.5); `full_rate` counts only answers graded 1.
