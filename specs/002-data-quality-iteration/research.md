# Phase 0 Research: Data Quality & Evaluation Iteration (Manacá-Instruct-PT v3)

Every decision below was checked against the code and data as they exist in the repository on 2026-09-15 (`src/`, `data/train.jsonl` 3,956 rows, `data/validation.jsonl` 439 rows, `eval/results/qlora-v2.jsonl`) and against the libraries actually installed in `.venv` (`trl` 1.13.0, `peft` 0.20.0, `transformers` 5.17.0). Numbers quoted are measured, not estimated. `proposal.md` in this directory holds the earlier technical sketch; where the clarification session changed a decision, this file wins.

## 1. Blind review and interleaving (blocks FR-001, FR-004, US1)

**Decision**: Extend `src/grading/review_cli.py` with `--blind` (hide `model` and `run_id` in the prompt shown to the reviewer), `--shuffle-seed N` (deterministic presentation order), and `--interleave a.jsonl b.jsonl ...` (grade several runs in one mixed session). Output is never written to the input files: for each input `eval/results/<run_id>.jsonl` the tool writes `eval/results/<run_id>-blind.jsonl`, a copy of every row with the blind `score` filled in and the row's `run_id` left as the original (so the report can pair protocols by `id`). A row keeps `score: null` until graded; the tool resumes from the `-blind` file if it already exists.

**Rationale**: The clarification session (Q1) requires the 001 result files to stay frozen while both protocols' grades remain available. A sibling file per run is the smallest change that satisfies that and keeps `contracts/evaluation-results-schema.md` unchanged — the `-blind` file is a valid `EvaluationResult` file. Interleaving is what makes the grading blind in practice: with only one file open, the reviewer knows which run they are grading even if the name is hidden.

**Alternatives considered**: In-place grading with a `previous_score` field (rejected: mutates frozen files and needs a schema change); a separate grades-only file keyed by `id` (rejected: every consumer would need a join; the copy is 104 rows, cost is nil).

## 2. Grading report (blocks FR-002, FR-019, SC-001)

**Decision**: New `src/grading/report.py` (`python -m src.grading.report eval/results/a.jsonl eval/results/b.jsonl ... [--baseline-run a]`). For each `(run_id, task_category)` it prints partial-credit mean, fully-correct rate (share of `score == 1`), the 1/0.5/0 counts, and the still-`null` count; for every pair of runs sharing prompt ids it prints improved/worsened/tied counts per category; output is Markdown tables. `grupo_b` is reported as its own row (`task_category: null` → label `grupo_b`). Runs whose file name does not end in `-blind` are marked with a "protocol: earlier (non-blind)" footnote unless the run is a new candidate (naming convention in §12).

**Rationale**: The audit showed the partial-credit mean alone hid that only 7/80 group-A answers were fully correct, and computed the 16/9/79 pairwise comparison by hand. Both belong in one reproducible tool whose output can be pasted into `MODEL_CARD.md`. The consumer rules of `contracts/evaluation-results-schema.md` (report null counts, never mix `run_id`s) already apply and are reused.

**Alternatives considered**: A notebook (rejected: not reviewable in a PR, not testable); extending `review_cli.py` (rejected: separate responsibilities, separate agents).

## 3. Shared prompt formatter and separated evaluation prompts (blocks FR-003, FR-019, US1 scenario 3)

**Decision**: New `src/prompt_format.py::format_prompt(instruction, input="", output=None)` becomes the single implementation of the `### Instrução / ### Entrada / ### Resposta` template; `train_qlora._format_prompt` and `evaluate._format_inference_prompt` delegate to it with no behaviour change. `data/eval/grupo_a_prompts.jsonl` rows gain two optional fields, `instruction` and `input`, authored once by splitting `prompt` at its first `": "` and reviewed by the author; `prompt` is untouched. A contract test asserts `f"{instruction}: {input}" == prompt` for every row that has the fields. `src/evaluate.py` gains `--prompt-format {combined,split}` (default `combined`, i.e. today's behaviour); `split` calls `format_prompt(instruction, input)` and is only valid for rows carrying the fields (`grupo_b` rows always use `combined`). The presentation is encoded in the run id by convention: `<run>` for combined, `<run>-split` for separated.

**Rationale**: 2,696/3,956 training rows use `### Entrada:`; the evaluator never produces it. The gap has to be measured before it can be ruled in or out (SC-002), and the frozen prompt text must not change (FR-022). Splitting at the first `": "` is verified to be unambiguous for all 80 group-A prompts (every one has the form `<instruction>: <text>`), but doing it by hand once, with a reconstruction test, removes any runtime heuristic.

**Alternatives considered**: Runtime splitting in `evaluate.py` (rejected: heuristic in the evaluation path, untestable against intent); training with a fraction of examples folded into single-line form so the model tolerates both (deferred: it is a data change, and the point of this feature is to measure one change at a time).

## 4. Data-quality filters (blocks FR-006–FR-009, US2)

All counts measured on the current `data/train.jsonl`.

| Filter | Decision | Measured effect |
|---|---|---|
| Grammar word boundaries (FR-006) | `revis(e\|ão\|ar)` → `\brevis(e\|ar\|ão\|ando)\b`; `\b` on `corrij`, `conserte`; new `_GRAMMAR_EXCLUDE` = `\b(código\|code\|programa\|função\|script\|sql\|python\|javascript\|bug)\b` (case-insensitive) checked before labelling | removes the 52 substring hits (`previsão` etc.) and 20 code-fix rows from 681 |
| Simplification exclusions (FR-007) | `_SIMPLIFICATION_EXCLUDE` = `curiosidade\|trivia\|\bexpressão\b\|\bequação\b\|\bfração\b\|\bpolinômio\b`; require non-empty `input` | removes 173 trivia + 4 math + 45 no-input rows from 566 → ≈344 |
| Classification label-in-instruction (FR-008) | keep only if `len(output.split()) <= 4` and `normalize(output) in normalize(instruction)`, with `normalize` = the existing `_normalize_label` from `src/grading/rule_based.py` moved to `src/text_normalize.py` | keeps 454/905; drops all 26 `ssrsrs` rows and `canarim-170450` without a hand list |
| Degenerate outputs (FR-009) | new `src/dataset_filters/quality.py::is_degenerate_output`: `re.search(r"(.)\1{5,}\|(..)\2{3,}\|(\S+\s)\3{3,}", text)` or, for `len(text) >= 30`, at most 8 distinct characters. **Calibrated during implementation (Agent 1, verified by the author on the real file)**: the originally planned ratio rule `distinct/len < 0.15` is length-blind and would have flagged 702 ordinary rows (452 summaries); the 2-char-cycle alternation is needed because `ssrsrs…` has no whitespace | 39 rows on the current `train.jsonl` = the audit's 37 + `pica-pau-pau…` (`canarim-273206`) + a `Drs, Drs, Drs, Drs,` run inside a summary (`canarim-061837`); none legitimate |

**Rationale**: Each rule targets a defect that was counted, not hypothesised, and each is a pure function testable with the synthetic-row pattern the existing filter tests already use. The label-in-instruction rule is preferred over an exclusion list because it encodes the shape the evaluation actually needs (label enumerated in the instruction, answer is one of them).

**Alternatives considered**: Hand-curated exclusion id lists (rejected: not reproducible from the sources); an LLM-based relevance classifier over 4k rows (rejected: adds a model dependency to a step that must be deterministic and fingerprintable).

## 5. Deduplication order and normalization (blocks FR-010, US2, FR-014 precondition)

**Decision**: `prepare_dataset.build_dataset` gains `_dedupe_examples()` after `_dedupe_against_eval` and before `rng.shuffle`: first by normalized `(instruction, input, output)`, then by normalized `(instruction, input)`, keeping the first occurrence in source order. Normalization = NFKC, lowercase, collapse whitespace, strip trailing `.`/space. `split_train_validation` is unchanged; because the split happens after dedupe, train/validation overlap becomes impossible, and a new contract test over the generated files asserts it.

**Rationale**: Measured 58 excess triples and 64 excess pairs in train, 25 triples shared with validation. Held-out evaluation (FR-014) is meaningless with overlap, so this is a hard precondition, not a nicety. Deduping before the shuffle keeps the result independent of the seed.

**Alternatives considered**: Near-duplicate clustering (MinHash) — deferred; exact-normalized dedupe removes every case the audit counted, and near-duplicates across *different* instructions on the same text are legitimate training variety.

## 6. Seed classification examples (blocks FR-011, US2 scenario 3)

**Decision**: `data/seed/classification_4class.jsonl` holds `InstructionExample` rows with `source: "seed-llm"`, `task_category: "classification"`, instruction exactly `Classifique a mensagem como reclamação, dúvida, elogio ou solicitação`, the message in `input`, and `output` ∈ {`reclamação`, `dúvida`, `elogio`, `solicitação`}. `data/seed/README.md` records the generating model and version, the date, a link to or quotation of its usage terms and the author's compatibility conclusion, the generation prompt used, how many rows were generated/kept/edited/discarded, and the author's written confirmation that the 16 evaluation messages were checked against every kept row. `prepare_dataset` gains `--seed-dir data/seed`; seed rows go through the same `validate_instruction_example`, `_dedupe_against_eval`, quality filter, dedupe and cap as public rows. A contract test enforces ≥30 per label, ≤40% for any label, and zero exact overlap with evaluation prompts.

**Rationale**: Clarification Q2 chose LLM generation with author review; the spec requires disclosure and terms compatibility. Keeping provenance in a sidecar README rather than per-row fields keeps `train.jsonl` rows uniform (extra keys are tolerated by `validate_instruction_example`, but a `source` value is enough for the preparation report's per-source count).

**Choice of generating model**: left to the author at execution time; the plan only fixes what must be recorded. Constraint to apply when choosing: the provider's terms must permit using outputs to train a model that is redistributed non-commercially under CC BY-NC 4.0. If the chosen model's terms fail that test, the spec's edge case applies (regenerate with another model or write by hand).

**Alternatives considered**: Author-written only (rejected by Q2); per-row `generator` field (rejected: redundant with the README and noisy in the training file).

## 7. Held-out evaluation as instrumentation (blocks FR-014, US3, Q3 of clarifications)

**Decision**: `train_qlora.py` gains `--validation data/validation.jsonl` (required). `SFTConfig` gets `eval_strategy="epoch"`, `per_device_eval_batch_size=batch_size`, `save_strategy="epoch"` (already), `save_total_limit=None` (keep every epoch), and **no** `load_best_model_at_end`. After training, the run's adapter is saved from the final model as today; the manifest records `eval_loss` per epoch (read from `trainer_state.json` `log_history`) and `best_epoch` (argmin). Evaluating the best-epoch checkpoint is a separate `evaluate.py --adapter adapters/<run>/checkpoint-<step>` invocation with run id `<run>-best`.

**Rationale**: Clarification Q3 separated "measure the curve" from "change which model is saved" so that the second candidate differs from the first in one factor only. `trl` 1.13.0's `SFTConfig` exposes all of these fields (verified by signature inspection); epoch checkpoints are already produced, so the best-epoch row costs no training.

**Alternatives considered**: `load_best_model_at_end=True` (rejected by Q3: bundles selection into the run); a third training run (rejected: unnecessary given per-epoch checkpoints).

## 8. Response-only objective (blocks FR-015, FR-018)

**Decision**: New config key `training.completion_only_loss: false` in `configs/train.yaml` (default keeps v2 behaviour). When `true`, `_run_training` builds the dataset as `{"prompt": format_prompt(instruction, input), "completion": output}` instead of `{"text": ...}` and does not pass `dataset_text_field`. `trl` 1.13.0 then computes loss on the completion only (`completion_only_loss=None` resolves to `True` for prompt-completion datasets) and appends `eos_token` to the completion automatically (`SFTTrainer`'s internal `add_eos` handles both `text` and `completion` columns — verified in the installed source), so answers still terminate.

**Rationale**: Today's `text` format spends part of the objective predicting the instruction and input. The change is a documented `trl` feature, config-gated so v2 stays reproducible (FR-015), and the EOS question that would have been the main risk is settled by reading the installed code.

**Alternatives considered**: Manual label masking with a custom collator (rejected: reimplements what `trl` already does); conversational/chat-template format (rejected: the base model has no chat template and the project's template is the `### Instrução` one).

## 9. Run manifests (blocks FR-016, SC-005)

**Decision**: New `src/run_manifest.py::write_manifest(path, **sections)` producing JSON with: `kind` (`training` | `evaluation`), `run_id`, `created_at`, `git_commit` (`git rev-parse HEAD`, plus `dirty: true/false` from `git status --porcelain`), `library_versions` (`torch`, `transformers`, `peft`, `trl`, `bitsandbytes`, `datasets` via `importlib.metadata.version`), `base_model` (`repo_id` + `revision` from `huggingface_hub.model_info(repo_id).sha`), `datasets` (path + SHA256 + row count for every JSONL consumed), `config` (the full loaded YAML), `prompt_format` (`combined` | `split` | `train-template`), and for training runs `eval_loss_by_epoch`, `best_epoch`, `adapter_path`, `checkpoints`; for evaluation runs `adapter_path` (or `null`), `inference_config`, `results_path`. Written to `adapters/<run_id>/run_manifest.json` (next to the adapter, gitignored) plus a byte-identical tracked copy at `runs/<run_id>.manifest.json`, and to `eval/results/<run_id>.manifest.json` for evaluation runs — the tracked copy exists precisely because `adapters/` is not committed and SC-005 needs the provenance reviewable in the PR.

**Rationale**: FR-016 lists exactly these fields; every value is obtainable offline except the base-model revision, which is one Hub metadata call and can fall back to the locally cached commit hash. SHA256 of the dataset files is what makes SC-005's "same sources → same fingerprint" checkable.

**Alternatives considered**: An experiment-tracking service (rejected: external dependency, `report_to=[]` is deliberate); Git tags per run (rejected: does not capture data or library state).

## 10. Additional public datasets for a short category (blocks FR-012/FR-013's conditional remedy)

**Decision**: Not pre-selected. The remedy is conditional on the preparation report, and the only category expected to be short is simplification (≈344 vs 350). Procedure, in order: (1) widen `_SIMPLIFICATION_KEYWORDS` with `\bem linguagem (simples|acessível)\b|\bpara (uma )?criança\b|\bem palavras simples\b`, measure the count and audit a 30-row sample for precision ≥90% exactly as was done for grammar in v2; (2) only if still short, evaluate candidate public PT-BR instruction datasets with the same regex + sample-audit method, admitting one only if its license permits redistribution of a derived model under CC BY-NC 4.0 and its README documents provenance. Already evaluated and rejected earlier in this project: `CohereLabs/aya_dataset` (Apache-2.0, but only 54 of its 8,997 Portuguese rows matched any of the five categories — yield, not license, was the problem).

**Rationale**: Clarification Q4 allows new public sources but the spec forbids relaxing filters or using generated data for this; the shortfall is small enough that step (1) will likely close it. Naming specific additional datasets here without checking their licenses would be exactly the unverified claim the audit criticised.

## 11. Development prompt set scoring (resolves the clarification session's deferred item; blocks FR-005)

**Decision**: `data/dev/dev_prompts.jsonl` = 10 rows per category sampled (seeded) from the cleaned `validation.jsonl`, in `EvaluationPrompt` shape with `group: "dev"`, `grading_method: "manual_review"` for all categories except classification (`rule_based`, `expected` = the label), and `expected` = the source `output` kept as a reference for the reviewer. Scored with the same `review_cli.py --blind` flow. It is used only in the conditional single-factor step (FR-021) and never for the adoption decision.

**Rationale**: Automatic reference similarity was already tried in feature 001 for grammar and could not distinguish a valid paraphrase from an off-topic answer; that failure mode applies to every open-ended category. Fifty manual grades per comparison is affordable for a step that may never run. `validate_evaluation_prompt` must learn the `dev` group value (one-line change to `EVAL_GROUPS`).

**Alternatives considered**: Reuse `validation.jsonl` loss as the only tuning signal (kept as a first filter, but loss does not measure faithfulness); LLM-as-judge (rejected: adds an unvalidated grader to a feature about grading validity).

## 12. Naming conventions for runs and files (cross-cutting)

**Decision**:
- Evaluation run ids: `<model-run>` (combined presentation), `<model-run>-split` (separated), `<model-run>-best` (best-epoch checkpoint), and `<run>-blind.jsonl` for the blind-graded copy of any of them. Existing ids `baseline`, `qlora-v1`, `qlora-v2`, `official-instruct` are unchanged.
- Training run ids for this feature: `qlora-v3a` (clean data, v2 process), `qlora-v3b` (clean data + response-only objective). Conditional single-factor runs: `qlora-v3c`, `-v3d`, `-v3e` at most (FR-021).
- The official release re-run under the separated presentation, if selected, is `official-instruct-split`.

**Rationale**: The report needs to tell presentation, checkpoint and protocol apart from the file name alone, and FR-022 needs every new result to land in a new file.
