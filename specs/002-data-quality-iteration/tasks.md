---

description: "Task list for the Data Quality & Evaluation Iteration (Manacá-Instruct-PT v3), organized for 3 coding agents + the author, controlled through GitHub (worktrees, branches, PRs, code review) exactly as feature 001"
---

# Tasks: Data Quality & Evaluation Iteration (Manacá-Instruct-PT v3)

**Input**: Design documents from `/specs/002-data-quality-iteration/` (plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md; proposal.md as background)

**Tests**: Included where a contract in `contracts/` names a tested guarantee — the four contracts are the interoperability surface between three independently-reviewed agents and the author's run outputs, so those guarantees are tasks, not optional coverage. No TDD ordering is imposed; each agent PR ships its code and its tests together.

**Organization**: Tasks are grouped by user story (spec.md: US1 P1, US2 P1, US3 P2, US4 P2). Every task carries an **owner** tag — `(Agent 1)`, `(Agent 2)`, `(Agent 3)`, or `(You)` — per plan.md's Delivery Workflow: agents build code and tests in parallel; the author does the serial work (grading, seed review, data audit, GPU runs, decisions, PR review/merge).

## Team & Branch Assignments (from plan.md)

| Owner | Scope | Worktree | Branch |
|---|---|---|---|
| **You** | integration branch; seed generation + review; all blind grading; both training runs; audits; presentation + adoption decisions; PR review/merge; direct commits of run outputs only | repo root | `002-data-quality-iteration` (integration; created in T001 from `001-manaca-instruct-tuning`'s head) |
| **Agent 1** — data | `src/text_normalize.py`, `src/dataset_filters/quality.py`, `src/dataset_filters/grammar_rewriting.py`, `src/prepare_dataset.py`, dataset/seed contract tests | `../manaca-instruct-agent1-dataset` | `agents/agent1-dataset` |
| **Agent 2** — evaluation | `src/prompt_format.py`, `src/dataset_filters/open_ended_tasks.py`, `src/evaluate.py`, `src/grading/review_cli.py`, `src/grading/report.py`, `src/grading/rule_based.py`, `src/schema_validation.py`, `data/eval/grupo_a_prompts.jsonl` split fields, eval contract tests, `MODEL_CARD.md` comparison section | `../manaca-instruct-agent2-eval` | `agents/agent2-eval` |
| **Agent 3** — training infra | `src/run_manifest.py`, `src/train_qlora.py`, `configs/train.yaml`, `runs/` | `../manaca-instruct-agent3-infra` | `agents/agent3-infra` |

## GitHub workflow (applies to every task)

1. Agents work only in their own worktree/branch, rebased onto `origin/002-data-quality-iteration` before each task group; every change is a PR **into `002-data-quality-iteration`** — never into `001-manaca-instruct-tuning` or `main`.
2. Before merging any agent PR: `/code-review` (`/code-review high` for `train_qlora.py`, `prepare_dataset.py`, `review_cli.py`), then `gh pr review --approve` + `gh pr merge`. You are the sole human reviewer.
3. One PR per task group marked "Open PR" below; foundation PRs are deliberately tiny.
4. **Direct commits (You only, on the integration branch)**: run outputs and bookkeeping — `eval/results/*-blind.jsonl`, `eval/results/*.manifest.json`, `runs/*.manifest.json`, `data/dataset_report.{md,json}`, regenerated `data/train.jsonl`/`validation.jsonl`, `data/dev/`, `data/seed/`, `eval/results/{presentation-experiment,final-table,adoption-decision}.md`, this file's status, and the one-line `configs/train.yaml` flag flip for the second candidate. Never source code.
5. **Frozen-file guard (FR-022)**: any diff to `eval/results/{baseline,qlora-v1,qlora-v2,official-instruct}.jsonl`, to `prompt` values in `data/eval/*.jsonl`, or to `adapters/qlora-v{1,2}` is a review blocker; `tests/contract/test_results_immutability.py` (T018) enforces it.
6. Merge order at the end: `002 → 001` (T058), then 001 finishes its own T058/T059 and merges to `main`. 002 never merges to `main` on its own.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the integration branch and bring the three existing agent worktrees onto it.

- [X] T001 (You) Create and push the integration branch from the current head of `001-manaca-instruct-tuning`: `git checkout 001-manaca-instruct-tuning && git pull && git checkout -b 002-data-quality-iteration && git push -u origin 002-data-quality-iteration`; then set `.specify/feature.json` to `specs/002-data-quality-iteration` (already set; gitignored) — **done** 2026-09-15: `002-data-quality-iteration` created from `bfab4d8` and pushed
- [X] T002 [P] (You) Sync Agent 1's worktree: in `../manaca-instruct-agent1-dataset`, `git fetch origin && git rebase origin/002-data-quality-iteration && git push --force-with-lease` — **done**
- [X] T003 [P] (You) Sync Agent 2's worktree: in `../manaca-instruct-agent2-eval`, same commands — **done**
- [X] T004 [P] (You) Sync Agent 3's worktree: in `../manaca-instruct-agent3-infra`, same commands — **done** (all three rebased to the 002 head; force-pushed with lease)
- [X] T005 (You) Confirm the starting state on the integration branch: `~/.venvs/global/bin/python3 -m pytest tests/ -q` → all green (82 at planning time); `sha256sum eval/results/{baseline,qlora-v1,qlora-v2,official-instruct}.jsonl > /tmp/frozen-before.txt` for later comparison — **done**: 82 passed; frozen SHA256 (baseline `8e07ebfc…8304`, qlora-v1 `2bf1c504…0ac4`, qlora-v2 `286abe87…620d`, official-instruct `aec23419…df9e3`; full values in T018's test once it lands)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Three tiny shared modules that every later PR imports. Each is its own PR so the parallel phase never co-edits a file.

**⚠️ CRITICAL**: T006–T014 must be merged before any user-story task starts.

- [X] T006 [P] (Agent 1) Create `src/text_normalize.py` with `normalize(text: str) -> str` = NFKC → lowercase → collapse whitespace → strip trailing `.`/spaces (contracts/dataset-preparation.md); unit tests in `tests/unit/test_text_normalize.py` (accents, `"Reclamação."` → `"reclamação"`, whitespace, NFKC width forms) — **done**
- [X] T007 (Agent 1) Open PR (`agents/agent1-dataset` → `002-data-quality-iteration`) with T006 — **done**: [PR #24](https://github.com/Wolfloiz/manaca-instruct/pull/24)
- [X] T008 (You) `/code-review` and merge T007's PR — **done**: diff reviewed, merged (GitHub refuses self-approval, as in 001); 88/88
- [X] T009 [P] (Agent 2) Create `src/prompt_format.py` with `format_prompt(instruction, input="", output=None)` exactly per contracts/evaluation-presentation.md (omit `### Entrada:` block when `input` is empty; end with `### Resposta:\n` when `output is None`); make `src/evaluate.py::_format_inference_prompt(text)` return `format_prompt(text)`; unit tests in `tests/unit/test_prompt_format.py` covering with/without input, with/without output, and asserting equality with `src.train_qlora._format_prompt(example)` and `src.evaluate._format_inference_prompt(text)` on sample rows (existing tests in `tests/unit/test_train_qlora.py` and `tests/unit/test_evaluate.py` must stay green untouched) — **done**
- [X] T010 [P] (Agent 2) Update `src/schema_validation.py`: `EVAL_GROUPS` gains `"dev"`; `validate_evaluation_prompt` enforces "`instruction` and `input` are either both present or both absent" and, when present, `f"{instruction}: {input}" == prompt` (raise `SchemaError` otherwise); `grupo_b` rows must not carry them; unit tests added to `tests/contract/test_dataset_schema.py` — **done**
- [X] T011 (Agent 2) Open PR (`agents/agent2-eval` → `002-data-quality-iteration`) with T009–T010 — **done**: [PR #25](https://github.com/Wolfloiz/manaca-instruct/pull/25)
- [X] T012 (You) `/code-review` and merge T011's PR — **done**: merged; 94/94
- [X] T013 [P] (Agent 3) Create `src/run_manifest.py` with `write_manifest(path: Path, kind: str, run_id: str, **fields) -> dict` producing the common fields of contracts/run-manifest-schema.md (`status`, `error`, `created_at` ISO-8601 UTC, `git_commit` via `git rev-parse HEAD`, `git_dirty` via `git status --porcelain`, `library_versions` for torch/transformers/peft/trl/bitsandbytes/datasets via `importlib.metadata.version` with `null` when absent, `base_model{repo_id, revision}` via `huggingface_hub.model_info(...).sha` with a local-cache fallback and `revision_source: "local-cache"`, `datasets[]{path, sha256, rows}` computed from file bytes) plus a helper `sha256_of(path)`; also create `runs/.gitkeep`; unit tests in `tests/unit/test_run_manifest.py` with a fake git/hub layer (fields present, SHA256 matches a synthetic file, `status: failed` path) — **done** (real helpers smoke-tested: Hub revision of the base model resolved live)
- [X] T014 (Agent 3) Open PR (`agents/agent3-infra` → `002-data-quality-iteration`) with T013; (You) `/code-review` and merge — **done**: [PR #26](https://github.com/Wolfloiz/manaca-instruct/pull/26) merged; 108/108 on the integration branch

**Checkpoint**: **reached 2026-09-15** — `normalize`, `format_prompt`, `build_manifest`/`write_manifest` and the extended prompt validator are on the integration branch (`4b80f55`), all three agent worktrees are rebased onto it, 108/108 tests pass. Story work (T015+, T028+, T041+) can start in parallel.

---

## Phase 3: User Story 1 — Make the existing evaluation trustworthy (Priority: P1) 🎯 MVP

**Goal**: Blind interleaved grading with sibling `-blind` result files, a two-metric report, and the prompt-presentation experiment on the existing qlora-v2 adapter — an honest comparison table with no training (spec.md US1; SC-001, SC-002).

**Independent Test**: quickstart.md "Validate User Story 1" — `qlora-v2-blind.jsonl` and `qlora-v2-split-blind.jsonl` exist, the report shows `mean` and `full_rate` per category, the presentation decision is written, and the four 001 result files are byte-identical to `/tmp/frozen-before.txt`.

### Implementation for User Story 1 (Agent 2)

- [X] T015 [P] [US1] (Agent 2) Author the split fields on all 80 rows of `data/eval/grupo_a_prompts.jsonl`: add `instruction` = text before the first `": "` and `input` = text after it (verified during planning: every row has exactly one `": "`), leaving `prompt` byte-identical; add `tests/contract/test_eval_prompt_split.py` asserting for every `grupo_a` row that both fields exist and `instruction + ": " + input == prompt`, and that no `grupo_b` row has them — **done** (all 80 rows; every original byte identical, verified at review)
- [X] T016 [P] [US1] (Agent 2) Extend `src/evaluate.py`: `--prompt-format {combined,split}` (default `combined`; `split` uses `format_prompt(row["instruction"], row["input"])`, falls back to `combined` for rows without the fields, and fails fast with a clear error if any `grupo_a` row lacks them); `--inference-config PATH` (default `configs/inference.yaml`); after the last row, write `eval/results/<run_id>.manifest.json` via `run_manifest.write_manifest` with the evaluation-only fields of contracts/run-manifest-schema.md (`model`, `adapter_path`, `checkpoint`, `adapter_manifest`, `inference_config_path`, `prompt_files`, `results_path`, `rows_written` == line count, `prompt_format`); unit tests in `tests/unit/test_evaluate.py` with mocked `_load_model`/`_generate` (split emits `### Entrada:`, combined does not, missing fields raise, manifest written with `rows_written` correct) — **done**
- [X] T017 [P] [US1] (Agent 2) Extend `src/grading/review_cli.py` per contracts/blind-review-and-report.md: `--blind` (reviewer prompt shows only position counter, `task_category`, `prompt`, `expected` when non-null, `output` — never `model`, `run_id`, or file name), `--shuffle-seed N` (deterministic order over all still-ungraded `manual_review` rows), `--interleave` (accept several files, route each grade back by `(file, id, model, run_id)`); output rules: never write to an input file; for each input `eval/results/<run_id>.jsonl` create/resume `eval/results/<run_id>-blind.jsonl` (full copy with `manual_review` scores reset to `null` on first creation; `rule_based` scores kept), fill only `null` scores, write after every accepted grade, accept `1`/`0.5`/`0`/`s`/`q`, print per-file graded/remaining and input SHA256 before/after; unit tests in `tests/unit/test_review_cli.py` (blind prompt contains no `model=`/`run_id=`; interleaved grades land in the right `-blind` file and row; resume fills only nulls; input bytes unchanged) — **done**
- [X] T018 [P] [US1] (Agent 2) Add `tests/contract/test_results_immutability.py` pinning the SHA256 of `eval/results/{baseline,qlora-v1,qlora-v2,official-instruct}.jsonl` and of every `prompt` value in `data/eval/grupo_a_prompts.jsonl` / `grupo_b_prompts.jsonl` (hash of the concatenated prompt strings) as constants; the test fails if any changes (FR-022) — **done**
- [X] T019 [P] [US1] (Agent 2) Create `src/grading/report.py` per contracts/blind-review-and-report.md: CLI `python -m src.grading.report RESULTS... [--pair A B]... [--markdown-out PATH]`; per-run table with columns `run | protocol | category | n | mean | full_rate | n1 | n05 | n0 | n_null` (categories = five task categories then `grupo_b`; `protocol` = `blind` when the file name ends in `-blind.jsonl` or the run id starts with `qlora-v3`, else `earlier (non-blind)`; `classification` row also prints `correct/16`); pairwise section per `--pair` with `improved/worsened/tied/not comparable` per category on shared `id`s; footnotes listing files and the verbatim sentence "Means include partial credit (0.5); `full_rate` counts only answers graded 1."; raise if one file mixes `run_id`s; unit tests in `tests/unit/test_report.py` with two synthetic files and hand-computed expectations, a mixed-run-id file raising, and `n_null` visible without changing `mean` — **done**
- [X] T020 [US1] (Agent 2) Make `src/grading/rule_based.py::_normalize_label` delegate to `src.text_normalize.normalize` (identical behaviour; `tests/unit/test_rule_based.py` unchanged and green) — **done**
- [X] T021 [US1] (Agent 2) Open PR (`agents/agent2-eval` → `002-data-quality-iteration`) with T015–T020 — **done**: [PR #28](https://github.com/Wolfloiz/manaca-instruct/pull/28)
- [X] T022 [US1] (You) `/code-review high` (review_cli.py must never touch a frozen file) and merge T021's PR; re-run `pytest tests/ -q` — **done**: diff reviewed (review_cli writes only `-blind`, SHA256-guarded; prompt file change is annotation-only), merged; 165 passed + 13 expected skips; frozen files unchanged. Contract note: `report.py` refuses an original and its `-blind` copy in one call (run the report once per protocol)

### Run User Story 1 (You)

- [x] T023 [US1] (You) Presentation experiment: `python -m src.evaluate --model manaca-instruct-pt --adapter adapters/qlora-v2 --prompts data/eval/grupo_a_prompts.jsonl data/eval/grupo_b_prompts.jsonl --prompt-format split --run-id qlora-v2-split --out eval/results/qlora-v2-split.jsonl` → 104 rows + `eval/results/qlora-v2-split.manifest.json` with `prompt_format: split`
- [x] T024 [US1] (You) Blind interleaved grading of both v2 presentations (~176 grades): `python -m src.grading.review_cli eval/results/qlora-v2.jsonl eval/results/qlora-v2-split.jsonl --blind --interleave --shuffle-seed 7` → `eval/results/qlora-v2-blind.jsonl`, `eval/results/qlora-v2-split-blind.jsonl`; confirm printed SHA256s match `/tmp/frozen-before.txt`
- [x] T025 [US1] (You) Report and presentation decision: `python -m src.grading.report eval/results/qlora-v2-blind.jsonl eval/results/qlora-v2-split-blind.jsonl --pair qlora-v2 qlora-v2-split --markdown-out eval/results/presentation-experiment.md`; apply FR-019 (select `split` if any category differs by ≥ 2/16 = 0.125 in `mean` or `full_rate`, else `combined`) and start `eval/results/adoption-decision.md` with a "Presentation" section recording the choice and the per-category deltas
- [x] T026 [US1] (You) Official release under the selected presentation: if `split` was selected, run `python -m src.evaluate --model manaca-1b-instruct --prompts data/eval/grupo_a_prompts.jsonl data/eval/grupo_b_prompts.jsonl --prompt-format split --run-id official-instruct-split --out eval/results/official-instruct-split.jsonl`; then blind-grade the official file for the selected presentation (~88 grades): `python -m src.grading.review_cli eval/results/official-instruct[-split].jsonl --blind --shuffle-seed 7`
- [x] T027 [US1] (You) Commit run outputs directly to `002-data-quality-iteration`: the `-blind` files, manifests, `presentation-experiment.md`, `adoption-decision.md` (presentation section); mark T023–T026 done here

**Checkpoint**: SC-001 and SC-002 met; the honest v2-vs-official table exists. This is the MVP — it has value even if nothing below is ever trained.

---

## Phase 4: User Story 2 — Train on clean, on-task data (Priority: P1)

**Goal**: Regenerated `data/train.jsonl` / `validation.jsonl` free of the audited defects, with author-reviewed seed classification examples, a development prompt set, and a preparation report (spec.md US2; SC-003, SC-004).

**Independent Test**: quickstart.md "Validate User Story 2" — `tests/contract/test_dataset_quality.py` and `test_seed_examples.py` green against the produced files, fingerprints identical across two runs, 30-row grammar audit ≥ 27, `data/dataset_report.md` lists per-source counts and licenses.

### Implementation for User Story 2 (Agent 1 + Agent 2)

- [X] T028 [P] [US2] (Agent 1) Create `src/dataset_filters/quality.py` with `is_degenerate_output(text: str) -> bool`: true when `re.search(r"(.)\1{5,}|(\S+\s)\2{3,}", text)` matches or when `len(text) >= 30 and len(set(text)) / len(text) < 0.15`; unit tests in `tests/unit/test_quality.py` (`"rochedo . . . . . . . ."` → True, `"E-mail : ssrsrsrsrs"` → True, a normal three-sentence answer → False, short normal label → False) — **done** — rule calibrated on the real file (39 rows, all genuine; the contract's ratio rule would have flagged 702), contract/research updated
- [X] T029 [P] [US2] (Agent 1) Amend `src/dataset_filters/grammar_rewriting.py`: `_GRAMMAR_KEYWORDS` uses `\brevis(e|ar|ão|ando)\b`, `\bcorrij`, `\bconserte\b` (keep the other terms); add `_GRAMMAR_EXCLUDE = re.compile(r"\b(código|code|programa|função|script|sql|python|javascript|bug)\b", re.I)` checked in `_classify` before the grammar label; unit tests in `tests/unit/test_grammar_rewriting.py`: `"Dada uma previsão do tempo, liste…"` → `None`, `"Encontre os erros no código a seguir e corrija-os"` → `None`, `"Revise a concordância do texto"` → `grammar_correction`, existing rewriting cases unchanged — **done**
- [X] T030 [P] [US2] (Agent 2) Amend `src/dataset_filters/open_ended_tasks.py`: `_SIMPLIFICATION_EXCLUDE = re.compile(r"curiosidade|trivia|\bexpressão\b|\bequação\b|\bfração\b|\bpolinômio\b", re.I)` checked before the simplification label; simplification rows require non-empty `input` (`context`); classification rows kept only when `len(output.split()) <= 4` and `normalize(output) in normalize(instruction)` using `src.text_normalize.normalize`; unit tests in `tests/unit/test_open_ended_tasks.py`: trivia instruction → `None`, `"Simplifique a expressão aritmética dada"` → `None`, simplification without context dropped, `("Classifique como positivo ou negativo…", output="Negativo")` kept, `(…, output="E-mail : ssrsrsrs")` dropped, `("Classifique a língua do texto…", output="E-mail")` dropped — **done** (+ `stats: Counter` kwarg convention shared with Agent 1)
- [X] T031 [US2] (Agent 2) Open PR (`agents/agent2-eval` → `002-data-quality-iteration`) with T030; (You) `/code-review` and merge — **done**: [PR #27](https://github.com/Wolfloiz/manaca-instruct/pull/27) merged; 116/116
- [X] T032 [US2] (Agent 1) Extend `src/prepare_dataset.py` per contracts/dataset-preparation.md in this pipeline order: source filters → `--seed-dir DIR` (load every `*.jsonl`, validate with `validate_instruction_example`, append) → quality filter (`is_degenerate_output`) → `_dedupe_against_eval` extended to also compare each row's `(instruction, input)` with the eval prompts' split fields → new `_dedupe_examples()` (normalized `(instruction, input, output)` then normalized `(instruction, input)`, first occurrence wins, **before** `rng.shuffle`) → shuffle → cap → split → optional `--dev-out PATH --dev-per-category 10` (seeded sample from the **validation** split, written as `EvaluationPrompt` rows with `group: "dev"`, `id: dev-<category>-NNN`, `instruction`/`input` copied, `prompt = f"{instruction}: {input}"` or `instruction` when input is empty, `expected` = source `output`, `grading_method` = `rule_based` for classification else `manual_review`, `source_id`) → report writer producing `data/dataset_report.json` with exactly the fields `generated_at, seed, sources{name→{license, rows_in, rows_kept}}, by_category{…→{raw, after_filter, after_quality, after_eval_dedupe, after_dedupe, after_cap, train, validation}}, dropped_by_reason{no_output, exclude_regex, label_not_in_instruction, missing_input, degenerate_output, overlap_with_eval, duplicate_triple, duplicate_pair, over_cap}, fingerprints{path→sha256}, warnings[]` and `data/dataset_report.md` rendering it as tables; stderr warning for any category < 350; unit tests in `tests/unit/test_prepare_dataset.py` (3 copies of a triple → 1; same pair different outputs → 1; seed rows pass through the same stages; dev rows come only from validation; report counts and `warnings` for a category under 350) — **done**
- [X] T033 [US2] (Agent 1) Add `tests/contract/test_dataset_quality.py` (skips when `data/dataset_report.json` is absent, i.e. before the first regenerated dataset): over `data/train.jsonl` + `data/validation.jsonl` assert no grammar instruction matches `previs` or the code-exclusion terms, no simplification instruction contains `curiosidade`, every classification `normalize(output)` is contained in its `normalize(instruction)`, no `is_degenerate_output`, no normalized triple appears twice across both files, no normalized pair appears in both files, no row's combined text or split pair equals an eval prompt, total in [3000, 5000], and each category ≥ 350 or named in `warnings`; and `tests/contract/test_seed_examples.py` (skips when `data/seed/` is absent): ≥ 30 rows per label, no label > 40%, `id` matches `seed-llm-\d{6}`, `source == "seed-llm"`, `output` ∈ {`reclamação`, `dúvida`, `elogio`, `solicitação`}, `instruction` exactly `Classifique a mensagem como reclamação, dúvida, elogio ou solicitação`, `README.md` present and containing the words "generating model" / "modelo gerador", zero `(instruction, input)` equal to any eval prompt's split fields — **done**
- [X] T034 [US2] (Agent 1) Open PR (`agents/agent1-dataset` → `002-data-quality-iteration`) with T028, T029, T032, T033 — **done**: [PR #29](https://github.com/Wolfloiz/manaca-instruct/pull/29) (opened after rebasing onto #27)
- [X] T035 [US2] (You) `/code-review high` and merge T034's PR; re-run `pytest tests/ -q` (the two new contract tests skip until data exists) — **done**: prepare_dataset.py diff read in full (dedupe order, normalized eval-overlap, seed validation, report fields), merged; 134 passed + 13 skips

### Run User Story 2 (You)

- [X] T036 [US2] (You) Seed examples: choose a generating language model whose terms permit training a non-commercial CC BY-NC 4.0 model on its outputs (record the terms reference); generate ≥ 160 candidate messages (≥ 40 per label) with a prompt asking for varied customer-service messages; review every row (keep / edit / discard), checking each against the 16 classification prompts in `data/eval/grupo_a_prompts.jsonl` for reuse or paraphrase; write `data/seed/classification_4class.jsonl` and `data/seed/README.md` (model + version, date, terms reference and compatibility conclusion, generation prompt, counts generated/kept/edited/discarded, the confirmation sentence); run `pytest tests/contract/test_seed_examples.py -q` — **done**: 207 candidates from Qwen2.5-7B-Instruct Q4_K_M (Apache-2.0) via llama-server, reviewed one by one (147 kept / 50 edited / 10 discarded) → 197 rows; `data/seed/README.md`; 5/5 contract tests
- [X] T037 [US2] (You) Regenerate the dataset: `python -m src.prepare_dataset --sources alpaca-pt-br canarim --seed-dir data/seed --out-dir data/ --dev-out data/dev/dev_prompts.jsonl`; run `pytest tests/contract/test_dataset_quality.py -q`; run the command a second time and confirm `sha256sum data/train.jsonl data/validation.jsonl` equals `data/dataset_report.json` → `fingerprints` — **done**: two pipeline bugs fixed on the way (set-ordered category dict made the split non-reproducible across processes; the cap discarded 170/197 seed rows — seeds now kept ahead of public rows); fingerprints identical across runs (`9b3d3ca3…` / `4d0e9801…`); 3,752 rows
- [X] T038 [US2] (You) Grammar audit: sample 30 random `grammar_correction` rows from `data/train.jsonl` (quickstart.md US2 step 5), count genuine language corrections (pass: ≥ 27), append the count to `data/dataset_report.md` — **done**: first build ~14/30 (`revis*` = film/book *reviews*, empty-input exercises) → grammar filter tightened (no `revis*`, sentence-building verbs excluded, `input` required; 676 → 394 rows); final sample **20/30** (24/30 counting grammaticality judgments) — below 27, documented shortfall in `data/dataset_report.md` (removing the remaining analysis/judgment/rewrite rows would leave 349 < 350)
- [X] T039 [US2] (You) Category minimum: if `warnings` is non-empty (simplification is expected near 344), apply the remedy order from FR-012 — first ask Agent 2 for a PR widening `_SIMPLIFICATION_KEYWORDS` with `\bem linguagem (simples|acessível)\b|\bpara (uma )?criança\b|\bem palavras simples\b`, regenerate, and audit a 30-row simplification sample for ≥ 27 on-task; only if still short, evaluate an additional public dataset per research.md §10 (license compatible with CC BY-NC 4.0 redistribution, regex + sample audit, new `src/dataset_filters/<name>.py` via an Agent 1 PR, entry in `sources` with its license); otherwise document the shortfall in the report — **done**: `warnings: []` (simplification 358 ≥ 350), no remedy needed
- [ ] T040 [US2] (You) Commit directly to `002-data-quality-iteration`: `data/train.jsonl`, `data/validation.jsonl`, `data/dev/dev_prompts.jsonl`, `data/seed/`, `data/dataset_report.{md,json}`; mark T036–T039 done

**Checkpoint**: SC-003 and SC-004 met; the v3 dataset is committed with its report and fingerprints.

---

## Phase 5: User Story 3 — Training that measures generalization and records provenance (Priority: P2)

**Goal**: `train_qlora.py` evaluates a held-out set every epoch, keeps every epoch checkpoint, saves the last-epoch adapter, optionally trains with the response-only objective, and writes a manifest (with a tracked copy under `runs/`) for every run including failed ones (spec.md US3; SC-005).

**Independent Test**: quickstart.md "Validate User Story 3" — a 200-row smoke run produces `adapters/smoke-v3/run_manifest.json` and `runs/smoke-v3.manifest.json` with `eval_loss_by_epoch`, `best_epoch`, `checkpoints[]`, `adapter_epoch == last epoch`, dataset SHA256 equal to the report fingerprint; the response-only smoke run terminates its answers.

### Implementation for User Story 3 (Agent 3)

- [X] T041 [P] [US3] (Agent 3) Amend `configs/train.yaml`: add `training.completion_only_loss: false` with a comment that `false` reproduces qlora-v2's full-sequence loss and `true` switches to the prompt-completion (response-only) objective; `load_config` in `src/train_qlora.py` defaults it to `false` when absent — **done**
- [X] T042 [US3] (Agent 3) Amend `src/train_qlora.py` per contracts/run-manifest-schema.md: required `--validation PATH`; pre-check refusing to start if any normalized `(instruction, input)` (via `src.text_normalize.normalize`) is shared between train and validation; `_format_prompt` delegates to `src.prompt_format.format_prompt`; `SFTConfig` adds `eval_strategy="epoch"`, `per_device_eval_batch_size=train["batch_size"]`, keeps `save_strategy="epoch"`, sets no `save_total_limit` and no `load_best_model_at_end`; `SFTTrainer(..., eval_dataset=...)`; when `completion_only_loss` is true build rows as `{"prompt": format_prompt(instruction, input), "completion": output}` and do not pass `dataset_text_field`, otherwise keep the `{"text": ...}` path unchanged; remove the dead `formatted = [...]  # noqa: F841` line in `train()`; after training read `trainer_state.json` `log_history` to fill `eval_loss_by_epoch`, `train_loss_by_epoch`, `best_epoch` (argmin eval loss), `checkpoints[]{epoch, path}`, `adapter_epoch` (last), `adapter_path`, `validation_path`, `completion_only_loss`; write the manifest to `adapters/<run_id>/run_manifest.json` and a byte-identical copy to `runs/<run_id>.manifest.json`; on any exception still write both manifests with `status: failed` and `error` before re-raising; unit tests in `tests/unit/test_train_qlora.py` with a mocked `SFTTrainer`/`SFTConfig` (eval_dataset passed; config fields; prompt-completion columns when the flag is true and `text` when false; overlap refusal; failure manifest written) — **done** (+ review fixes: numeric `checkpoint-*` order, ceil epoch buckets, reused run-id guard, `BaseException` so Ctrl-C still writes the failed manifest, uniform failed-manifest fields)
- [X] T043 [US3] (Agent 3) Open PR (`agents/agent3-infra` → `002-data-quality-iteration`) with T041–T042 — **done** as a direct commit on `002-data-quality-iteration` (no agent PR)
- [X] T044 [US3] (You) `/code-review high` and merge T043's PR — **done**: `/code-review high src/train_qlora.py` on the working tree, 6 findings fixed before committing; 173 passed + 13 expected skips

### Run User Story 3 (You)

- [ ] T045 [US3] (You) Smoke run on a slice (`head -n 200 data/train.jsonl > /tmp/train-smoke.jsonl; head -n 40 data/validation.jsonl > /tmp/val-smoke.jsonl`): `python -m src.train_qlora --config configs/train.yaml --dataset /tmp/train-smoke.jsonl --validation /tmp/val-smoke.jsonl --run-id smoke-v3`; inspect `runs/smoke-v3.manifest.json` for the US3 fields; then flip `completion_only_loss: true` locally, run `--run-id smoke-v3-co`, evaluate 3 rows of `data/dev/dev_prompts.jsonl` with `--adapter adapters/smoke-v3-co` and confirm the answers end before `max_new_tokens`; revert the flag; delete `adapters/smoke-*` and `runs/smoke-*` (do not commit smoke manifests)

**Checkpoint**: the trainer is instrumented and reproducible; SC-005's fingerprint link is proven on the smoke run.

---

## Phase 6: User Story 4 — Two controlled follow-up runs and a documented decision (Priority: P2)

**Goal**: `qlora-v3a` (clean data, v2 process) and `qlora-v3b` (clean data + response-only objective), evaluated under the selected presentation, blind-graded, compared with v2 and the official release, and adopted or declined by FR-020 (spec.md US4; SC-006, SC-007, SC-008).

**Independent Test**: quickstart.md "Validate User Story 4" — `eval/results/final-table.md` shows all rows with both metrics, `eval/results/adoption-decision.md` records the rule checks per candidate, the outcome and the attribution, citing only `-blind` files and manifests with `git_dirty: false`.

- [ ] T046 [US4] (You) Train the data-only candidate with `completion_only_loss: false`: `python -m src.train_qlora --config configs/train.yaml --dataset data/train.jsonl --validation data/validation.jsonl --run-id qlora-v3a` (~10–15 min); confirm `runs/qlora-v3a.manifest.json` has `git_dirty: false` and `datasets[].sha256` equal to the report fingerprints; commit the manifest
- [ ] T047 [US4] (You) Flip `configs/train.yaml` to `completion_only_loss: true` and commit that one-line change directly (message: "configs: enable completion_only_loss for qlora-v3b"); train `--run-id qlora-v3b`; commit `runs/qlora-v3b.manifest.json`; note its `best_epoch` vs `adapter_epoch`
- [ ] T048 [US4] (You) Evaluate both candidates under the presentation selected in T025 (commands in quickstart.md US4 step 2; run ids `qlora-v3a[-split]`, `qlora-v3b[-split]`)
- [ ] T049 [US4] (You) If `qlora-v3b`'s `best_epoch` ≠ `adapter_epoch`: evaluate `--adapter adapters/qlora-v3b/checkpoint-<step of best_epoch>` with run id `qlora-v3b-best[-split]` (no retraining); apply the same to `qlora-v3a` only if it later becomes the candidate under consideration (FR-018)
- [ ] T050 [US4] (You) Blind interleaved grading of all candidate files (~88 grades each): `python -m src.grading.review_cli eval/results/qlora-v3a[-split].jsonl eval/results/qlora-v3b[-split].jsonl [eval/results/qlora-v3b-best[-split].jsonl] --blind --interleave --shuffle-seed 11`
- [ ] T051 [US4] (You) Final table: `python -m src.grading.report` over the `-blind` files of v2 (selected presentation), v3a, v3b, [v3b-best], official (selected presentation) with `--pair qlora-v2[-split] qlora-v3a[-split] --pair qlora-v3a[-split] qlora-v3b[-split]` and `--markdown-out eval/results/final-table.md`; apply FR-020 per candidate — classification correct ≥ 8/16; group-A `full_rate` ≥ 0.20; no category `mean` below v2's blind `mean` under the selected presentation; `grupo_b` relative drop ≤ 10% vs those v2 grades — and complete `eval/results/adoption-decision.md` with the rule checks, the outcome (`adopted: <run_id>` or `declined`), the attribution of each observed difference (data / objective / checkpoint / cannot attribute), and the US4 scenario-3 note if v3b fails where v3a passes
- [ ] T052 [US4] (You) Commit run outputs directly: candidate result files, `-blind` files, manifests, `final-table.md`, `adoption-decision.md`; mark T046–T051 done

**Checkpoint**: the feature's decision exists. If `declined`, qlora-v2 remains feature 001's final model and Phase 7 is considered; if `adopted`, skip to Phase 8.

---

## Phase 7: Conditional single-factor runs (only if no candidate met FR-020; at most 3 runs)

**Purpose**: FR-021 — one factor per run, justified by the candidates' results, tuned on the development set, never on the frozen set.

- [ ] T053 (You) Decide, from `adoption-decision.md`, which single factor each conditional run changes and record it before running: candidates are (a) generation settings on the development set only (`configs/inference-rp1.1.yaml` with `repetition_penalty: 1.1`, `no_repeat_ngram_size: 0`, graded via `review_cli --blind` on `data/dev/dev_prompts.jsonl`), (b) k-bit preparation (`training.gradient_checkpointing` gate + `peft.prepare_model_for_kbit_training` before `get_peft_model`), (c) `lora.target_modules: all-linear`; (b) and (c) need an Agent 3 PR to `src/train_qlora.py` / `configs/train.yaml` each, reviewed with `/code-review high`
- [ ] T054 (You) For each conditional run (`qlora-v3c`, `-v3d`, `-v3e` at most): train from the base model, evaluate on the frozen set once under the selected presentation, blind-grade (~88), append to `final-table.md`, re-apply FR-020, and update `adoption-decision.md`; stop at the first candidate that passes or after the third run

---

## Phase 8: Polish & close-out

**Purpose**: Reporting obligations (FR-023), full validation, hand-off to feature 001's publication step.

- [ ] T055 [P] (Agent 2) Regenerate `MODEL_CARD.md`'s comparison section from `eval/results/final-table.md`: both metrics per category, the `protocol` column marking baseline/qlora-v1 as "earlier (non-blind)", the verbatim partial-credit footnote, the statement that qlora-v2's classification collapsed to a single label, the dataset list with each source's license and contribution from `data/dataset_report.json` (including `seed-llm` with its generating model and the customer-service domain note), and the adopted model's identity; open PR (`agents/agent2-eval` → `002-data-quality-iteration`); (You) review and merge
- [ ] T056 (You) If a candidate was adopted: produce its deployment artifacts by re-running feature 001's T049–T051 procedure on the adopted adapter (`python -m src.merge_adapter --adapter adapters/<adopted> --out models/merged/manaca-instruct-pt`, `python -m src.quantize …`, `python -m src.benchmark --machine rtx-5050 …`, Dell G3 run) so that what gets published is what was evaluated; record the new benchmark rows in `benchmarks/rtx-5050.jsonl` (append, do not delete the v2 rows) with a note in `adoption-decision.md`
- [ ] T057 (You) Run the full quickstart.md validation: `pytest tests/ -q` green (contract tests no longer skipping), `sha256sum eval/results/{baseline,qlora-v1,qlora-v2,official-instruct}.jsonl` equal to `/tmp/frozen-before.txt`, every manifest cited in `adoption-decision.md` has `git_dirty: false`, `data/dataset_report.json` fingerprints equal the committed data files
- [ ] T058 (You) Open the closing PR `002-data-quality-iteration` → `001-manaca-instruct-tuning`, run `/code-review`, merge; then in `specs/001-manaca-instruct-tuning/tasks.md` note that T058 (publish) is unblocked by `eval/results/adoption-decision.md` and which model it publishes; set `.specify/feature.json` back to `specs/001-manaca-instruct-tuning` to finish 001 (T058–T063)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → **Foundational (Phase 2)**: T006–T014 block every story (they are the shared imports).
- **US1 (Phase 3)** and **US2 (Phase 4)** code can proceed in parallel after Phase 2 (different agents, different files; the only cross-link is T030 → T006, already merged).
- **US2 run tasks (T036–T040)** need US2 code merged (T035) and, for the eval-overlap check on split fields, T015 merged (T022).
- **US3 (Phase 5)** code needs T009 (prompt_format) and T013 (run_manifest) merged; its run task (T045) needs the v3 dataset (T040) for a meaningful smoke run.
- **US4 (Phase 6)** needs US1's presentation decision (T025), US2's data (T040), US3's trainer (T044), and the official release's blind file (T026).
- **Phase 7** only if T051 declines; **Phase 8** after T052 (or T054).

### User Story Dependencies

- **US1 (P1)**: independent — deliverable with no data or training changes (MVP).
- **US2 (P1)**: independent of US1 for its code; its run needs T015's split fields for the stricter eval-overlap check.
- **US3 (P2)**: depends on Foundational only for code; on US2 for a meaningful smoke run.
- **US4 (P2)**: depends on US1 (presentation, official baseline), US2 (data), US3 (trainer).

### Parallel Opportunities

- Phase 2: T006, T009+T010, T013 — three agents, three PRs, in parallel.
- Phase 3 / Phase 4 code: Agent 2 on T015–T020 while Agent 1 on T028–T033 and Agent 3 on T041–T042; T030 (Agent 2) can be a separate early PR.
- Author's serial chain: T023→T027 (grading ~264) can overlap with agents' Phase 4/5 PRs; T036 (seed review) overlaps with T041–T044.
- T048 evaluations of v3a and v3b are independent; T055 can start as soon as `final-table.md` exists.

---

## Parallel Example: Phase 2 + start of Phase 3/4/5

```bash
# Three foundation PRs in flight at once (one per worktree):
Task: "(Agent 1) src/text_normalize.py + tests/unit/test_text_normalize.py"            # T006
Task: "(Agent 2) src/prompt_format.py + schema_validation split rule + tests"           # T009-T010
Task: "(Agent 3) src/run_manifest.py + runs/.gitkeep + tests/unit/test_run_manifest.py" # T013

# After they merge, the parallel story work:
Task: "(Agent 2) eval split fields, evaluate.py flags+manifest, review_cli blind, report.py"  # T015-T020
Task: "(Agent 1) quality.py, grammar filter, prepare_dataset pipeline + report, contract tests" # T028-T029, T032-T033
Task: "(Agent 3) train.yaml flag, train_qlora held-out/prompt-completion/manifest"            # T041-T042
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 (T001–T005) and Phase 2 (T006–T014).
2. Phase 3 code (T015–T022) and the author's run (T023–T027).
3. **STOP and VALIDATE**: the honest v2-vs-official table under a blind protocol, with the presentation effect measured — publishable knowledge on its own, no GPU training spent.

### Incremental Delivery

1. + US2 → a verifiably clean dataset with a report (still no training).
2. + US3 → an instrumented, reproducible trainer proven on a smoke run.
3. + US4 → two candidates, one decision, one table; Phase 7 only if needed.
4. Phase 8 → model card and hand-off; feature 001 publishes what this feature decided.

### Parallel Team Strategy

- Agents: Phase 2 together (three tiny PRs), then Agent 2 → US1 code, Agent 1 → US2 code, Agent 3 → US3 code, all at once; then Agent 2 → T030 and later T055; Agent 3 → Phase 7 PRs only if needed.
- You: review/merge as PRs land; run US1 (grading) while agents finish US2/US3; seed review (T036) while Agent 3's PR is in review; then the GPU/grading chain of US4.

---

## Notes

- Every `(You)` run task ends with a direct commit of outputs on the integration branch and a status update here — same bookkeeping habit as 001.
- Effort reminders from spec.md: blind grades ≈ 264 for existing runs (T024, T026) + 88 per candidate file (T050, T054); seed review 1–2 h (T036); training ≈ 10–15 min per run (T046, T047, T054).
- The `-split` suffix in run ids applies only when `split` was selected in T025; drop it everywhere otherwise.
- Never edit `proposal.md` to match reality — it is the historical sketch; `adoption-decision.md` and this file are the record.
