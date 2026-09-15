# Contract: Dataset Preparation, Seed Examples, and Preparation Report

Governs `src/prepare_dataset.py` (extended), `src/dataset_filters/*.py` (amended), `src/dataset_filters/quality.py` (new), `data/seed/`, `data/dev/`, and `data/dataset_report.{md,json}`. Extends `specs/001-manaca-instruct-tuning/contracts/dataset-schema.md`; the `InstructionExample` row shape is unchanged.

## `python -m src.prepare_dataset`

```
python -m src.prepare_dataset --sources alpaca-pt-br canarim [ADDITIONAL...] --seed-dir data/seed --out-dir data/ [--dev-out data/dev/dev_prompts.jsonl] [--dev-per-category 10] [--seed 42]
```

Pipeline order (each stage is a pure function over lists of rows and is unit-tested on synthetic rows):

1. **Source filters** (per source module) — category assignment with the amended keyword rules:
   - grammar: whole-word matching, `_GRAMMAR_EXCLUDE` applied first (code-fix instructions never become grammar rows);
   - simplification: `_SIMPLIFICATION_EXCLUDE` applied first (trivia, math); `input` must be non-empty;
   - classification: `len(output.split()) <= 4` and normalized `output` contained in normalized `instruction`;
   - rewriting / summarization: unchanged.
2. **Seed rows** loaded from `--seed-dir` (every `*.jsonl`) and appended.
3. **Quality filter** — drop rows where `is_degenerate_output(output)` is true (any category).
4. **Eval overlap** — existing `_dedupe_against_eval`, now also comparing against the split `(instruction, input)` of evaluation prompts.
5. **Dedupe** — by normalized `(instruction, input, output)`, then by normalized `(instruction, input)`; first occurrence wins; runs before any shuffle.
6. **Shuffle** (seeded) → **cap per category** (unchanged: 1,000) → **split** train/validation (unchanged: 10%).
7. **Dev set** (optional) — 10 rows per category sampled (seeded) from the *validation* split, written as `EvaluationPrompt` rows with `group: "dev"`.
8. **Report** — `data/dataset_report.md` and `.json`.

`normalize(text)` = NFKC → lowercase → collapse whitespace → strip trailing `.`/spaces; it is the single shared implementation in `src/text_normalize.py`, also used by `src/grading/rule_based.py`.

### Guarantees (contract tests over the produced files)

- No grammar row's instruction matches `previs` or the code-exclusion terms; no simplification row's instruction contains `curiosidade`; every classification row's normalized `output` is contained in its normalized `instruction`.
- No row's `output` is degenerate.
- No normalized `(instruction, input, output)` appears twice across `train.jsonl` + `validation.jsonl`; no normalized `(instruction, input)` appears in both files.
- No row's split `(instruction, input)` equals an evaluation prompt's split fields; no row's combined text equals an evaluation `prompt`.
- Total rows in [3,000, 5,000]; each category ≥ 350 or listed in `warnings`.
- Running the command twice with the same sources and seed yields identical SHA256s for `train.jsonl` and `validation.jsonl`.

## `data/seed/` — seed examples

- Files: `data/seed/classification_4class.jsonl` (rows), `data/seed/README.md` (provenance, required).
- Row rules: see `data-model.md` → SeedExample. `source` is `seed-llm`.
- README MUST contain: generating model and version; generation date; the usage terms consulted (link or quote) and the author's one-line compatibility conclusion with CC BY-NC 4.0; the generation prompt; counts generated / kept / edited / discarded; the sentence confirming that every kept row was checked against the 16 classification evaluation messages for reuse or paraphrase.
- Contract tests: ≥ 30 rows per label; no label > 40%; README present and non-template; zero overlap with evaluation prompts.

## Additional public sources (conditional, FR-012/FR-013)

A new source is admitted only through a new module `src/dataset_filters/<name>.py` following the existing loader/filter seam, plus: an entry in `sources` of the report with its license string; a note in `research.md` §10 recording the license check and the sample-audit precision; and the model card's dataset list. Filters for existing categories are never loosened to admit it.

## `data/dataset_report.json`

```json
{"generated_at": "...", "seed": 42,
 "sources": {"alpaca-pt-br": {"license": "CC BY-NC 4.0", "rows_in": 51759, "rows_kept": 0}, "canarim": {...}, "seed-llm": {"license": "author-reviewed synthetic; generator: <model>", "rows_in": 0, "rows_kept": 0}},
 "by_category": {"grammar_correction": {"raw": 0, "after_filter": 0, "after_quality": 0, "after_eval_dedupe": 0, "after_dedupe": 0, "after_cap": 0, "train": 0, "validation": 0}, "...": {}},
 "dropped_by_reason": {"no_output": 0, "exclude_regex": 0, "label_not_in_instruction": 0, "missing_input": 0, "degenerate_output": 0, "overlap_with_eval": 0, "duplicate_triple": 0, "duplicate_pair": 0, "over_cap": 0},
 "fingerprints": {"data/train.jsonl": "<sha256>", "data/validation.jsonl": "<sha256>"},
 "warnings": ["simplification: 344 < 350 — remedy: ..."]}
```

`data/dataset_report.md` is the same content rendered as tables, committed alongside the data files so the counts are reviewable in the PR.
