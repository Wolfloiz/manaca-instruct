# Contract: Dataset Files

Governs `data/train.jsonl`, `data/validation.jsonl`, `data/eval/grupo_a_prompts.jsonl`, `data/eval/grupo_b_prompts.jsonl`. Consumed by `src/train_qlora.py` and `src/evaluate.py`; produced by `src/prepare_dataset.py`.

## Format

JSON Lines (one JSON object per line, UTF-8, no trailing comma). No wrapping array.

## `train.jsonl` / `validation.jsonl` — one `InstructionExample` per line

```json
{"id": "alpaca_pt_br-000123", "source": "alpaca-pt-br", "task_category": "grammar_correction", "instruction": "Corrija o texto a seguir.", "input": "os menino foi na escola ontem", "output": "Os meninos foram à escola ontem."}
```

Required keys: `id`, `source`, `task_category`, `instruction`, `input`, `output`. See `data-model.md`'s `InstructionExample` for field types and validation rules (unique `id`, `task_category` ∈ the fixed 5-value set, no overlap with evaluation prompts).

## `grupo_a_prompts.jsonl` / `grupo_b_prompts.jsonl` — one `EvaluationPrompt` per line

```json
{"id": "grupo_a-grammar-003", "group": "grupo_a", "task_category": "grammar_correction", "prompt": "Corrija: os relatório foi enviado ontem", "expected": "O relatório foi enviado ontem.", "grading_method": "rule_based"}
```

Required keys: `id`, `group`, `task_category`, `prompt`, `expected`, `grading_method`. See `data-model.md`'s `EvaluationPrompt` for validation rules (rule-based prompts require non-null `expected`; `grupo_b` prompts have `task_category: null`).

## Compatibility rule

`src/train_qlora.py` MUST reject (fail fast, not silently skip) any line missing a required key or with a `task_category` outside the fixed 5-value set. `src/evaluate.py` MUST reject any `grupo_a`/`grupo_b` line where `grading_method: rule_based` but `expected` is null.
