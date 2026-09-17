# Data Model: Data Quality & Evaluation Iteration (Manacá-Instruct-PT v3)

Extends `specs/001-manaca-instruct-tuning/data-model.md`. Entities from 001 that are unchanged (`InstructionExample`, `EvaluationResult`, `QuantizedArtifact`, `BenchmarkRecord`) are referenced, not repeated; the sections below list only what this feature adds or amends.

## EvaluationPrompt (amended)

Two **optional** fields are added to `grupo_a` rows of `data/eval/grupo_a_prompts.jsonl`. `grupo_b` rows do not carry them.

| Field | Type | Notes |
|---|---|---|
| `instruction` | string (optional) | The part of `prompt` before its first `": "`. Authored once, reviewed by the author. |
| `input` | string (optional) | The part of `prompt` after its first `": "`. |

**Validation rules (added)**:
- `instruction` and `input` are either both present or both absent on a row.
- When present, `f"{instruction}: {input}" == prompt` exactly (contract test) — the frozen `prompt` text is the source of truth; the split is an annotation of it.
- `prompt` itself MUST NOT change (FR-022). Verified property of the current file: all 80 `grupo_a` rows contain exactly one `": "`, so the split is unambiguous.
- `group` gains a third allowed value, `dev`, used only by `data/dev/dev_prompts.jsonl` (see DevelopmentPrompt). `grupo_a`/`grupo_b` rules are unchanged.

## EvaluationResult (unchanged schema; new file conventions)

The row schema in 001 is reused as-is. Conventions added by this feature, all expressed in file names and `run_id`:

| Run id / file | Meaning |
|---|---|
| `<run>` | combined (single-line) presentation — today's behaviour |
| `<run>-split` | separated presentation (`### Instrução` / `### Entrada`) via `--prompt-format split` |
| `<run>-best` | the same training run's best-by-held-out-loss epoch checkpoint |
| `eval/results/<run_id>-blind.jsonl` | blind-graded copy of `eval/results/<run_id>.jsonl` (see BlindResultFile) |

**Validation rules (added)**:
- Every new result of this feature is written to a file that did not exist before (FR-022); the four 001 files (`baseline`, `qlora-v1`, `qlora-v2`, `official-instruct`) are read-only inputs.
- `run_id` inside a `-blind` file equals the original `run_id` (the file name, not the field, carries the protocol) so `id`-level pairing between protocols is trivial.

## BlindResultFile

A copy of one `EvaluationResult` file produced by a Blind Review Session.

| Field | Type | Notes |
|---|---|---|
| `source_path` | string | `eval/results/<run_id>.jsonl` it was copied from. |
| `path` | string | `eval/results/<run_id>-blind.jsonl`. |
| `rows` | EvaluationResult[] | Identical to the source rows except `score` for `manual_review` rows, which is `null` until graded blind; `rule_based` rows keep their computed score. |

**State transitions**: `absent` → `created` (all `manual_review` scores `null`, written when a blind session first touches the run) → `partially graded` → `fully graded` (no `null` scores). A session may be interrupted and resumed; the tool only ever fills `null` scores and never overwrites a non-null one.

**Validation rules**:
- `(id, model, run_id)` set identical to the source file's.
- `source_path` MUST NOT be modified by the session (checked by comparing its SHA256 before and after).

## BlindReviewSession

One interactive grading pass (not persisted as a record; described here because its behaviour is contractual — see `contracts/blind-review-and-report.md`).

| Attribute | Notes |
|---|---|
| `inputs` | one or more `EvaluationResult` files (interleaved) |
| `shuffle_seed` | integer; presentation order = deterministic shuffle of all ungraded `manual_review` rows across inputs |
| `hidden` | `model`, `run_id`, and input file name are never shown to the reviewer |
| `outputs` | one BlindResultFile per input |

## GradingReport (derived, not stored as data)

Produced by `src/grading/report.py` from any set of `EvaluationResult` files; Markdown output. Per `(run_id, category)` with `category` ∈ the five task categories ∪ {`grupo_b`}:

| Column | Definition |
|---|---|
| `mean` | mean of non-null `score` (partial credit counts 0.5) |
| `full_rate` | share of non-null rows with `score == 1` |
| `n1`, `n05`, `n0` | counts per grade value |
| `n_null` | rows still ungraded (reported, never silently dropped) |
| `protocol` | `blind` if the file name ends in `-blind` or the run is a new candidate; otherwise `earlier (non-blind)` |

Pairwise section for every two runs sharing prompt ids: `improved` / `worsened` / `tied` counts per category (comparison on `score`, both non-null).

**Validation rules**: never mixes rows from different `run_id`s into one aggregate (001 consumer rule); the adoption rule (FR-020) is evaluated on `-blind` files only.

## PreparationReport

Written by `src/prepare_dataset.py` to `data/dataset_report.md` (Markdown) and `data/dataset_report.json` (machine-readable).

| Field | Type | Notes |
|---|---|---|
| `generated_at` | string | ISO timestamp |
| `sources` | {name → {license, rows_in, rows_kept}} | per source dataset, including `seed-llm` and any additional public dataset with its license |
| `by_category` | {category → {raw, after_filter, after_quality, after_eval_dedupe, after_dedupe, after_cap, train, validation}} | counts at each stage |
| `dropped_by_reason` | {reason → count} | reasons: `no_output`, `exclude_regex`, `label_not_in_instruction`, `missing_input`, `degenerate_output`, `overlap_with_eval`, `duplicate_triple`, `duplicate_pair`, `over_cap` |
| `fingerprints` | {`train.jsonl` → sha256, `validation.jsonl` → sha256} | what RunManifest references |
| `warnings` | string[] | one entry per category below 350 |

**Validation rules**: `sum(by_category[*].train) + sum(by_category[*].validation)` ∈ [3,000, 5,000] (FR-013); every `warnings` entry names the remedy step taken or "documented shortfall" (FR-012).

## SeedExample (InstructionExample with a reserved source)

Rows in `data/seed/classification_4class.jsonl`; same shape as `InstructionExample`.

| Field | Constraint |
|---|---|
| `id` | `seed-llm-NNNNNN`, unique |
| `source` | `seed-llm` (reserved value; `data-model.md` of 001 listed only `alpaca-pt-br` \| `canarim`, now also `seed-llm` and any admitted additional public source's name) |
| `task_category` | `classification` |
| `instruction` | exactly `Classifique a mensagem como reclamação, dúvida, elogio ou solicitação` |
| `input` | the message; non-empty |
| `output` | one of `reclamação` \| `dúvida` \| `elogio` \| `solicitação` (lowercase, exact) |

Sidecar `data/seed/README.md` (required, human-readable): generating model + version, date, usage-terms reference and the author's compatibility conclusion, generation prompt, counts generated/kept/edited/discarded, and the author's confirmation that every kept row was checked against the 16 classification evaluation messages.

**Validation rules**: ≥30 rows per label; no label >40% of the file; no `(instruction, input)` equal to an evaluation prompt's split fields; passes `is_degenerate_output == False`; the README exists and names a generating model.

## DevelopmentPrompt

Rows of `data/dev/dev_prompts.jsonl`, `EvaluationPrompt` shape with `group: "dev"`.

| Field | Constraint |
|---|---|
| `id` | `dev-<category>-NNN` |
| `group` | `dev` |
| `task_category` | one of the five |
| `prompt` / `instruction` / `input` | built from a cleaned `validation.jsonl` row: `instruction` and `input` copied, `prompt` = `f"{instruction}: {input}"` (or `instruction` alone when `input` is empty) |
| `expected` | the source row's `output` (reference for the reviewer; the label for classification) |
| `grading_method` | `rule_based` for classification, `manual_review` otherwise |
| `source_id` | the `InstructionExample.id` it came from |

**Validation rules**: exactly 10 rows per category; source rows come from `validation.jsonl` only (never `train.jsonl`); never used in the adoption decision (FR-005/FR-020).

## RunManifest

JSON at `adapters/<run_id>/run_manifest.json` with a byte-identical tracked copy at `runs/<run_id>.manifest.json` (training — `adapters/` is gitignored, `runs/` is not) or `eval/results/<run_id>.manifest.json` (evaluation). Full field list in `contracts/run-manifest-schema.md`; summary:

| Field | Training | Evaluation |
|---|---|---|
| `kind`, `run_id`, `created_at`, `git_commit`, `git_dirty`, `library_versions`, `base_model{repo_id, revision}` | yes | yes |
| `datasets[]{path, sha256, rows}` | train + validation | prompt files (+ dev file when used) |
| `config` | loaded `configs/train.yaml` | loaded inference YAML |
| `prompt_format` | `train-template` (+ `completion_only_loss` flag) | `combined` \| `split` |
| `eval_loss_by_epoch`, `best_epoch`, `checkpoints[]`, `adapter_path` | yes | — |
| `adapter_path`, `checkpoint` (when `-best`), `results_path` | — | yes |

**Validation rules**: `datasets[].sha256` MUST equal the PreparationReport fingerprints for the files used (SC-005); a manifest is written even when the run fails (with `status: failed` and the error), so a failed run is still attributable.

## CandidateRun (extends 001's FineTuningRun)

| Field | Type | Notes |
|---|---|---|
| `run_id` | string | `qlora-v3a` (data only) \| `qlora-v3b` (data + response-only objective) \| conditional `qlora-v3c..e` |
| `completion_only_loss` | boolean | `false` for v3a (v2 process), `true` for v3b |
| `adapter_path` | string | `adapters/<run_id>/` — always the **last epoch** |
| `best_epoch` | integer | from the manifest; when ≠ last epoch for v3b, the `<run_id>-best` evaluation row is mandatory (FR-018) |
| `eval_run_ids` | string[] | `<run_id>` or `<run_id>-split` per the selected presentation, plus `<run_id>-best` when applicable; each with a `-blind` graded file |
| `differs_from` | string | the single factor separating it from its comparator (`v3a` vs `qlora-v2`: data; `v3b` vs `v3a`: objective; `v3c..e` vs their base: one named factor) |

**Validation rules**: exactly two primary CandidateRuns; at most three conditional ones (FR-021); every CandidateRun starts from `menezesbruno/manaca-1b-base` (FR-017).

## AdoptionDecision

Written once to `eval/results/adoption-decision.md` (Markdown; the record the model card cites).

| Field | Notes |
|---|---|
| `presentation` | `combined` \| `split`, with the per-category v2 delta that selected it (FR-019) |
| `table` | the GradingReport output for v2, v3a, v3b, (v3b-best), official — all `-blind` |
| `rule_checks` | per candidate: classification correct ≥ 8/16; group-A `full_rate` ≥ 0.20; no category `mean` < v2's; grupo_b relative drop ≤ 10% |
| `outcome` | `adopted: <run_id>` \| `declined` (v2 remains 001's final model) |
| `attribution` | which factor each observed difference is attributed to, or "cannot attribute" |

**Validation rules**: all inputs are `-blind` files; the rule is applied as written in FR-020, no additional criteria.

## Relationships

```text
EvaluationPrompt (frozen prompt) ──(annotated by)──> instruction/input split ──(rendered by)──> prompt_format.format_prompt
EvaluationResult file <run> ──(blind session copies)──> BlindResultFile <run>-blind ──(aggregated by)──> GradingReport
GradingReport (v2, v3a, v3b, v3b-best, official; all -blind) ──(FR-020 rule)──> AdoptionDecision

public sources + SeedExample[] ──(filters, quality, dedupe, cap)──> InstructionExample[] (train / validation) + PreparationReport
validation.jsonl ──(seeded sample, 10/category)──> DevelopmentPrompt[]
train.jsonl + validation.jsonl ──(fingerprints)──> RunManifest(training) ──(one per)──> CandidateRun ──(evaluated as)──> EvaluationResult files + RunManifest(evaluation)
CandidateRun.best_epoch ──(when ≠ last)──> <run_id>-best evaluation
```
