# Contract: Blind Review CLI and Grading Report

Governs `src/grading/review_cli.py` (extended) and `src/grading/report.py` (new). Consumed by the author (grading) and by `MODEL_CARD.md` / `eval/results/adoption-decision.md` (report output). Builds on `specs/001-manaca-instruct-tuning/contracts/evaluation-results-schema.md`, which remains in force.

## `python -m src.grading.review_cli` (extended)

```
python -m src.grading.review_cli RESULTS... [--blind] [--shuffle-seed N] [--interleave]
```

| Argument | Rule |
|---|---|
| `RESULTS...` | one or more `eval/results/<run_id>.jsonl` files. Without `--interleave`, exactly one is accepted (today's behaviour, extended with output redirection below). |
| `--blind` | the prompt shown to the reviewer MUST NOT contain `model`, `run_id`, or the input file name; it shows only the position counter, `task_category`, `prompt`, `expected` (when non-null) and `output`. |
| `--shuffle-seed N` | presentation order is a deterministic shuffle (seed `N`) of all rows still to grade, across all inputs. Required when `--interleave` is used. |
| `--interleave` | rows from all inputs are merged into one session; each grade is routed back to the row's origin by `(input file, id, model, run_id)`. |

### Output rules

- The tool MUST NOT write to any input file. For each input `eval/results/<run_id>.jsonl` it writes `eval/results/<run_id>-blind.jsonl` (creating it as a full copy with `manual_review` scores reset to `null` if it does not exist; resuming from it if it does).
- Only `null` scores are ever filled; an existing non-null score in the `-blind` file is never overwritten (re-running the tool grades only what is left).
- Every write happens immediately after each accepted grade (one row at a time), never buffered to the end.
- Accepted grade values: `1`, `0.5`, `0`, `s` (skip — leaves `null`), `q` (quit — session resumable).
- On exit the tool prints, per input, `graded / remaining` counts and the SHA256 of the untouched input file before and after (must be equal).

### Guarantees tested

- Blind mode output contains no `model=` / `run_id=` text (unit test on `_prompt_for_score`).
- Interleaved grades land in the right file and row (unit test with two synthetic files and a scripted `input_fn`).
- Source files are byte-identical after a session (contract test).

## `python -m src.grading.report` (new)

```
python -m src.grading.report RESULTS... [--pair RUN_A RUN_B]... [--markdown-out PATH]
```

| Argument | Rule |
|---|---|
| `RESULTS...` | any number of `EvaluationResult` files (original or `-blind`). |
| `--pair A B` | adds a pairwise section for runs `A` and `B` (by `run_id` as found in the files, disambiguated by file name when both an original and a `-blind` copy are given). May repeat. |
| `--markdown-out` | also writes the Markdown to a file; stdout always gets it. |

### Output format (Markdown)

1. **Per-run table**, one row per `(run, category)`, categories = the five task categories then `grupo_b`:

   | run | protocol | category | n | mean | full_rate | n1 | n05 | n0 | n_null |

   - `protocol` = `blind` when the file name ends with `-blind.jsonl` or the run id starts with `qlora-v3`; otherwise `earlier (non-blind)`.
   - `mean` and `full_rate` computed over non-null scores only; `n_null` reported, never dropped.
   - For `classification`, `full_rate` equals accuracy and the table also prints `correct/16` explicitly, since FR-020 uses that count.
2. **Pairwise section** per `--pair`: per category `improved` / `worsened` / `tied` / `not comparable` (either side null), comparing `score` row by row on shared `id`s.
3. **Footnotes**: which files were used, and the sentence "Means include partial credit (0.5); `full_rate` counts only answers graded 1." verbatim, so the model card cannot omit it.

### Guarantees tested

- Given two synthetic files with known grades, the table and pairwise counts match hand-computed values (unit test).
- Rows from different `run_id`s are never aggregated together (unit test with a file containing two run ids raises).
- Presence of `null` scores is visible in `n_null` and does not change `mean` (unit test).
