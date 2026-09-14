# Data Model: Manacá-Instruct-PT (Core Lifecycle v1)

Derived from spec.md's Key Entities section and the FR-002/FR-003/FR-004/FR-006/FR-007 requirements. This is a local ML pipeline, not an application with a persistent database — these are file-backed record shapes (JSONL/YAML), not database tables.

## InstructionExample

Represents one training example in the fine-tuning dataset (`data/train.jsonl`, `data/validation.jsonl`).

| Field | Type | Notes |
|---|---|---|
| `id` | string | Stable unique identifier, e.g. `alpaca_pt_br-000123` or `canarim-004501`, prefixed by source dataset for traceability. |
| `source` | string | Which candidate dataset this example was filtered/adapted from (`alpaca-pt-br` \| `canarim`), per research.md §1. |
| `task_category` | string | One of `grammar_correction` \| `rewriting` \| `summarization` \| `simplification` \| `classification`, per spec.md's five target categories. |
| `instruction` | string | The instruction text, in Brazilian Portuguese. |
| `input` | string | The input text the instruction applies to (may be empty for some classification-style prompts). |
| `output` | string | The expected/reference response. |

**Validation rules**:
- `task_category` MUST be one of the five fixed values — no sixth category is in scope (FR-002).
- `id` MUST be unique across the full `train.jsonl` + `validation.jsonl` set (no duplicate training examples).
- No `InstructionExample` may share its `(instruction, input)` pair with any `EvaluationPrompt` (spec.md's Key Entities: "Distinct from the evaluation prompt set — no overlap between the two").
- Total example count across both files MUST fall in the 3,000–5,000 range agreed in the Clarifications session, roughly evenly split across the five `task_category` values.

## EvaluationPrompt

Represents one fixed prompt in the evaluation set (`data/eval/grupo_a_prompts.jsonl`, `data/eval/grupo_b_prompts.jsonl`). Never used for training (spec.md's Key Entities).

| Field | Type | Notes |
|---|---|---|
| `id` | string | Stable unique identifier, e.g. `grupo_a-grammar-003`. |
| `group` | string | `grupo_a` (new-capability, the five task categories) or `grupo_b` (forgetting-check, general PT-BR language). |
| `task_category` | string \| null | One of the five categories for `grupo_a`; `null` for `grupo_b` (general-language prompts aren't category-scoped). |
| `prompt` | string | The full instruction+input text as it will be sent to each model. |
| `expected` | string \| null | Reference answer, required for rule-graded prompts (grammar correction, classification); `null` for manually-reviewed prompts, per the grading-method split in the Clarifications session. |
| `grading_method` | string | `rule_based` \| `manual_review`, fixed per FR-004's hybrid split: `rule_based` for `grammar_correction`/`classification`, `manual_review` for everything else including all of `grupo_b`. |

**Validation rules**:
- `grupo_a` prompt count MUST cover all five `task_category` values, roughly 15–20 prompts each (spec.md Assumptions).
- `grupo_b` prompt count MUST be roughly 20–30 prompts, `task_category = null`, `grading_method = manual_review`.
- Every `rule_based` prompt MUST have a non-null `expected` value (the rule-based grader has nothing to compare against otherwise).
- This file is created once (Phase 1 of the pipeline, User Story 1) and frozen — no edits after baseline evaluation begins, to keep Base/Instruct/Official comparisons valid (FR-001, FR-003, FR-004).

## EvaluationResult

Represents one (prompt, model) scoring record (`eval/results/*.jsonl`), per research.md §5.

| Field | Type | Notes |
|---|---|---|
| `id` | string | The `EvaluationPrompt.id` this result scores. |
| `task_category` | string \| null | Copied from the source `EvaluationPrompt` for convenient filtering. |
| `model` | string | One of `manaca-1b-base` \| `manaca-instruct-pt` \| `manaca-1b-instruct` (the official comparison model, FR-004). |
| `prompt` | string | Copied from the source `EvaluationPrompt` (denormalized for a self-contained record). |
| `expected` | string \| null | Copied from the source `EvaluationPrompt`. |
| `output` | string | The raw generated response from `model` for this `prompt`. |
| `grading_method` | string | `rule_based` \| `manual_review`, copied from the source `EvaluationPrompt`. |
| `score` | number | `1` (pass) or `0` (fail) for `rule_based`; `1`/`0.5`/`0` (correct/partial/incorrect) for `manual_review`, matching the rubric in FR-004. |
| `run_id` | string | Groups all results from one evaluation pass (baseline run, post-training run, post-iteration run) so SC-002/SC-003/SC-008 can be computed per run without mixing runs together. |
| `latency_ms` | number \| null | Generation latency for this prompt, when measured (User Story 1's baseline recording; optional for later runs). |

**Validation rules**:
- Every `(id, model, run_id)` triple MUST be unique (no duplicate scoring of the same prompt/model/run).
- `score` for `rule_based` entries MUST be computed by `src/grading/rule_based.py` (research.md §3), never hand-edited.
- `score` for `manual_review` entries is entered via `src/grading/review_cli.py` by the author and MUST NOT be silently defaulted — an unset score blocks that run's SC-002/SC-003 computation rather than being treated as a pass or fail.
- Per-category pass rate (SC-002) and forgetting relative-drop (SC-003) are derived views over this file, not separately stored fields — computed by aggregating `score` grouped by `(model, task_category)` within one `run_id`.

## FineTuningRun

Represents one training attempt (the baseline "run" is implicit/not a FineTuningRun since no training occurs; this entity covers the first pass and the single budgeted iteration from FR-005).

| Field | Type | Notes |
|---|---|---|
| `run_id` | string | e.g. `qlora-v1`, `qlora-v2` (the latter only if FR-005's iteration round is used). |
| `config_path` | string | Path to the `configs/train.yaml` snapshot used for this run (frozen copy, not a live reference, so past runs remain reproducible even if the config file later changes). |
| `adapter_path` | string | Where the resulting LoRA adapter checkpoint is stored (`adapters/<run_id>/`). |
| `base_model` | string | Always `menezesbruno/manaca-1b-base` for this feature. |
| `dataset_snapshot` | string | Path or hash identifying the exact `train.jsonl`/`validation.jsonl` used, for reproducibility. |
| `eval_run_id` | string | The `EvaluationResult.run_id` produced by evaluating this `FineTuningRun`'s adapter — links training attempts to their scored outcomes. |

**Validation rules**:
- At most 2 `FineTuningRun` records are expected for this feature (`qlora-v1` and, only if needed, `qlora-v2`) — a 3rd would violate FR-005's one-iteration cap and should trigger a scope conversation rather than silent continuation.
- The `FineTuningRun` ultimately selected for merge/quantize/publish (User Stories 3 & 4) MUST be the one whose `eval_run_id` meets or best approaches the FR-004 thresholds, not simply the latest one by default.

## QuantizedArtifact

Represents one GGUF file produced from the merged model (`models/gguf/*.gguf`).

| Field | Type | Notes |
|---|---|---|
| `quant_level` | string | e.g. `Q4_K_M`, `Q5_K_M` — at least two required per FR-006. |
| `file_path` | string | Location under `models/gguf/`. |
| `source_run_id` | string | The `FineTuningRun.run_id` this artifact was merged and quantized from. |

## BenchmarkRecord

Represents one throughput/resource measurement (`benchmarks/*.jsonl`), per FR-007.

| Field | Type | Notes |
|---|---|---|
| `machine` | string | `rtx-5050` \| `dell-g3` — the two required targets (FR-007). |
| `quant_level` | string | Which `QuantizedArtifact.quant_level` was measured. |
| `tokens_per_second` | number | Measured generation throughput. |
| `load_time_s` | number | Time to load the model into memory/VRAM. |
| `vram_mb` | number \| null | Peak VRAM usage, where applicable (may be null for a CPU-only Dell G3 run). |
| `ram_mb` | number | Peak system RAM usage. |
| `stalled_or_crashed` | boolean | Whether generation failed to complete cleanly (SC-004's pass/fail signal). |

**Validation rules**:
- At least one `BenchmarkRecord` per `(machine, quant_level)` combination actually tested is required before FR-007/SC-004/SC-005 can be marked satisfied — these are measured facts, not estimates, per the Edge Cases section of spec.md.

## Relationships

```text
InstructionExample ──(filtered/curated from)──> external source datasets (alpaca-pt-br, canarim)
                                                  [not modeled here — external, read-only]

FineTuningRun ──(trained on)──> InstructionExample[] (via dataset_snapshot)
FineTuningRun ──(produces)────> adapter checkpoint ──(merge, FR-006)──> merged model
merged model ──(quantize, FR-006)──> QuantizedArtifact[] (≥2 quant_levels)
QuantizedArtifact ──(benchmarked on, FR-007)──> BenchmarkRecord[] (per machine)

EvaluationPrompt ──(scored per model, FR-003/FR-004)──> EvaluationResult[]
FineTuningRun ──(evaluated via eval_run_id)──> EvaluationResult[] (model = manaca-instruct-pt)
                                                EvaluationResult[] (model = manaca-1b-base, no FineTuningRun — baseline)
                                                EvaluationResult[] (model = manaca-1b-instruct, no FineTuningRun — official comparison)
```
