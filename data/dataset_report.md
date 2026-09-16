# Dataset preparation report

Generated 2026-09-16T19:29:34Z (seed 42). Stage semantics: `raw` = keyword-matched public rows with a usable output (after per-source exclusions); `after_filter` = raw + seed rows; then quality filter, eval-overlap check, dedupe, cap, split.

## Sources

| source | license | rows in | rows kept |
|---|---|---:|---:|
| alpaca-pt-br | CC BY-NC-4.0 | 51759 | 1394 |
| canarim | CC BY-NC-4.0 | 316413 | 2161 |
| seed-llm | author-reviewed synthetic (see data/seed/README.md) | 197 | 197 |

## Per category

| category | raw | after_filter | after_quality | after_eval_dedupe | after_dedupe | after_cap | train | validation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| classification | 9232 | 9429 | 9426 | 9426 | 7105 | 1000 | 908 | 92 |
| grammar_correction | 394 | 394 | 394 | 394 | 394 | 394 | 355 | 39 |
| rewriting | 1689 | 1689 | 1689 | 1689 | 1689 | 1000 | 906 | 94 |
| simplification | 380 | 380 | 379 | 379 | 358 | 358 | 311 | 47 |
| summarization | 3386 | 3386 | 3375 | 3375 | 2926 | 1000 | 897 | 103 |

## Dropped by reason

| reason | rows |
|---|---:|
| no_output | 3 |
| exclude_regex | 296 |
| label_not_in_instruction | 8229 |
| missing_input | 117 |
| degenerate_output | 15 |
| overlap_with_eval | 0 |
| duplicate_triple | 2684 |
| duplicate_pair | 107 |
| over_cap | 8720 |

## Fingerprints

- `data/train.jsonl`: `9b3d3ca3513677bd7f4cf56c32b298cabf4c12f698a0276b31c71143e1107f1d`
- `data/validation.jsonl`: `4d0e980162dcd7424c3a56972c1f49dd989f6302799b6caa781d0603563528f2`

## Warnings

- none

## Grammar audit (T038, 2026-09-16)

Sample: 30 `grammar_correction` rows from `data/train.jsonl` (fingerprint `9b3d3ca3…`), `random.Random(1).shuffle` as in quickstart.md US2 step 5. Ids, in sample order: alpaca-pt-br-021190, 046587, 029419, 003539, 045345, 006550, 016187, 001275, 010392, 040338, 034300, 034481, 007871, 008346, 012568, 050521, 050898, 005976, 000238, 038038, 014045, 016472, 027759, 042212, 028099, 025352, 001043, 034596, 006004, 011341.

Count (made with AI assistance — Claude Code — over the printed sample; the author accepted the number without re-counting):

| kind | rows | sample positions |
|---|---:|---|
| genuine correction/editing of a given text | **20** | 1, 4, 9, 11–20, 22, 23, 26–30 |
| grammaticality judgment (yes/no, 0/1, pick the spelling) — language task, not a correction | 4 | 2, 3, 7, 8 |
| grammatical analysis / parsing / explanation | 4 | 6, 10, 21, 25 |
| rewriting "with the same meaning" | 2 | 5, 24 |

**Result: 20/30 genuine corrections (24/30 if grammaticality judgments are counted) — below the 27/30 threshold of spec.md US2 scenario 4 / SC-003.** Documented shortfall.

Context: the first v3 build scored ~14/30 on the same sampling (8 of the 30 were film/book/product *reviews* matched by `revis*`, plus rule lists and word-ordering exercises with empty `input`); the filter was tightened in this build (no `revis*` keyword, sentence-building verbs excluded, `input` required), taking grammar from 676 to 394 rows. The remaining off-task families in the full category are grammatical analysis (19 rows), yes/no grammaticality judgments (20) and rewriting-with-same-meaning (6). Excluding all three would leave 349 rows, one below the 350 category minimum (FR-012), so they were kept and the shortfall is recorded here instead of admitting an additional public source.
