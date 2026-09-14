---

description: "Task list for Manacá-Instruct-PT (Core Lifecycle v1), organized for 3 coding agents + the author, controlled entirely through GitHub (worktrees, branches, PRs, code review)"
---

# Tasks: Manacá-Instruct-PT (Core Lifecycle v1)

**Input**: Design documents from `/specs/001-manaca-instruct-tuning/` (plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md)

**Tests**: Not requested as TDD; the two schema-conformance checks below exist because three independent contributors produce files that must interoperate through the shared contracts in `contracts/` — not general test coverage.

**Organization**: Tasks are grouped by user story (spec.md priorities P1/P1/P2/P3), and every task also carries an **owner** tag — `(Agent 1)`, `(Agent 2)`, `(Agent 3)`, or `(You)` — reflecting the real constraint already identified in `.specify/assessments/manaca-instruct-pt/roadmap-execucao.md` (echoed in `manaca-local-projeto.md`): agents can parallelize *artifact creation* (scripts, prompts, filters, docs), but GPU training, physical Dell G3 access, dataset-quality judgment, and the final public-publish action are inherently sequential and stay with the author.

## Repo state today

**Updated 2026-09-14 during `/speckit-implement`**: Phase 1 is done. Repo live at `https://github.com/Wolfloiz/manaca-instruct` (private), `main` pushed, integration branch `001-manaca-instruct-tuning` pushed, all 3 agent worktrees created. Branch protection (T003) could **not** be enabled — GitHub blocks branch-protection rules on private repos without GitHub Pro (403: "Upgrade to GitHub Pro or make this repository public"). The PR-only workflow below is now enforced by convention, not by a server-side gate; if that matters, either upgrade the plan or make the repo public later (`gh repo edit --visibility public`) and re-run T003's command. Also note: agent branch names changed from the original `001-manaca-instruct-tuning/agentN-...` to `agents/agentN-...` — git rejects a branch name that is a path-prefix of another existing branch name (`001-manaca-instruct-tuning` already exists as the integration branch), so the nested form was never actually creatable.

## Team & Branch Assignments

| Owner | Role (per the author's own roadmap-execucao.md split) | Worktree | Branch |
|---|---|---|---|
| **You** | Environment/CUDA setup, all GPU training runs, physical Dell G3 benchmarking, dataset-quality review, hyperparameter decisions, PR review/merge, the final publish action | main checkout (repo root) | `001-manaca-instruct-tuning` (integration branch) |
| **Agent 1** | Dataset: grammar-correction + rewriting sourcing/filtering; `prepare_dataset.py` orchestration | `../manaca-instruct-agent1-dataset` | `agents/agent1-dataset` |
| **Agent 2** | Dataset: simplification/summarization/classification sourcing/filtering; the fixed evaluation prompt set; the grading/evaluation harness; the model-card comparison tables | `../manaca-instruct-agent2-eval` | `agents/agent2-eval` |
| **Agent 3** | Infrastructure: repo scaffolding, `train_qlora.py`, `merge_adapter.py`, `quantize.py`, `benchmark.py`, `publish.py` | `../manaca-instruct-agent3-infra` | `agents/agent3-infra` |

## GitHub workflow (applies to every task below)

1. **Trunk**: `main` — direct pushes to it are avoided by convention (T003 found that server-side branch protection isn't available on this GitHub plan for a private repo; see "Repo state today" above). Still merge only via a reviewed PR, same as if the gate were enforced.
2. **Integration branch**: `001-manaca-instruct-tuning`, created off `main` (T004). All three agents' branches open PRs **into this branch**, not `main`. You merge `001-manaca-instruct-tuning` → `main` once (T059), after every user story phase is done.
3. **Per-agent branch**: each agent works only inside their own worktree, on their own branch, and never pushes directly to `001-manaca-instruct-tuning` or `main` — every change is a PR.
4. **Code review**: before merging any agent's PR, run `/code-review` (or `/code-review high` for the training/quantization scripts, since correctness there is harder to eyeball) on the diff, then `gh pr review --approve` and `gh pr merge`. You are the sole human reviewer — there is no second person, so the automated review pass is not optional, it's the substitute for a second pair of eyes.
5. **Commit granularity**: one PR per numbered task group below (grouped explicitly where a PR task exists); don't batch unrelated tasks into one PR.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Turn this directory into a GitHub-controlled repo with the worktrees the 3 agents will work in.

- [X] T001 (You) Run `git init`, `git add -A`, and commit the existing `specs/`, `.specify/`, and project docs (`manaca-local-projeto.md`, `roadmap-execucao.md`) as the initial commit on `main`
- [X] T002 (You) Run `gh repo create manaca-instruct --private --source=. --remote=origin --push` to create the GitHub repository and push `main` (rename/make public later with `gh repo rename` / `gh repo edit --visibility public` if desired — private is the safer default while the repo holds work-in-progress)
- [X] T003 (You) ~~Configure branch protection on `main`~~ — **blocked**: not available for private repos on the current GitHub plan (see "Repo state today" above). Falling back to convention-enforced PRs.
- [X] T004 (You) Create and push the integration branch: `git checkout -b 001-manaca-instruct-tuning && git push -u origin 001-manaca-instruct-tuning`
- [X] T005 [P] (You) Create Agent 1's worktree: `git worktree add ../manaca-instruct-agent1-dataset -b agents/agent1-dataset 001-manaca-instruct-tuning`
- [X] T006 [P] (You) Create Agent 2's worktree: `git worktree add ../manaca-instruct-agent2-eval -b agents/agent2-eval 001-manaca-instruct-tuning`
- [X] T007 [P] (You) Create Agent 3's worktree: `git worktree add ../manaca-instruct-agent3-infra -b agents/agent3-infra 001-manaca-instruct-tuning`

**Checkpoint**: Repo exists on GitHub (main pushed, protection unavailable on this plan — see above), the integration branch exists, and all 3 agent worktrees are ready to be handed to agents.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared scaffolding every user story needs. No story work starts before this merges.

**⚠️ CRITICAL**: Blocks Phase 3 onward.

- [X] T008 (Agent 3, in `../manaca-instruct-agent3-infra`) Create `requirements.txt` (or `pyproject.toml`) pinning `torch` (CUDA build), `transformers`, `peft`, `trl`, `bitsandbytes`, `datasets`, `huggingface_hub`, `pytest`, per plan.md's Primary Dependencies
- [X] T009 [P] (Agent 3) Scaffold the directory tree from plan.md's Project Structure: `configs/`, `data/raw/`, `data/processed/`, `data/eval/`, `adapters/`, `models/merged/`, `models/gguf/`, `eval/results/`, `benchmarks/`, `tests/unit/`, `tests/contract/` (each with a `.gitkeep` so empty dirs are tracked)
- [X] T010 [P] (Agent 3) Create `configs/train.yaml` with the QLoRA starting configuration from research.md §2: 4-bit NF4 quantization, LoRA rank 8–16, LoRA alpha 16–32, dropout 0.05, batch size 1–2, gradient accumulation 8–32, learning rate 1e-4–2e-4, 1–3 epochs
- [X] T011 [P] (Agent 3) Create `configs/inference.yaml` with generation defaults (temperature, top_p, max_new_tokens) for evaluation/benchmarking runs
- [X] T012 [US-shared] (Agent 2, in `../manaca-instruct-agent2-eval`) Implement the schema-conformance checks in `tests/contract/test_dataset_schema.py` and `tests/contract/test_evaluation_results_schema.py`, validating files against `contracts/dataset-schema.md` and `contracts/evaluation-results-schema.md` respectively — these are what let 3 independently-reviewed PRs interoperate safely (12/12 tests passing)
- [X] T013 (Agent 3) Open PR #1 (`agent3-infra` → `001-manaca-instruct-tuning`) with T008–T011 — [PR #1](https://github.com/Wolfloiz/manaca-instruct/pull/1), merged
- [X] T014 (Agent 2) Open PR #2 (`agent2-eval` → `001-manaca-instruct-tuning`) with T012 — [PR #2](https://github.com/Wolfloiz/manaca-instruct/pull/2), merged
- [ ] T015 (You) Set up CUDA/WSL2/PyTorch on the RTX 5050 machine per `manaca-local-projeto.md` §10; verify `torch.cuda.is_available()` returns `True` — **not done**: out of scope for this implementation pass (installing the full CUDA torch build is a large download reserved for when you're ready to actually train); `requirements.txt` is ready whenever you are
- [X] T016 (You) Code-review and merge PR #1 and PR #2 into `001-manaca-instruct-tuning` — `/code-review` caught a real documentation contradiction in this file (introduced while updating Phase 1's checkboxes), fixed before merge

**Checkpoint**: Foundation merged — Agents 1 and 2 can now start their story-phase work in parallel.

---

## Phase 3: User Story 1 - Establish the base model baseline (Priority: P1) 🎯 MVP

**Goal**: Run the untouched base model against a fixed, frozen evaluation prompt set and record the result (spec.md FR-001, SC-001).

**Independent Test**: `eval/results/baseline.jsonl` exists with one row per prompt across all five categories, and at least one row demonstrates the base model failing to follow an instruction.

- [ ] T017 [P] [US1] (Agent 2) Author `data/eval/grupo_a_prompts.jsonl` — 15–20 prompts per each of the 5 task categories (grammar_correction, rewriting, summarization, simplification, classification), one `EvaluationPrompt` JSON object per line per `contracts/dataset-schema.md`; `grading_method` is `rule_based` for grammar_correction/classification (non-null `expected` required) and `manual_review` for the other three
- [ ] T018 [P] [US1] (Agent 2) Author `data/eval/grupo_b_prompts.jsonl` — 20–30 general Brazilian Portuguese prompts unrelated to the five categories, `task_category: null`, `grading_method: manual_review`, per `contracts/dataset-schema.md`
- [ ] T019 [P] [US1] (Agent 2) Implement `src/grading/rule_based.py`: edit-distance scoring (`difflib.SequenceMatcher` ratio ≥0.9 = pass) for `grammar_correction`, exact case/whitespace-insensitive match for `classification`, per research.md §3
- [ ] T020 [US1] (Agent 2) Implement `src/evaluate.py`: given `--model {manaca-1b-base|manaca-instruct-pt|manaca-1b-instruct}` (optionally `--adapter <path>`), `--prompts <files>`, `--run-id <id>`, `--out <file>`, generate a response per prompt and write one `EvaluationResult` line per `contracts/evaluation-results-schema.md` (`rule_based` rows scored immediately via T019, `manual_review` rows written with `score: null`) — depends on T017–T019
- [ ] T021 [US1] (Agent 2) Implement `src/grading/review_cli.py`: walks an `eval/results/*.jsonl` file, presents each `score: null` row for a 1/0.5/0 (correct/partial/incorrect) judgment, writes the score back in place — depends on T020
- [ ] T022 [US1] (Agent 2) Open PR #3 (`agent2-eval` → `001-manaca-instruct-tuning`) with T017–T021
- [ ] T023 [US1] (You) Code-review and merge PR #3
- [ ] T024 [US1] (You) Run `python src/evaluate.py --model manaca-1b-base --prompts data/eval/grupo_a_prompts.jsonl data/eval/grupo_b_prompts.jsonl --run-id baseline --out eval/results/baseline.jsonl` on the RTX 5050 — depends on T023
- [ ] T025 [US1] (You) Run `src/grading/review_cli.py` against `eval/results/baseline.jsonl` to grade every `manual_review` row; confirm at least one `grupo_a` prompt shows the base model not following the instruction (Acceptance Scenario 2)
- [ ] T026 [US1] (You) Commit `eval/results/baseline.jsonl` to `001-manaca-instruct-tuning` (direct commit is fine here — it's your own run output, not agent-authored code needing review)

**Checkpoint**: SC-001 satisfied — documented baseline exists. The `grupo_a`/`grupo_b` prompt files are now frozen (no further edits — spec.md's Assumptions).

---

## Phase 4: User Story 2 - Produce and validate an instruction-following model (Priority: P1)

**Goal**: Fine-tune Manacá-Instruct-PT and prove it beats the base model per-category while not forgetting general PT-BR ability, with the official `manaca-1b-instruct` release as a third comparison point (spec.md FR-002–FR-005, SC-002/SC-003/SC-008).

**Independent Test**: `eval/results/qlora-v1.jsonl` (or `qlora-v2.jsonl` after one iteration) shows ≥70% pass rate per category vs. baseline and ≤10% forgetting drop, or each shortfall is documented; `eval/results/official-instruct.jsonl` gives the third comparison point.

**⚠️ Cross-agent dependency**: T028 (Agent 1's `prepare_dataset.py`) needs T017/T018 (Agent 2's frozen eval prompt files, already merged after Phase 3) to perform the "no training/eval overlap" check from `data-model.md`. Since Phase 3 is complete before this phase starts, this is already satisfied — no extra coordination needed.

- [X] T027 [P] [US2] (Agent 1, in `../manaca-instruct-agent1-dataset`) Implement `src/dataset_filters/grammar_rewriting.py`: pull `dominguesm/alpaca-data-pt-br`, filter/curate to `grammar_correction` + `rewriting` examples matching the `InstructionExample` schema (data-model.md) — keyword-based classification; `load_raw_alpaca_pt_br()` is real but not invoked (no downloads in this pass); 4 tests passing
- [X] T028 [P] [US2] (Agent 2) Implement `src/dataset_filters/open_ended_tasks.py`: pull `dominguesm/Canarim-Instruct-PTBR-Dataset` (and `alpaca-data-pt-br` as needed), filter/curate to `simplification` + `summarization` + `classification` examples matching the `InstructionExample` schema — 4 tests passing
- [X] T029 [US2] (Agent 1) Implement `src/prepare_dataset.py`: orchestrates T027 + T028's filter modules, deduplicates against `data/eval/grupo_a_prompts.jsonl`/`grupo_b_prompts.jsonl` (no `(instruction, input)` overlap, per data-model.md), writes `data/train.jsonl` + `data/validation.jsonl` totaling **3,000–5,000** examples roughly evenly split across the 5 categories — depends on T027, T028; 5 tests passing on the pure orchestration logic
- [X] T030 [US2] (Agent 1) Open PR (`agent1-dataset` → `001-manaca-instruct-tuning`) with T027, T029 — [PR #5](https://github.com/Wolfloiz/manaca-instruct/pull/5), merged
- [X] T031 [US2] (Agent 2) Open PR (`agent2-eval` → `001-manaca-instruct-tuning`) with T028 — [PR #4](https://github.com/Wolfloiz/manaca-instruct/pull/4), merged first so T029 could import it (actual PR numbers ended up #4/#5, not #4/#5 as originally sketched — sequencing adapted to the real cross-agent dependency)
- [X] T032 [US2] (You) Code-review and merge PR #4 and PR #5
- [ ] T033 [US2] (You) Run `python src/prepare_dataset.py`; spot-check the resulting `train.jsonl`/`validation.jsonl` for Portuguese correctness and category balance; approve, or send specific examples back to Agent 1/2 for a follow-up fix commit — **not done**: requires a real dataset download, out of scope for this implementation pass
- [X] T034 [P] [US2] (Agent 3, in `../manaca-instruct-agent3-infra`) Implement `src/train_qlora.py`: QLoRA fine-tuning entrypoint — `menezesbruno/manaca-1b-base` + `configs/train.yaml` + `data/train.jsonl` → adapter checkpoint under `adapters/<run-id>/` — validates config against research.md §2's ranges and the dataset schema; `_build_model`/`_run_training` are documented seams (no GPU execution in this pass)
- [X] T035 [P] [US2] (Agent 3) Implement `src/merge_adapter.py`: merges a trained LoRA adapter into a standalone model under `models/merged/<run-id>/` — same seam pattern
- [X] T036 [US2] (Agent 3) Open PR (`agent3-infra` → `001-manaca-instruct-tuning`) with T034–T035 — [PR #6](https://github.com/Wolfloiz/manaca-instruct/pull/6), merged
- [X] T037 [US2] (You) Code-review and merge PR #6 — 50/50 tests passing at merge time
- [ ] T038 [US2] (You) Run `python src/train_qlora.py --config configs/train.yaml --dataset data/train.jsonl --run-id qlora-v1` on the RTX 5050 — depends on T033, T037
- [ ] T039 [US2] (You) Run `python src/evaluate.py --model manaca-instruct-pt --adapter adapters/qlora-v1 --prompts data/eval/grupo_a_prompts.jsonl data/eval/grupo_b_prompts.jsonl --run-id qlora-v1 --out eval/results/qlora-v1.jsonl`
- [ ] T040 [US2] (You) Run `python src/evaluate.py --model manaca-1b-instruct --prompts data/eval/grupo_a_prompts.jsonl data/eval/grupo_b_prompts.jsonl --run-id official-instruct --out eval/results/official-instruct.jsonl` (the official comparison model, FR-004)
- [ ] T041 [US2] (You) Run `src/grading/review_cli.py` against both `eval/results/qlora-v1.jsonl` and `eval/results/official-instruct.jsonl`
- [ ] T042 [US2] (You) Aggregate `eval/results/qlora-v1.jsonl` by `(model, task_category)`; confirm each of the 5 categories reaches ≥70% pass rate vs. baseline (SC-002) and the forgetting-check relative drop is ≤10% (SC-003) — or write up the shortfall as a known limitation per category
- [ ] T043 [US2] (You) **If T042 misses either threshold**: adjust `configs/train.yaml` within research.md §2's ranges and repeat T038–T042 once as `run-id qlora-v2` (FR-005's single budgeted iteration cap — do not repeat again after this)
- [ ] T044 [US2] (You) Commit the final `eval/results/qlora-v1.jsonl` (or `qlora-v2.jsonl`) and `eval/results/official-instruct.jsonl` to `001-manaca-instruct-tuning`

**Checkpoint**: Manacá-Instruct-PT exists and is evaluated three ways (base, instruct, official). SC-002/SC-003/SC-008 data is final.

---

## Phase 5: User Story 3 - Run reliably on both target machines (Priority: P2)

**Goal**: Quantize the model and prove it runs, without stalling, on both the RTX 5050 and the Dell G3 (spec.md FR-006–FR-008, SC-004/SC-005).

**Independent Test**: `benchmarks/rtx-5050.jsonl` and `benchmarks/dell-g3.jsonl` each contain a `BenchmarkRecord` with `stalled_or_crashed: false`.

- [ ] T045 [P] [US3] (Agent 3) Implement `src/quantize.py`: wraps llama.cpp's `convert_hf_to_gguf.py` (merged model → F16 GGUF) and `llama-quantize` (F16 → `Q4_K_M` and `Q5_K_M`) per research.md §4 — note the flagged risk there about aggressive quantization on QLoRA-derived models and validate output isn't degraded before proceeding
- [ ] T046 [P] [US3] (Agent 3) Implement `src/benchmark.py`: loads a given GGUF file on the current machine, runs a repeated prompt set, records `tokens_per_second`, `load_time_s`, `vram_mb`, `ram_mb`, `stalled_or_crashed` as a `BenchmarkRecord` (data-model.md) to a `--out` JSONL file, tagged with `--machine {rtx-5050|dell-g3}`
- [ ] T047 [US3] (Agent 3) Open PR #7 (`agent3-infra` → `001-manaca-instruct-tuning`) with T045–T046
- [ ] T048 [US3] (You) Code-review and merge PR #7
- [ ] T049 [US3] (You) Run `src/merge_adapter.py` + `src/quantize.py` on the final `qlora-v1`/`qlora-v2` adapter to produce `models/gguf/manaca-instruct-pt-Q4_K_M.gguf` and `-Q5_K_M.gguf` — depends on T044, T048
- [ ] T050 [US3] (You) Run `src/benchmark.py --machine rtx-5050` on the RTX 5050, writing `benchmarks/rtx-5050.jsonl`; confirm `stalled_or_crashed: false`
- [ ] T051 [US3] (You) Physically run `src/benchmark.py --machine dell-g3` on the Dell G3 (GTX 1050, 4GB VRAM), writing `benchmarks/dell-g3.jsonl`; confirm `stalled_or_crashed: false` and record the real tokens/sec honestly even if it comes in below the ~70 tok/s typical-downloader target (SC-005 applies to a typical modern GPU, not necessarily this machine — see spec.md's Edge Cases)
- [ ] T052 [US3] (You) Commit `models/gguf/*.gguf` (or Git LFS pointers, if the files are large — see note below) and `benchmarks/*.jsonl` to `001-manaca-instruct-tuning`

**Note on large files**: GGUF files can be 1GB+; if that's too large for a normal git push, run `git lfs install && git lfs track "*.gguf"` before T052, or skip committing the binary and instead record its SHA256 + where it's stored (it will be pushed to Hugging Face in Phase 6 regardless).

**Checkpoint**: SC-004 and SC-005 verified on real hardware.

---

## Phase 6: User Story 4 - Publish the model for public use (Priority: P3)

**Goal**: Publish Manacá-Instruct-PT to Hugging Face with a model card meeting the `contracts/model-usage-contract.md` gate (spec.md FR-009–FR-011, SC-006/SC-008).

**Independent Test**: Someone who has never seen this project can download the model and generate a response using only the model card.

- [ ] T053 [P] [US4] (Agent 3) Implement `src/publish.py`: pushes the merged model + GGUF files + model card via `huggingface_hub` (`create_repo` + `upload_folder`), **refusing to run** if the model card is missing its `license` front-matter, either usage snippet, or a populated evaluation section — per `contracts/model-usage-contract.md`'s pre-publish gate
- [ ] T054 [P] [US4] (Agent 2) Draft the model card `README.md` template (YAML front matter: `license: cc-by-nc-4.0`, `language: [pt]`, `base_model: menezesbruno/manaca-1b-base`) with all 6 required sections from `contracts/model-usage-contract.md`, including the SC-008 three-way comparison table generated from `eval/results/baseline.jsonl` + `eval/results/qlora-v1.jsonl` (or `v2`) + `eval/results/official-instruct.jsonl`
- [ ] T055 [US4] (Agent 3) Open PR #8 (`agent3-infra` → `001-manaca-instruct-tuning`) with T053
- [ ] T056 [US4] (Agent 2) Open PR #9 (`agent2-eval` → `001-manaca-instruct-tuning`) with T054
- [ ] T057 [US4] (You) Code-review and merge PR #8 and PR #9
- [ ] T058 [US4] (You) Run `src/publish.py` against your own Hugging Face token to push the repository — this is the one genuinely hard-to-reverse action in the whole feature (a public release), so treat it as a deliberate final sign-off, not a routine script run — depends on T044, T052, T057
- [ ] T059 [US4] (You) Verify Acceptance Scenario 2: have someone unfamiliar with the project follow only the published model card to generate a response, with no undocumented steps

**Checkpoint**: Manacá-Instruct-PT is public. SC-006 verified.

---

## Final Phase: Polish & Cross-Cutting Concerns

- [ ] T060 [P] (Agent 1) Write the repository root `README.md` summarizing the project and linking to `specs/001-manaca-instruct-tuning/` and the published Hugging Face model
- [ ] T061 (You) Run the full `quickstart.md` validation end-to-end as a final sign-off — this is also the SC-007 lifecycle-completeness check (every stage executed and documented at least once)
- [ ] T062 (You) Open and merge the final PR: `001-manaca-instruct-tuning` → `main`
- [ ] T063 (You) Tag the release (`git tag v1.0-manaca-instruct-pt && git push --tags`) and remove the 3 agent worktrees (`git worktree remove ../manaca-instruct-agent{1,2,3}-*`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately. Creates the repo agents will work in.
- **Foundational (Phase 2)**: Depends on Phase 1 (repo + worktrees must exist). BLOCKS Phase 3 onward.
- **US1 (Phase 3)**: Depends on Foundational. Produces the frozen eval prompt files US2 needs.
- **US2 (Phase 4)**: Depends on Foundational directly for dataset-filter work (T027/T028 could theoretically start alongside Phase 3), but `prepare_dataset.py` (T029) and everything after it depends on Phase 3's frozen prompt files (T017/T018) for the no-overlap check — so treat Phase 4 as starting after Phase 3's Checkpoint in practice, even though the dataset-filter tasks alone don't strictly require it.
- **US3 (Phase 5)**: Depends on US2's merged/evaluated adapter (T044) and its own infra PR (T047).
- **US4 (Phase 6)**: Depends on US2's final eval results (T044) and US3's GGUF artifacts (T052).
- **Polish (Final Phase)**: Depends on US4 complete.

### Owner Load Summary (rough, for scheduling)

- **Agent 1**: T027, T029 (Phase 4), T060 — dataset-filter + orchestration work, front-loaded in Phase 4.
- **Agent 2**: T012 (Phase 2), T017–T021 (Phase 3), T028 (Phase 4), T054 (Phase 6) — the heaviest single-agent load; consider having Agent 2 prioritize T017/T018 (the eval prompt files) first within Phase 3, since Phase 4 quietly depends on them.
- **Agent 3**: T008–T011 (Phase 2), T034–T035 (Phase 4), T045–T046 (Phase 5), T053 (Phase 6) — spread evenly across every phase; this agent is rarely idle.
- **You**: every execution/GPU/physical-hardware/review/publish task — irreducible by design (per `.specify/assessments/manaca-instruct-pt/research.md`: "mais agentes não encurtam uma rodada de fine-tuning").

### Parallel Opportunities

- T005–T007 (worktree creation) run in parallel.
- T009–T011 (Agent 3's scaffolding) run in parallel with each other and with T012 (Agent 2's schema tests).
- Within Phase 3: T017, T018, T019 run in parallel (different files, no dependency).
- Within Phase 4: T027 (Agent 1) and T028 (Agent 2) run in parallel; T034 and T035 (Agent 3) run in parallel with each other and with T027/T028.
- Within Phase 5: T045 and T046 (Agent 3) run in parallel.
- Within Phase 6: T053 (Agent 3) and T054 (Agent 2) run in parallel.

---

## Parallel Example: Phase 4 kickoff (once Phase 3's Checkpoint is reached)

```bash
# In ../manaca-instruct-agent1-dataset (Agent 1):
Task: "Implement src/dataset_filters/grammar_rewriting.py (T027)"

# In ../manaca-instruct-agent2-eval (Agent 2):
Task: "Implement src/dataset_filters/open_ended_tasks.py (T028)"

# In ../manaca-instruct-agent3-infra (Agent 3):
Task: "Implement src/train_qlora.py (T034)"
Task: "Implement src/merge_adapter.py (T035)"
```

All four run concurrently in their own worktrees; none touches a file another owns.

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1).
2. **STOP and VALIDATE**: `eval/results/baseline.jsonl` exists and documents the base model's instruction-following gap.
3. This alone is a legitimate checkpoint to pause at if time is short — it's the smallest slice that proves the tooling (env, dataset schema, eval harness, GitHub flow with 3 agents) actually works end-to-end before committing to a full training run.

### Incremental Delivery

1. Setup + Foundational → repo and scaffolding ready.
2. US1 → documented baseline (SC-001).
3. US2 → Manacá-Instruct-PT exists and is evaluated three ways (SC-002, SC-003, SC-008 data).
4. US3 → proven to run on both machines (SC-004, SC-005).
5. US4 → public on Hugging Face (SC-006).
6. Polish → README, full quickstart sign-off (SC-007), merge to `main`, tag.

### Parallel Team Strategy (as requested: 3 agents + you, GitHub-controlled)

1. You run Phase 1 solo (repo/worktree bootstrap — nothing here is parallelizable, it's fast).
2. Phase 2: Agent 3 scaffolds while Agent 2 writes the schema tests; you set up CUDA in parallel.
3. Phase 3: Agent 2 builds the eval harness solo (this phase has only one agent-owned track); you review and then run the baseline.
4. Phase 4: Agent 1 and Agent 2 build dataset filters in parallel; Agent 3 builds training infra in parallel with both; you review 3 PRs, then run the actual training/eval sequence yourself (unavoidably sequential — one GPU).
5. Phase 5: Agent 3 builds quantize/benchmark tooling solo; you review, then physically run both benchmarks.
6. Phase 6: Agent 3 and Agent 2 work in parallel (publish script vs. model card); you review both, then execute the one irreversible action (publish) yourself.
7. Polish: quick, mostly you.

---

## Notes

- `[P]` tasks touch different files and have no unmet dependency — safe to hand to different agents/worktrees simultaneously.
- `[US#]` maps a task to its user story for traceability back to spec.md.
- Every task not owned by "(You)" happens in an agent's own worktree, on its own branch, and reaches `001-manaca-instruct-tuning` only through a reviewed PR — never a direct push.
- GPU training, physical Dell G3 access, manual-review grading, dataset-quality approval, and the Hugging Face publish action are intentionally never delegated to an agent — they require either hardware access an agent doesn't have, or a judgment call spec.md explicitly reserved for the author (FR-005's iteration decision, the personal/learning disclosure, the final publish sign-off).
- Avoid: skipping code review "just this once" on an agent PR, committing large binaries without checking `git lfs` first, and letting `qlora-v2` (T043) happen more than once — that would violate FR-005's one-iteration cap.
