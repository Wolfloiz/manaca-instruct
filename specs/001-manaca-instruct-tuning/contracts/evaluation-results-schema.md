# Contract: Evaluation Results Files

Governs `eval/results/*.jsonl` (one file per `run_id`, e.g. `eval/results/baseline.jsonl`, `eval/results/qlora-v1.jsonl`, `eval/results/official-instruct.jsonl`). Produced by `src/evaluate.py` (rule-based scores) and `src/grading/review_cli.py` (manual-review scores); consumed by whatever reporting step generates the model card's comparison tables (FR-009, SC-008).

## Format

JSON Lines, one `EvaluationResult` per line (see `data-model.md` for full field list and validation rules):

```json
{"id": "grupo_a-grammar-003", "task_category": "grammar_correction", "model": "manaca-instruct-pt", "prompt": "Corrija: os relatório foi enviado ontem", "expected": "O relatório foi enviado ontem.", "output": "O relatório foi enviado ontem.", "grading_method": "rule_based", "score": 1, "run_id": "qlora-v1", "latency_ms": 812}
```

## Producer rules

- `src/evaluate.py` MUST write one line per `(EvaluationPrompt, model)` pair it runs, immediately after scoring — never buffer an entire run in memory only to lose it on a crash.
- For `grading_method: rule_based` lines, `score` MUST be set by `src/grading/rule_based.py` at write time (never left `null`).
- For `grading_method: manual_review` lines, `src/evaluate.py` MUST write the line with `score: null` and `output` populated; `src/grading/review_cli.py` is the only component permitted to fill in `score` afterward (see `data-model.md`'s validation rule against silent defaulting).

## Consumer rules

- Any aggregation (per-category pass rate for SC-002, forgetting relative-drop for SC-003, the three-way SC-008 comparison table) MUST first filter to rows where `score` is non-null, and MUST report the count of still-`null` (not-yet-manually-reviewed) rows separately rather than silently excluding them — an incomplete manual review should be visible, not invisible.
- Aggregation MUST group by `(run_id, model, task_category)` — never mix rows from two different `run_id`s into one pass-rate computation, since that would conflate the baseline, a training attempt, and its iteration.
