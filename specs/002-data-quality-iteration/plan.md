# Implementation Plan: Data Quality & Evaluation Iteration (Manacá-Instruct-PT v3)

**Branch**: `002-data-quality-iteration` | **Date**: 2026-09-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-data-quality-iteration/spec.md`, plus the audit that motivated it (`eval/results/qlora-v2-review.md`) and the pre-spec technical sketch [proposal.md](./proposal.md). Where `proposal.md` and the clarified spec disagree (blind-grade storage, checkpoint selection, the classification criterion), the spec and this plan win.

## Summary

Feature 001 ended with qlora-v2 as its final model after its single FR-005 iteration round, and an audit of that run found three things this feature fixes in order of cost: (1) the evaluation cannot be trusted as-is — grades were not blind, the reported metric hides that only 7/80 group-A answers were fully correct, and training used a two-part prompt structure the evaluator never presents; (2) the training data contains counted defects (52 grammar rows about weather forecasts, 173 "simplification" rows that are trivia questions, 26 corrupted classification answers, 58 duplicates, 25 rows shared between training and validation, and zero classification rows using the four labels the evaluation asks for); (3) training recorded no held-out signal and changed two factors at once, so nothing in v2 can be attributed. The plan adds blind interleaved grading and a two-metric report, measures the prompt-structure gap on the existing v2 adapter with no retraining, rewrites the dataset filters and adds deduplication plus author-reviewed synthetic classification seeds, instruments training with per-epoch held-out loss and a full provenance manifest, and then trains exactly two candidates (clean data; clean data + response-only objective) that are compared to v2 and the official release under one blind protocol and a pre-declared adoption rule. Publication of feature 001 waits for that decision.

## Technical Context

**Language/Version**: Python 3.11 in `.venv` (unchanged from 001).

**Primary Dependencies**: Same stack as 001, at the versions actually installed and verified during planning — `trl` 1.13.0 (`SFTConfig.eval_strategy`, prompt-completion datasets with response-only loss and automatic EOS, all confirmed by reading the installed source), `peft` 0.20.0, `transformers` 5.17.0, `bitsandbytes`, `datasets`, `huggingface_hub` (base-model revision lookup for manifests). No new third-party dependency: SHA256 (`hashlib`), version lookup (`importlib.metadata`), Unicode normalization (`unicodedata`) and Git introspection (`subprocess`) are stdlib. The language model used to *generate* seed examples is an external tool the author operates, not a code dependency; only its name and terms are recorded (research.md §6).

**Storage**: Local filesystem, JSONL and JSON as in 001. New files: `eval/results/<run>-blind.jsonl` (blind grades, siblings of the frozen originals), `eval/results/<run>.manifest.json`, `adapters/<run>/run_manifest.json` with a tracked copy in `runs/<run>.manifest.json`, `data/dataset_report.{md,json}`, `data/seed/`, `data/dev/`, `eval/results/adoption-decision.md`. The four 001 result files, both 001 adapters and the v2 GGUF files are read-only inputs (FR-022).

**Testing**: `pytest` — unit tests on pure functions (filters, dedupe, degenerate detection, report aggregation, manifest assembly with a fake git/hub layer, blind CLI prompt with a scripted `input_fn`) and contract tests over produced files (dataset guarantees, seed file rules, prompt split reconstruction, original-result-file immutability). Training and evaluation are exercised through the mocked-stack pattern already used in `tests/unit/test_train_qlora.py`; real runs are validated by `quickstart.md`, not by the suite.

**Target Platform**: Linux, RTX 5050 (8 GB) for the two ~10–15 min candidate runs and all evaluations; no second-machine work in this feature.

**Project Type**: Single project — extension of the existing local ML pipeline of CLI modules under `src/`.

**Performance Goals**: None new for the model; the feature's throughput constraint is human: ≈264 blind grades for existing runs (v2 in both presentations + official), 88 per candidate, 88 more for a best-epoch row, ≈50 per conditional dev-set comparison. Tooling must make a 90-row blind session resumable and safe to interrupt.

**Constraints**: FR-022 immutability of 001 artifacts; every new result in a new file; adoption rule fixed before the runs (FR-020: classification ≥ 8/16 correct, group-A full-correct rate ≥ 20%, no category mean below v2's blind grades under the selected presentation, grupo_b relative drop ≤ 10%); exactly two primary candidates differing in one factor, at most three conditional single-factor runs (FR-018/FR-021); dataset stays in 3,000–5,000 and CC BY-NC 4.0 (FR-013); v2 stays reproducible (response-only objective and held-out instrumentation are additive and config-gated); seed data must come from a model whose terms allow it, disclosed in the model card (FR-011/FR-023).

**Scale/Scope**: ≈3,300 examples expected after cleaning (grammar ≈610, rewriting ≈880, summarization ≈890, simplification ≈344, classification ≈450 + ≥120 seed); 104 frozen evaluation prompts; 50 development prompts; 2 primary training runs (+ up to 3 conditional); 5 rows in the final table (v2, v3a, v3b, optional v3b-best, official).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template (no principles ratified) — same situation as feature 001. Treated as **pass-through, not exempt**: there are no project gates to evaluate, and this plan asserts no compliance with principles that do not exist. The only standing project rules come from the 001 workflow and are honoured here: agent-owned code goes through worktree → PR → review → merge; frozen artifacts are never edited; measured numbers, not estimates, in every document.

**Post-Phase-1 re-check**: Unchanged. `research.md`, `data-model.md`, `contracts/` and `quickstart.md` add no external service, framework, or architectural layer — only new CLI flags, one new module for the shared prompt template, one for text normalization, one for output-quality checks, one for manifests, one for the report, new JSON/JSONL/Markdown files on the local filesystem, and one optional Hub metadata call (base-model revision) with a local-cache fallback. Complexity Tracking stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/002-data-quality-iteration/
├── plan.md                         # This file (/speckit-plan command output)
├── proposal.md                     # Pre-spec technical sketch derived from the v2 audit (input; superseded where it conflicts)
├── research.md                     # Phase 0 output — 12 decisions, each checked against code/data/installed libs
├── data-model.md                   # Phase 1 output — amended EvaluationPrompt, BlindResultFile, GradingReport, PreparationReport,
│                                   #   SeedExample, DevelopmentPrompt, RunManifest, CandidateRun, AdoptionDecision
├── quickstart.md                   # Phase 1 output — per-user-story validation commands and pass conditions
├── contracts/                      # Phase 1 output
│   ├── blind-review-and-report.md  #   review_cli --blind/--interleave; report.py output format
│   ├── evaluation-presentation.md  #   prompt_format.py; instruction/input split fields; --prompt-format; FR-019 selection rule
│   ├── dataset-preparation.md      #   pipeline order, filter guarantees, data/seed/, data/dev/, dataset_report.json
│   └── run-manifest-schema.md      #   training/evaluation manifests; trainer rules (held-out eval, response-only objective)
├── checklists/requirements.md      # Spec quality checklist (16/16)
└── tasks.md                        # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root) — changes relative to feature 001

```text
manaca-instruct/
├── configs/
│   └── train.yaml                     # + training.completion_only_loss: false (default keeps v2 behaviour)
│
├── data/
│   ├── eval/grupo_a_prompts.jsonl     # + optional instruction/input on every row (prompt text untouched)
│   ├── seed/                          # NEW — classification_4class.jsonl (source: seed-llm) + README.md (provenance)
│   ├── dev/dev_prompts.jsonl          # NEW — 10 prompts/category sampled from validation.jsonl, group: dev
│   ├── dataset_report.md / .json      # NEW — PreparationReport, committed with the data
│   ├── train.jsonl / validation.jsonl # regenerated (v3 dataset); v2's remain in git history
│
├── src/
│   ├── prompt_format.py               # NEW — single ### Instrução/### Entrada/### Resposta implementation
│   ├── text_normalize.py              # NEW — normalize() shared by dedupe, classification filter, rule-based grader
│   ├── run_manifest.py                # NEW — write_manifest() for training and evaluation runs
│   ├── dataset_filters/
│   │   ├── grammar_rewriting.py       # word boundaries + _GRAMMAR_EXCLUDE
│   │   ├── open_ended_tasks.py        # _SIMPLIFICATION_EXCLUDE, input required, label-in-instruction rule
│   │   └── quality.py                 # NEW — is_degenerate_output()
│   ├── prepare_dataset.py             # --seed-dir, --dev-out; quality filter; _dedupe_examples(); report writer
│   ├── train_qlora.py                 # --validation (required); eval per epoch; keep all checkpoints; last-epoch adapter;
│   │                                  #   prompt-completion path when completion_only_loss; manifest; dead code removed
│   ├── evaluate.py                    # --prompt-format {combined,split}; --inference-config; manifest; group "dev" accepted
│   ├── schema_validation.py           # EVAL_GROUPS += "dev"; optional instruction/input pairing rule
│   └── grading/
│       ├── review_cli.py              # --blind, --shuffle-seed, --interleave; writes <run>-blind.jsonl, never the input
│       ├── report.py                  # NEW — per-run/per-category table (mean + full_rate + counts) and pairwise section
│       └── rule_based.py              # uses text_normalize.normalize (behaviour unchanged)
│
├── eval/results/
│   ├── <run>-blind.jsonl              # NEW — blind-graded copies (v2, v2-split, official[-split], candidates)
│   ├── <run>.manifest.json            # NEW — evaluation manifests
│   ├── presentation-experiment.md     # NEW — report output for SC-002
│   ├── final-table.md                 # NEW — report output for the adoption decision
│   └── adoption-decision.md           # NEW — AdoptionDecision record (FR-020)
│
├── adapters/<run_id>/run_manifest.json  # NEW — training manifest next to the adapter (gitignored with it)
├── runs/<run_id>.manifest.json          # NEW — tracked, byte-identical copy of each training manifest (reviewable in PRs)
│
└── tests/
    ├── unit/                          # test_prompt_format, test_text_normalize, test_quality, test_run_manifest, test_report,
    │                                  #   + extended test_grammar_rewriting / test_open_ended_tasks / test_prepare_dataset /
    │                                  #   test_train_qlora / test_evaluate / test_review_cli
    └── contract/                      # test_eval_prompt_split (reconstruction), test_dataset_quality (produced-file guarantees),
                                       #   test_seed_examples, test_results_immutability (001 files byte-identical after a blind session)
```

**Structure Decision**: Keep the single-project layout of 001 and extend it in place — every change is a flag, a field, a new small module, or a new output file beside an existing one. Three things were deliberately *not* done: no new top-level package for "v3" (the point is one pipeline whose runs are distinguished by manifests, not by code copies); no experiment-tracking service (manifests on disk are reviewable in PRs, which is how this project audits itself); and no runtime splitting of evaluation prompts (the split is data, authored once and checked by a reconstruction test). Agent ownership follows 001: Agent 1 — `prepare_dataset.py`, `grammar_rewriting.py`, `quality.py`, `text_normalize.py`; Agent 2 — `open_ended_tasks.py`, `prompt_format.py`, `evaluate.py`, `review_cli.py`, `report.py`, eval prompt split fields; Agent 3 — `train_qlora.py`, `run_manifest.py`, `configs/train.yaml`; You — seed generation/review, all grading, both training runs, the adoption decision.

## Complexity Tracking

> No Constitution Check violations were raised (no ratified constitution exists — see Constitution Check above), so this section is intentionally empty.
