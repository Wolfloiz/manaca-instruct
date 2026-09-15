# Contract: Prompt Presentation in Evaluation

Governs `src/prompt_format.py` (new), the optional `instruction`/`input` fields in `data/eval/grupo_a_prompts.jsonl`, `data/dev/dev_prompts.jsonl`, and `src/evaluate.py`'s `--prompt-format` flag. Amends `specs/001-manaca-instruct-tuning/contracts/dataset-schema.md` (EvaluationPrompt section) without changing any existing required key.

## `src/prompt_format.py`

```python
format_prompt(instruction: str, input: str = "", output: str | None = None) -> str
```

- Returns `### Instrução:\n{instruction}` + (`\n\n### Entrada:\n{input}` only when `input` is non-empty) + `\n\n### Resposta:\n` + (`{output}` when `output` is not `None`).
- With `output=None` the string ends exactly with `### Resposta:\n` (inference form). With `output` given it is the training form.
- `src/train_qlora.py::_format_prompt(example)` MUST equal `format_prompt(example["instruction"], example["input"], example["output"])`; `src/evaluate.py::_format_inference_prompt(text)` MUST equal `format_prompt(text)`. Existing tests for both remain valid unchanged — this is a refactor with identical output.

## EvaluationPrompt rows — optional split fields

```json
{"id": "grupo_a-grammar-001", "group": "grupo_a", "task_category": "grammar_correction",
 "prompt": "Corrija gramaticalmente o texto: os menino foi na escola ontem",
 "instruction": "Corrija gramaticalmente o texto", "input": "os menino foi na escola ontem",
 "expected": "Os meninos foram à escola ontem.", "grading_method": "manual_review"}
```

Rules:
- `instruction` and `input` are optional and appear together or not at all.
- When present: `instruction + ": " + input == prompt` byte-for-byte (contract test over every row of the file).
- `prompt` is never modified (FR-022). The split is authored once by hand and reviewed; no runtime splitting.
- `grupo_b` rows never carry the fields.
- `group` may be `grupo_a` | `grupo_b` | `dev` (`dev` only in `data/dev/dev_prompts.jsonl`; `dev` rows additionally carry `source_id`).

## `python -m src.evaluate --prompt-format {combined,split}`

| Value | Behaviour |
|---|---|
| `combined` (default) | `format_prompt(row["prompt"])` — identical to feature 001's evaluation. |
| `split` | `format_prompt(row["instruction"], row["input"])` for rows that carry the split fields; rows without them (all of `grupo_b`) fall back to `combined`. The run MUST fail fast if a `grupo_a` row lacks the fields, rather than silently mixing presentations within a run. |

- The presentation is recorded in the evaluation manifest (`prompt_format`) and, by convention, in the run id (`<run>` vs `<run>-split`).
- A `split` run and a `combined` run of the same model are two distinct result files; the report pairs them by `id` (SC-002).

## Selection rule for the final table (FR-019)

`split` is selected when, comparing `qlora-v2-blind` and `qlora-v2-split-blind`, any task category differs by ≥ 2 prompts in either `full_rate` or `mean` (2/16 = 0.125); otherwise `combined`. The chosen value and the deltas are written to `eval/results/adoption-decision.md` before any candidate is evaluated.
