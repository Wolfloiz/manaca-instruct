# Quickstart: Validating the Data Quality & Evaluation Iteration End-to-End

Each section proves one user story of `spec.md` with runnable commands and the outcome that counts as passing. File shapes are in `data-model.md`; CLI behaviour in `contracts/`. Commands assume the repository root and the project virtualenv (`.venv/bin/python3`; the test suite also runs under `~/.venvs/global`). Expected effort figures are from `spec.md`'s Assumptions.

## Prerequisites

- Feature 001 artifacts present and untouched: `eval/results/{baseline,qlora-v1,qlora-v2,official-instruct}.jsonl`, `adapters/qlora-v2/`, `data/eval/*.jsonl`.
- `.venv` with the ML stack (`trl` 1.13.x, `peft` 0.20.x, `transformers` 5.17.x) for anything that loads a model; the unit/contract suite needs only `pytest`.
- Baseline check before starting: `python -m pytest tests/ -q` → all green (82 at the time of planning).

## Validate User Story 1 — Trustworthy evaluation (no training)

```bash
# 1. Presentation experiment on the existing v2 adapter (~3 min GPU)
python -m src.evaluate --model manaca-instruct-pt --adapter adapters/qlora-v2 \
    --prompts data/eval/grupo_a_prompts.jsonl data/eval/grupo_b_prompts.jsonl \
    --prompt-format split --run-id qlora-v2-split --out eval/results/qlora-v2-split.jsonl
#    → eval/results/qlora-v2-split.jsonl (104 rows) + eval/results/qlora-v2-split.manifest.json (prompt_format: split)

# 2. Blind, interleaved grading of both v2 presentations (~176 grades)
python -m src.grading.review_cli eval/results/qlora-v2.jsonl eval/results/qlora-v2-split.jsonl \
    --blind --interleave --shuffle-seed 7
#    → eval/results/qlora-v2-blind.jsonl and eval/results/qlora-v2-split-blind.jsonl; originals byte-identical (tool prints matching SHA256s)

# 3. Report and presentation decision
python -m src.grading.report eval/results/qlora-v2-blind.jsonl eval/results/qlora-v2-split-blind.jsonl \
    --pair qlora-v2 qlora-v2-split --markdown-out eval/results/presentation-experiment.md
#    → per-category mean + full_rate for both, pairwise improved/worsened/tied; apply FR-019's ≥2/16 rule and write the choice into eval/results/adoption-decision.md

# 4. Official release under the selected presentation (only re-run if 'split' was selected), then blind grading (~88 grades)
python -m src.evaluate --model manaca-1b-instruct --prompts data/eval/grupo_a_prompts.jsonl data/eval/grupo_b_prompts.jsonl \
    --prompt-format split --run-id official-instruct-split --out eval/results/official-instruct-split.jsonl   # if split
python -m src.grading.review_cli eval/results/official-instruct[-split].jsonl --blind --shuffle-seed 7
```

**Pass when**: SC-001 (v2 and official have `-blind` files and a report with both metrics), SC-002 (presentation delta documented with the rule applied), and no 001 result file changed (`git status` clean for `eval/results/{baseline,qlora-v1,qlora-v2,official-instruct}.jsonl`).

## Validate User Story 2 — Clean training data (no training)

```bash
# 1. Seed examples: generate with the chosen model, review each row, fill data/seed/README.md (author task, ~1–2 h)
#    then check the seed file alone:
python -m pytest tests/contract/test_seed_examples.py -q

# 2. Regenerate the dataset (network: downloads the public sources)
python -m src.prepare_dataset --sources alpaca-pt-br canarim --seed-dir data/seed --out-dir data/ \
    --dev-out data/dev/dev_prompts.jsonl
#    → data/train.jsonl, data/validation.jsonl, data/dev/dev_prompts.jsonl, data/dataset_report.{md,json}

# 3. Contract checks over the produced files
python -m pytest tests/contract/test_dataset_quality.py -q
#    → zero defect-pattern hits, zero duplicates, zero train/validation overlap, totals in range

# 4. Reproducibility: run step 2 again and compare fingerprints
sha256sum data/train.jsonl data/validation.jsonl   # must equal data/dataset_report.json → fingerprints

# 5. Author audit: 30 random grammar rows
python - <<'EOF'
import json, random; rows=[json.loads(l) for l in open("data/train.jsonl")]
g=[r for r in rows if r["task_category"]=="grammar_correction"]; random.Random(1).shuffle(g)
for r in g[:30]: print(r["id"], "|", r["instruction"][:100], "|", r["input"][:60])
EOF
#    → at least 27/30 are genuine language corrections (record the count in data/dataset_report.md)
```

**Pass when**: SC-003 and SC-004 hold, `data/dataset_report.md` lists per-source counts and licenses (including `seed-llm` with its generator), and any `warnings` entry names its remedy or "documented shortfall".

## Validate User Story 3 — Training with validation and provenance (short run)

```bash
# Smoke run: 1 epoch on a 200-row slice to prove instrumentation without spending real GPU time
head -n 200 data/train.jsonl > /tmp/train-smoke.jsonl; head -n 40 data/validation.jsonl > /tmp/val-smoke.jsonl
python -m src.train_qlora --config configs/train.yaml --dataset /tmp/train-smoke.jsonl \
    --validation /tmp/val-smoke.jsonl --run-id smoke-v3
#    → adapters/smoke-v3/run_manifest.json with eval_loss_by_epoch, best_epoch, checkpoints[], adapter_epoch == last epoch
cat adapters/smoke-v3/run_manifest.json | python -m json.tool | head -40

# Response-only objective path (flip the config key, rerun the smoke run as smoke-v3-co)
#    → manifest shows completion_only_loss: true; a 3-prompt generation with evaluate.py terminates its answers
```

**Pass when**: US3 scenarios 1, 3, 4 hold on the smoke run (held-out loss per epoch recorded, last epoch saved, manifest complete with dataset SHA256 = report fingerprint) and scenario 2 holds on the response-only smoke run (answers end without hitting `max_new_tokens`).

## Validate User Story 4 — Two candidates and the decision (GPU + grading)

```bash
# 1. Candidates (~10–15 min each)
python -m src.train_qlora --config configs/train.yaml --dataset data/train.jsonl --validation data/validation.jsonl --run-id qlora-v3a
#    configs/train.yaml: completion_only_loss: true for the second run (record the diff in the PR)
python -m src.train_qlora --config configs/train.yaml --dataset data/train.jsonl --validation data/validation.jsonl --run-id qlora-v3b

# 2. Evaluate under the presentation selected in US1 (shown here as split; use the plain run ids if combined was selected)
for r in qlora-v3a qlora-v3b; do
  python -m src.evaluate --model manaca-instruct-pt --adapter adapters/$r --prompts data/eval/grupo_a_prompts.jsonl data/eval/grupo_b_prompts.jsonl \
      --prompt-format split --run-id $r-split --out eval/results/$r-split.jsonl
done
# 3. Best-epoch row for v3b when best_epoch != adapter_epoch (see adapters/qlora-v3b/run_manifest.json)
python -m src.evaluate --model manaca-instruct-pt --adapter adapters/qlora-v3b/checkpoint-<step> \
    --prompts data/eval/grupo_a_prompts.jsonl data/eval/grupo_b_prompts.jsonl --prompt-format split \
    --run-id qlora-v3b-best-split --out eval/results/qlora-v3b-best-split.jsonl

# 4. Blind grading, all candidates interleaved (~88 grades per file)
python -m src.grading.review_cli eval/results/qlora-v3a-split.jsonl eval/results/qlora-v3b-split.jsonl [eval/results/qlora-v3b-best-split.jsonl] \
    --blind --interleave --shuffle-seed 11

# 5. Final table and rule
python -m src.grading.report eval/results/qlora-v2-split-blind.jsonl eval/results/qlora-v3a-split-blind.jsonl \
    eval/results/qlora-v3b-split-blind.jsonl eval/results/official-instruct-split-blind.jsonl \
    --pair qlora-v2-split qlora-v3a-split --pair qlora-v3a-split qlora-v3b-split --markdown-out eval/results/final-table.md
#    → apply FR-020: classification correct ≥ 8/16, group-A full_rate ≥ 0.20, no category mean < v2, grupo_b relative drop ≤ 10%
#    → write eval/results/adoption-decision.md (outcome + attribution)
```

**Pass when**: US4 scenarios 1–3 hold; SC-006/SC-007 for the adopted candidate (or the decline is documented); every manifest cited has `git_dirty: false`.

## Conditional step — single-factor follow-ups (only if FR-020 is not met)

```bash
# Development set exists from US2 step 2; grade generation-setting comparisons on it, never on data/eval/*
python -m src.evaluate --model manaca-instruct-pt --adapter adapters/<candidate> --prompts data/dev/dev_prompts.jsonl \
    --inference-config configs/inference-rp1.1.yaml --prompt-format split --run-id <candidate>-dev-rp11 --out eval/results/<candidate>-dev-rp11.jsonl
python -m src.grading.review_cli eval/results/<candidate>-dev-*.jsonl --blind --interleave --shuffle-seed 13
```

At most three such runs (`qlora-v3c..e`), each changing exactly one factor named in its manifest's `differs_from` note; the frozen set is used once per resulting candidate.

## Full sign-off (SC-008)

- `eval/results/adoption-decision.md` exists, cites only `-blind` files, and states the presentation, the rule checks per candidate, the outcome, and the attribution.
- `MODEL_CARD.md` comparison section is regenerated from `src.grading.report` output and carries the "means include partial credit" footnote, the protocol column, the dataset list with licenses, and the seed-data disclosure (FR-023).
- Feature 001's publication step (its T058) is unblocked only after this file exists.
