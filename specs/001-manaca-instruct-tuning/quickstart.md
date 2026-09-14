# Quickstart: Validating Manacá-Instruct-PT End-to-End

A runnable validation path proving each user story in `spec.md` actually works, in priority order. Commands are illustrative (exact script flags are decided during implementation) — this documents *what* to run and *what to expect*, not full implementation code. See `contracts/` for the exact file formats these steps produce/consume, and `data-model.md` for the record shapes.

## Prerequisites

- Python 3.11 environment with the dependencies from `research.md` (`torch`, `transformers`, `peft`, `trl`, `bitsandbytes`, `datasets`, `huggingface_hub`) installed.
- `menezesbruno/manaca-1b-base` downloadable (Hugging Face access, no auth required — it's public).
- `menezesbruno/manaca-1b-instruct` downloadable for the FR-004 comparison (also public).
- llama.cpp built locally (`convert_hf_to_gguf.py`, `llama-quantize`, `llama-cli` available) for User Story 3.
- RTX 5050 machine available for training and dev-machine benchmarking; Dell G3 machine available for deployment benchmarking (User Story 3).
- A Hugging Face account + write token for User Story 4 (can be deferred until Stories 1–3 pass).

## Validate User Story 1 — Baseline

```bash
python src/evaluate.py \
  --model manaca-1b-base \
  --prompts data/eval/grupo_a_prompts.jsonl data/eval/grupo_b_prompts.jsonl \
  --run-id baseline \
  --out eval/results/baseline.jsonl
```

**Expected outcome**: `eval/results/baseline.jsonl` contains one `EvaluationResult` row per prompt (per `contracts/evaluation-results-schema.md`), `latency_ms` populated for every row, and manual review (`src/grading/review_cli.py`) completed for the `manual_review`-graded rows. Spot-check: at least one `grupo_a` prompt's `output` visibly fails to follow the instruction (confirms Acceptance Scenario 2 of User Story 1 — the base model doesn't reliably follow instructions).

## Validate User Story 2 — Fine-tune & evaluate

```bash
python src/prepare_dataset.py --sources alpaca-pt-br canarim --out-dir data/
python src/train_qlora.py --config configs/train.yaml --dataset data/train.jsonl --run-id qlora-v1
python src/evaluate.py --model manaca-instruct-pt --adapter adapters/qlora-v1 \
  --prompts data/eval/grupo_a_prompts.jsonl data/eval/grupo_b_prompts.jsonl \
  --run-id qlora-v1 --out eval/results/qlora-v1.jsonl
python src/evaluate.py \
  --model manaca-1b-instruct \
  --prompts data/eval/grupo_a_prompts.jsonl data/eval/grupo_b_prompts.jsonl \
  --run-id official-instruct --out eval/results/official-instruct.jsonl
```

**Expected outcome**: `data/train.jsonl` + `data/validation.jsonl` together total ~3,000–5,000 examples (per `data-model.md`'s `InstructionExample` validation rule). After scoring (including manual review for open-ended categories), aggregate `eval/results/qlora-v1.jsonl` by `(model, task_category)`:
- Each of the 5 categories reaches ≥70% pass rate for `manaca-instruct-pt` vs. `manaca-1b-base` (SC-002), **or** any shortfall is written up as a known limitation.
- The `grupo_b` (forgetting-check) relative drop for `manaca-instruct-pt` vs. `manaca-1b-base` is ≤10% (SC-003).
- If either threshold is missed, run the single budgeted iteration (FR-005): adjust `configs/train.yaml` within the ranges in `research.md` §2, retrain as `qlora-v2`, re-run this whole step with `--run-id qlora-v2`, and accept that result (pass or documented limitation) — no further iteration.
- `eval/results/official-instruct.jsonl` gives the third comparison point for SC-008's reporting table, independent of whether `manaca-instruct-pt` passes its own thresholds.

## Validate User Story 3 — Cross-hardware deployment

```bash
python src/merge_adapter.py --adapter adapters/qlora-v1 --out models/merged/manaca-instruct-pt
python src/quantize.py --model models/merged/manaca-instruct-pt --levels Q4_K_M Q5_K_M --out-dir models/gguf/

# On the RTX 5050 (dev machine):
python src/benchmark.py --model models/gguf/manaca-instruct-pt-Q4_K_M.gguf --machine rtx-5050 --out benchmarks/rtx-5050.jsonl

# On the Dell G3 (deployment machine):
python src/benchmark.py --model models/gguf/manaca-instruct-pt-Q4_K_M.gguf --machine dell-g3 --out benchmarks/dell-g3.jsonl
```

**Expected outcome**: `models/gguf/` contains at least 2 quantization levels (FR-006). Both `benchmarks/rtx-5050.jsonl` and `benchmarks/dell-g3.jsonl` contain at least one `BenchmarkRecord` with `stalled_or_crashed: false` (SC-004) — generation completes cleanly on both machines regardless of measured speed. `tokens_per_second` is recorded honestly on both, even if the Dell G3's 4GB-VRAM number comes in below the ~70 tok/s target aimed at typical modern-GPU downloaders (SC-005; per the Edge Cases section, this is reported, not hidden).

## Validate User Story 4 — Publish

```bash
python src/publish.py --model models/merged/manaca-instruct-pt --gguf-dir models/gguf/ \
  --eval-results eval/results/qlora-v1.jsonl eval/results/baseline.jsonl eval/results/official-instruct.jsonl \
  --repo-id <hf-username>/manaca-instruct-pt
```

**Expected outcome**: `src/publish.py` refuses to run if the model-card gate in `contracts/model-usage-contract.md` isn't satisfied (missing license, missing usage snippet, or missing evaluation section). On success, the Hugging Face repo is live with the required front matter, both usage snippets (transformers + llama.cpp), the SC-008 three-way comparison table, and the known-limitations section. Final check (Acceptance Scenario 2 of User Story 4): have someone who has not seen this repo before follow only the model card to generate one response — no extra undocumented steps needed.

## Full lifecycle sign-off (SC-007)

All of the above having been run at least once — baseline, dataset prep, training, evaluation (all three models), merge, quantization, both benchmarks, and publish — is itself the completion signal for SC-007, independent of whether every numeric threshold was hit on the first attempt.
