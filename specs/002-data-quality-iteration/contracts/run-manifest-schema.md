# Contract: Run Manifests (training and evaluation)

Governs `src/run_manifest.py` (new) and the files `adapters/<run_id>/run_manifest.json` (written by `src/train_qlora.py` next to the adapter, gitignored with it) with its **tracked copy** `runs/<run_id>.manifest.json` (same bytes; `runs/` is a new version-controlled directory so training provenance is reviewable in PRs even though adapters are not committed), and `eval/results/<run_id>.manifest.json` (written by `src/evaluate.py`). Also governs the training-side changes in `src/train_qlora.py` that the manifest records (held-out evaluation, response-only objective).

## Common fields

```json
{
  "kind": "training" | "evaluation",
  "run_id": "qlora-v3b",
  "status": "ok" | "failed",
  "error": null | "<message>",
  "created_at": "2026-09-15T21:04:11Z",
  "git_commit": "<40-hex>",
  "git_dirty": false,
  "library_versions": {"torch": "...", "transformers": "...", "peft": "...", "trl": "...", "bitsandbytes": "...", "datasets": "..."},
  "base_model": {"repo_id": "menezesbruno/manaca-1b-base", "revision": "<hub commit sha or local cache hash>"},
  "datasets": [{"path": "data/train.jsonl", "sha256": "<hex>", "rows": 0}],
  "config": { ... the loaded YAML, verbatim ... },
  "prompt_format": "train-template" | "combined" | "split"
}
```

Rules:
- Written **always**, including on failure (`status: failed`, `error` set) — a failed run is still attributable.
- `datasets[].sha256` MUST be computed from the file bytes at run start; for training runs the values MUST match `data/dataset_report.json`'s `fingerprints` (SC-005).
- `base_model.revision` comes from `huggingface_hub.model_info(repo_id).sha`; if the Hub is unreachable, the locally cached snapshot hash is used and `revision_source: "local-cache"` is added.
- `git_dirty: true` is allowed but is printed as a warning at run start; the adoption decision MUST cite manifests with `git_dirty: false` only.

## Training-only fields

```json
{
  "validation_path": "data/validation.jsonl",
  "completion_only_loss": false,
  "eval_loss_by_epoch": {"1": 2.31, "2": 1.98, "3": 1.91},
  "train_loss_by_epoch": {"1": 2.6, "2": 2.0, "3": 1.7},
  "best_epoch": 3,
  "checkpoints": [{"epoch": 1, "path": "adapters/qlora-v3b/checkpoint-124"}, ...],
  "adapter_path": "adapters/qlora-v3b",
  "adapter_epoch": 3
}
```

Rules for `src/train_qlora.py` (what makes these fields true):
- `--validation` is required; the trainer receives it as its evaluation set and evaluates every epoch (`eval_strategy="epoch"`).
- Every epoch checkpoint is kept (`save_strategy="epoch"`, no `save_total_limit`), and `adapter_path` is always the **last** epoch — held-out evaluation never changes which adapter a run produces (FR-014; clarification Q3).
- `best_epoch` = argmin of `eval_loss_by_epoch`; when it differs from `adapter_epoch`, the manifest's `checkpoints` entry for it is what `evaluate.py --adapter <path>` uses for the `<run_id>-best` evaluation.
- `completion_only_loss` mirrors `training.completion_only_loss` from the config (default `false`); when `true`, the dataset handed to the trainer is prompt-completion (`prompt` = `format_prompt(instruction, input)`, `completion` = `output`) and the trainer's default response-only loss applies; when `false`, the `text` form and full-sequence loss of feature 001 apply unchanged.
- Any training run MUST refuse to start if `validation.jsonl` shares a normalized `(instruction, input)` with `train.jsonl` (cheap pre-check; overlap invalidates held-out loss).

## Evaluation-only fields

```json
{
  "model": "manaca-instruct-pt",
  "adapter_path": "adapters/qlora-v3b" | null,
  "checkpoint": "adapters/qlora-v3b/checkpoint-124" | null,
  "adapter_manifest": "adapters/qlora-v3b/run_manifest.json" | null,
  "inference_config_path": "configs/inference.yaml",
  "prompt_files": ["data/eval/grupo_a_prompts.jsonl", "data/eval/grupo_b_prompts.jsonl"],
  "results_path": "eval/results/qlora-v3b-split.jsonl",
  "rows_written": 104
}
```

Rules for `src/evaluate.py`:
- `--inference-config PATH` (default `configs/inference.yaml`) is recorded verbatim under `config`.
- `--prompt-format` is recorded as `prompt_format`; the run id convention (`-split`, `-best`) is the author's responsibility but the manifest is the source of truth.
- The manifest is written next to the results file after the last row; `rows_written` MUST equal the line count of `results_path`.

## Guarantees tested

- `write_manifest` output validates against the field list above (unit test with a fake git/hub layer).
- SHA256 in a training manifest equals the report fingerprint for the same file (contract test on synthetic files).
- A simulated trainer failure still produces a manifest with `status: failed` (unit test with a mocked trainer that raises).
