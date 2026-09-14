# Implementation Plan: Manacá-Instruct-PT (Core Lifecycle v1)

**Branch**: `001-manaca-instruct-tuning` | **Date**: 2026-09-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-manaca-instruct-tuning/spec.md`

## Summary

Fine-tune the `menezesbruno/manaca-1b-base` Brazilian Portuguese base model into an instruction-following model ("Manacá-Instruct-PT") using QLoRA on a curated ~3,000–5,000-example blend of existing published PT-BR instruction datasets (filtered to five task categories: grammar correction, rewriting, summarization, simplification, classification). Evaluate it against both the base model and the newly-released official `menezesbruno/manaca-1b-instruct` on a fixed prompt set (hybrid rule-based + manual grading), quantize to GGUF, benchmark on two real machines (RTX 5050 dev / Dell G3 deployment), and publish the result publicly on Hugging Face with a model card disclosing it as a personal/learning project, CC BY-NC 4.0 licensed (inherited from the NC-licensed instruction datasets). No API, UI, or RAG layer is in scope.

## Technical Context

**Language/Version**: Python 3.11 (matches the author's own environment plan in `manaca-local-projeto.md` §10; standard for the PyTorch/Transformers/PEFT ecosystem).

**Primary Dependencies**: PyTorch (CUDA build) + `transformers` + `peft` + `trl` + `bitsandbytes` + `datasets` (training/fine-tuning); `huggingface_hub` (dataset access and model publishing); llama.cpp (`convert_hf_to_gguf.py` + `llama-quantize`) for GGUF conversion and cross-hardware inference; a lightweight scoring library (Python stdlib `difflib`, or `rapidfuzz` if a dependency is warranted) for rule-based grading.

**Storage**: Local filesystem only — JSONL for datasets and evaluation results, safetensors/PyTorch checkpoints for the adapter and merged model, GGUF files for quantized artifacts. No database. Hugging Face Hub is the sole external storage/publish target (dataset pull + final model push).

**Testing**: `pytest` for the automatable pieces only — dataset schema/format validation, the rule-based grader (grammar correction, classification) tested against known input/expected pairs, and evaluation-result JSONL schema checks. The manual-review grading path (rewriting, summarization, simplification, forgetting-check) is a documented human process, not an automated test, per the FR-004 clarification.

**Target Platform**: Linux (WSL2/Ubuntu, per the author's existing environment) for training and dev-machine inference on the RTX 5050; Linux or Windows with llama.cpp for deployment/benchmarking on the Dell G3 (GTX 1050, 4GB VRAM, 32GB RAM).

**Project Type**: Single project — a local ML pipeline of CLI scripts/notebooks, not a client-server or mobile application. No API surface is in scope (per spec.md's out-of-scope items).

**Performance Goals**: ~70 tokens/second generation on hardware typical of a Hugging Face downloader (SC-005) — measured, not just claimed; separately, real (uncapped) throughput is recorded on both the author's own machines (FR-007) for honest reporting regardless of whether they hit that figure.

**Constraints**: 8GB VRAM ceiling for training (RTX 5050); 4GB VRAM / 32GB system RAM ceiling for deployment inference (Dell G3); 4096-token context window inherited from the base model; the chosen dataset sources (see research.md) are CC BY-NC 4.0, which propagates to the published model's license (FR-009); at most one training iteration round is budgeted (FR-005).

**Scale/Scope**: ~3,000–5,000 fine-tuning examples across 5 categories; ~50–100 fixed evaluation prompts (≈15–20 per category for the new-capability group, ≈20–30 for the forgetting-check group, per spec.md's Assumptions); one published model repository on Hugging Face with at least two GGUF quantization levels.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` has not been ratified for this project — it is still the unfilled template (`[PROJECT_NAME] Constitution` placeholder, no principles defined). There are therefore no project-specific gates to evaluate against. This is treated as **pass-through, not exempt**: no constitutional principles are being satisfied because none exist yet, not because this feature is presumed compliant with anything. If a constitution is ratified later, this plan should be re-checked against it.

No violations to track; **Complexity Tracking** section below is empty accordingly.

**Post-Phase-1 re-check**: Unchanged — `research.md`, `data-model.md`, `contracts/`, and `quickstart.md` introduce no new external services, frameworks, or architectural layers beyond what Technical Context already declared (local scripts, JSONL/GGUF files, Hugging Face Hub as the sole external system). No ratified constitution exists to re-check against, so this remains pass-through.

## Project Structure

### Documentation (this feature)

```text
specs/001-manaca-instruct-tuning/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── dataset-schema.md
│   ├── evaluation-results-schema.md
│   └── model-usage-contract.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
manaca-instruct/
├── configs/
│   ├── train.yaml              # QLoRA hyperparameters (rank, alpha, lr, batch size, etc.)
│   └── inference.yaml          # Generation defaults (temperature, top_p, max_new_tokens)
│
├── data/
│   ├── raw/                    # Unmodified pulls from source datasets (Alpaca-PT-BR, Canarim)
│   ├── processed/               # Filtered/deduplicated intermediate data, by category
│   ├── train.jsonl              # Final ~3,000–5,000 example fine-tuning set
│   ├── validation.jsonl
│   └── eval/
│       ├── grupo_a_prompts.jsonl   # Fixed new-capability prompts (5 categories)
│       └── grupo_b_prompts.jsonl   # Fixed forgetting-check prompts (general PT-BR)
│
├── src/
│   ├── prepare_dataset.py       # Pull, filter, dedupe, split existing datasets → train/validation.jsonl
│   ├── train_qlora.py           # QLoRA fine-tuning entrypoint (base model + train.jsonl → adapter)
│   ├── evaluate.py              # Runs grupo_a/grupo_b prompts against base / instruct / official-instruct
│   ├── grading/
│   │   ├── rule_based.py        # Grammar-correction & classification scorer
│   │   └── review_cli.py        # Lightweight CLI to record manual review scores for open-ended categories
│   ├── merge_adapter.py         # Merges trained LoRA adapter into a standalone model
│   ├── quantize.py              # Drives llama.cpp convert_hf_to_gguf.py + llama-quantize
│   ├── benchmark.py             # Measures tokens/sec, load time, VRAM/RAM on a given machine
│   └── publish.py               # Pushes the merged/quantized model + model card to Hugging Face Hub
│
├── eval/
│   └── results/                 # JSONL evaluation run outputs (base vs instruct vs official-instruct)
│
├── adapters/                    # Trained LoRA adapter checkpoints
│
├── models/
│   ├── merged/                  # Standalone merged fine-tuned model
│   └── gguf/                    # Quantized GGUF artifacts (Q4_K_M + one comparison level)
│
├── benchmarks/                  # Recorded throughput/VRAM/RAM logs per machine (RTX 5050, Dell G3)
│
└── tests/
    ├── unit/                    # prepare_dataset.py filtering logic, rule_based.py scorer
    └── contract/                 # dataset-schema.md / evaluation-results-schema.md compliance checks
```

**Structure Decision**: Single-project layout (no frontend/backend or mobile split — this is a local ML pipeline of scripts, not a client-server app). Domain-specific directories (`data/`, `adapters/`, `models/`, `eval/`, `benchmarks/`) replace the generic `models/services/cli/lib` scaffold from the template because this feature's "domain objects" are datasets, checkpoints, and benchmark logs rather than application services. This mirrors the structure the author already sketched independently in `manaca-local-projeto.md` §11, adjusted to add `eval/` and `benchmarks/` as first-class directories since the spec's evaluation and cross-hardware benchmarking requirements (FR-003, FR-004, FR-007) need durable, reviewable output locations, not just scratch space.

## Complexity Tracking

> No Constitution Check violations were raised (no ratified constitution exists yet — see Constitution Check above), so this section is intentionally empty.
