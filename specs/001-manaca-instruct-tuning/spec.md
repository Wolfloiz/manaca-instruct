# Feature Specification: Manacá-Instruct-PT (Core Lifecycle v1)

**Feature Branch**: `001-manaca-instruct-tuning`

**Created**: 2026-09-14

**Status**: Draft

**Input**: User description: "Go decision handoff from `.specify/assessments/manaca-instruct-pt/decision.md` (Concept Option B — Core Lifecycle v1): build an instruction-tuned PT-BR model ('Manacá-Instruct-PT') from the Manacá-1B base model — dataset adaptation, QLoRA fine-tuning, Base-vs-Instruct and forgetting evaluation, GGUF quantization, cross-hardware benchmarking on the RTX 5050 and Dell G3, and a public Hugging Face release — excluding any API, UI, or RAG layer."

## Clarifications

### Session 2026-09-14

- Q: How should each evaluation prompt be scored as a "pass" or "fail" toward the 70% per-category threshold and 10% forgetting-drop threshold? → A: Hybrid — rule/heuristic-based scoring for grammar correction and classification (clear expected answers), manual human review for rewriting, summarization, and simplification (open-ended, many valid outputs).
- Q: After filtering the existing-dataset blend down to the five task categories, roughly how many training examples should the final fine-tuning dataset contain? → A: 3,000–5,000 examples, roughly evenly split across the five categories.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Establish the base model baseline (Priority: P1)

As the project author, I run the untouched Manacá-1B-base model against a fixed set of Brazilian Portuguese prompts covering the five target task categories (grammar correction, rewriting, summarization, simplification, classification) and record exactly how it behaves, so that I have a documented reference point to measure any later fine-tuning against.

**Why this priority**: Nothing else in the project is verifiable without this. It's also the fastest way to de-risk the biggest unproven assumption — that the training tooling, tokenizer, and hardware actually work together — before any time is spent on dataset work or training.

**Independent Test**: Can be fully tested by loading the base model, running it against the fixed evaluation prompt set, and recording outputs, latency, and resource usage — this delivers a usable, documented baseline on its own, even if fine-tuning work is delayed or paused afterward.

**Acceptance Scenarios**:

1. **Given** the base model downloaded and the environment set up, **When** the fixed evaluation prompt set is run against it, **Then** outputs, latency, and resource usage (VRAM, load time) are recorded for every prompt in all five task categories.
2. **Given** an instruction-style prompt (e.g. "Corrija o texto: ..."), **When** it is run against the base model, **Then** the recorded output confirms the base model does not reliably follow the instruction — establishing the problem the rest of the project addresses.

---

### User Story 2 - Produce and validate an instruction-following model (Priority: P1)

As the project author, I fine-tune the base model into an instruction-following model ("Manacá-Instruct-PT") and confirm it follows Brazilian Portuguese instructions across the five task categories measurably better than the base model, without losing the base model's core language ability.

**Why this priority**: This is the core value of the entire project — both the hands-on learning objective and the "genuinely usable model" objective depend entirely on this working. Nothing downstream (quantization, deployment, publication) is worth doing if this fails.

**Independent Test**: Can be tested by running the same fixed evaluation prompts through both the base model and the fine-tuned model and comparing the results — this delivers a working, evaluated model on its own, independent of later quantization, hardware benchmarking, or publication.

**Acceptance Scenarios**:

1. **Given** the same fixed evaluation prompt, **When** it is run against Manacá-Instruct-PT and against Manacá-1B-base, **Then** the instruct model's output correctly follows the instruction more often than the base model's, per the recorded scoring.
2. **Given** a set of general Brazilian Portuguese language prompts unrelated to the five task categories, **When** they are run against Manacá-Instruct-PT and manually reviewed against the base model's outputs on the same prompts, **Then** the recorded relative drop in performance is no more than 10%.
3. **Given** the same fixed evaluation prompt, **When** it is run against Manacá-Instruct-PT and against the officially released `menezesbruno/manaca-1b-instruct` model, **Then** results are recorded side-by-side so the author can report honestly how Manacá-Instruct-PT compares to the official instruction-tuned release, regardless of which one scores higher.

---

### User Story 3 - Run reliably on both target machines (Priority: P2)

As the project author, I quantize the fine-tuned model and confirm it runs reliably, without stalling, at an acceptable generation speed on both my primary development machine and the older secondary machine, so I know the result is genuinely usable outside of a single environment.

**Why this priority**: "Genuinely usable" was explicitly defined by the author as reliable, stall-free generation at approximately 70 tokens/second. The project must prove this on real hardware rather than assume it — this is also the step most likely to reveal that the older machine is a hard constraint.

**Independent Test**: Can be tested by loading the quantized model on each machine independently and measuring generation throughput, stability, and resource usage against a repeated set of prompts — this delivers verified deployment evidence on its own, independent of whether the model has been published yet.

**Acceptance Scenarios**:

1. **Given** the quantized model loaded on the primary development machine, **When** generating a response to a typical instruction prompt, **Then** generation completes without stalling or crashing.
2. **Given** the quantized model loaded on the secondary deployment machine, **When** generating a response to the same prompt, **Then** it also loads and completes generation successfully, so the model is not tied to a single machine (even if measured throughput differs between the two).

---

### User Story 4 - Publish the model for public use (Priority: P3)

As a Hugging Face user looking for a Brazilian Portuguese instruction-following model, I can find, download, and successfully run Manacá-Instruct-PT, with clear documentation of what it is, how it was built, how to use it, and its known limitations.

**Why this priority**: This fulfills the author's confirmed goal of publishing the result for others, turning the private learning exercise into a usable public artifact. It comes after the model actually works (Stories 1–3) since publishing an unverified model would be irresponsible.

**Independent Test**: Can be tested by having someone unfamiliar with the project download the published model from Hugging Face and follow only the model card's instructions to generate a response, without needing to contact the author.

**Acceptance Scenarios**:

1. **Given** the published Hugging Face repository, **When** a new visitor reads the model card, **Then** they can determine what the model does, what it was built from (Manacá-1B-base, CC BY 4.0 attribution), that it is a personal/learning project, which five tasks it supports, and its known limitations — without needing any context outside the page.
2. **Given** a downloaded copy of the published model, **When** a user follows the documented usage instructions, **Then** they can generate a response to an instruction prompt without any additional undocumented steps.

---

### Edge Cases

- What happens when the fine-tuned model produces a nonsensical or incoherent output on a prompt it should handle well (a quality regression)? The evaluation step must catch this before publication, not after.
- How does the project handle a forgetting result where Manacá-Instruct-PT clearly loses general-language ability compared to the base model? A single iteration round (revised dataset mix and/or hyperparameters, followed by a full re-run of the same evaluation) is budgeted for this; if forgetting persists after that round, it must be documented as a known limitation in the model card rather than hidden or endlessly re-attempted.
- What happens if the quantized model cannot reach the ~70 tokens/second target on the older deployment machine due to its 4GB VRAM limit? This must be recorded as an honest, measured result (not assumed away), and the model card's usability claims must reflect what was actually measured on each machine.
- What happens if the chosen existing instruction dataset's license terms are unclear or incompatible with redistributing a model fine-tuned on it? This must be checked and resolved before the dataset is adapted, not discovered after training.
- What happens if evaluation shows improvement on some of the five task categories but not others? This must be reported per-category in the model card's limitations, not summarized away as an overall pass.
- What happens if the officially released `menezesbruno/manaca-1b-instruct` model outperforms Manacá-Instruct-PT on the same evaluation prompts? This must be reported honestly in the model card's comparison section — this feature's success criteria do not depend on beating the official release, only on completing and documenting the comparison.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST establish a documented baseline by running the untouched Manacá-1B-base model against a fixed set of Brazilian Portuguese evaluation prompts covering all five task categories (grammar correction, rewriting, summarization, simplification, classification), recording outputs, latency, and resource usage, before any fine-tuning occurs.
- **FR-002**: The project MUST fine-tune Manacá-1B-base into an instruction-following model ("Manacá-Instruct-PT") using an instruction dataset built as a blend of existing published Brazilian Portuguese instruction sources (drawing on candidates such as the translated Alpaca dataset and the Canarim Instruct Dataset), filtered down to the five target task categories and curated to a final size of approximately 3,000–5,000 examples, roughly evenly split across the five categories — rather than a dataset authored entirely from scratch or used unfiltered at full source size.
- **FR-003**: The project MUST evaluate the fine-tuned model against the same fixed prompt set used for the baseline (new-capability check across all five task categories) and MUST separately evaluate it against a set of general Brazilian Portuguese language prompts unrelated to those five categories, to check for loss of the base model's original capabilities (forgetting check).
- **FR-004**: The evaluation MUST apply a numeric pass/fail threshold per task category: Manacá-Instruct-PT must reach at least a 70% task-level pass rate on the fixed evaluation prompts for each of the five task categories, measured against Manacá-1B-base's pass rate on the same prompts, and must show no more than a 10% relative drop in performance on the forgetting-check prompts compared to the base model. Pass/fail scoring MUST use rule/heuristic-based grading (e.g. exact or fuzzy match against an expected answer) for the grammar correction and classification categories, and manual human review against a simple correct/partial/incorrect rubric for the rewriting, summarization, and simplification categories and for the forgetting-check prompts. The evaluation MUST additionally run the same fixed evaluation prompts against the officially released `menezesbruno/manaca-1b-instruct` model (an experimental v0.1 release found by the author on 2026-09-14, after this project began) as a third comparison point, so results can be reported honestly relative to both the untuned base model and the official instruction-tuned release — this comparison is informational and does not gate completion (per the Edge Cases section).
- **FR-005**: If evaluation reveals a quality problem (weak instruction-following or significant forgetting) in any task category, the project MUST allow for at most one iteration round — a revised dataset mix and/or training configuration, followed by a full re-run of the same evaluation — before the result is either accepted or documented as a known limitation.
- **FR-006**: The project MUST merge the trained adapter into a standalone fine-tuned model and quantize it, producing at least the Q4_K_M quantization level plus one additional comparison level, so that quality-versus-size trade-offs are documented rather than assumed.
- **FR-007**: The project MUST measure and record generation throughput (tokens per second), load time, and memory/VRAM usage of the quantized model separately on the primary development machine (RTX 5050, 8GB VRAM) and the secondary deployment machine (Dell G3, GTX 1050, 4GB VRAM, 32GB system RAM).
- **FR-008**: The quantized model MUST generate responses reliably — without stalling or crashing — at approximately 70 tokens per second under conditions typical of a general Hugging Face downloader running a reasonably modern GPU, independent of the author's own two specific machines. The author's RTX 5050 and Dell G3 results (FR-007) are measured and reported separately, as real data points, not as the basis for whether this bar is considered met.
- **FR-009**: The project MUST publish the finished model publicly on Hugging Face, accompanied by a model card that: discloses the model as a personal/learning project (for this initial release); documents the base model and determines the correct license for the fine-tuned model based on the datasets actually used in FR-002 (the officially released `menezesbruno/manaca-1b-instruct` used CC BY-NC 4.0 because its training mix included non-commercial sources such as Alpaca-PT — Manacá-Instruct-PT MUST be assumed to require the same CC BY-NC 4.0 license unless the final dataset blend is verified to use only permissively-licensed sources); describes the intended use and the five supported task categories; and states known limitations, including any forgetting or per-category weaknesses found during evaluation, the base model's documented reasoning limitations, and an honest comparison to the official `menezesbruno/manaca-1b-instruct` release (per FR-004).
- **FR-010**: The project MUST enable any person who downloads the published model to generate an instruction-following response using only the documentation provided in the model card, without contacting the author.
- **FR-011**: The project MUST perform a lightweight, non-blocking check of the official Manacá project's public channels (GitHub, Hugging Face, team announcements) for signs of an official instruction-tuned release. This check already surfaced one during specification — `menezesbruno/manaca-1b-instruct`, an experimental v0.1 release found 2026-09-14 — which does not block this feature but is now folded into evaluation as a required comparison point (FR-004), not merely tracked informationally.

### Key Entities *(include if feature involves data)*

- **Manacá-1B-base**: The pretrained Brazilian Portuguese base language model this project starts from. Treated as a fixed, unmodified input (CC BY 4.0 licensed); never edited directly, only used to derive fine-tuned artifacts.
- **Instruction Dataset**: The curated/adapted set of Brazilian Portuguese instruction-input-output examples, drawn from existing published sources, covering the five target task categories, used to fine-tune the base model. Distinct from the evaluation prompt set — no overlap between the two.
- **Fixed Evaluation Prompt Set**: A stable set of Brazilian Portuguese prompts, split into a new-capability group (the five task categories) and a forgetting-check group (general language ability), used to measure Base-vs-Instruct-vs-Official performance (see below). Never used for training.
- **`menezesbruno/manaca-1b-instruct`**: The officially released instruction-tuned Manacá model (experimental v0.1, found 2026-09-14), used as a third comparison point in evaluation alongside the base model and Manacá-Instruct-PT. Not used for training or as a source of training data — comparison only.
- **Manacá-Instruct-PT (adapter and merged model)**: The fine-tuned artifact, produced first as a trainable adapter and then merged into a standalone model ready for quantization.
- **Quantized Model**: The compressed deployment artifact (at least two quantization levels) derived from the merged model, used for cross-hardware benchmarking and public release.
- **Hugging Face Model Card**: The public-facing documentation artifact published alongside the model, covering intended use, base model attribution, license, supported tasks, and known limitations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A documented baseline exists, showing the untouched base model's recorded behavior on all five task categories, before any training occurs.
- **SC-002**: Manacá-Instruct-PT reaches at least a 70% task-level pass rate on the fixed evaluation set in every one of the five task categories, compared against Manacá-1B-base's pass rate on the same prompts (or the shortfall is explicitly documented as a known limitation for that category).
- **SC-003**: Manacá-Instruct-PT's performance on the forgetting-check prompts shows no more than a 10% relative drop compared to the base model's performance on the same prompts.
- **SC-004**: The quantized model loads and completes a full, coherent generation without stalling or crashing, verified independently on both the development machine and the deployment machine.
- **SC-005**: The quantized model reaches approximately 70 tokens per second under conditions typical of a general Hugging Face downloader on a reasonably modern GPU — an independently reproducible, measured result, not an estimate — while the author's own RTX 5050 and Dell G3 numbers are recorded and reported separately regardless of whether they individually clear that bar.
- **SC-006**: A person unfamiliar with the project can download the published Hugging Face model and successfully generate a response to an instruction prompt using only the model card's documentation, with no additional undocumented steps.
- **SC-007**: Every pipeline stage — baseline, dataset preparation, fine-tuning, evaluation, merge, quantization, cross-hardware benchmarking, and publication — has been executed and documented at least once, regardless of final model quality (the lifecycle-completeness signal for the author's learning goal).
- **SC-008**: The fixed evaluation results include a documented three-way comparison — Manacá-1B-base, Manacá-Instruct-PT, and the official `menezesbruno/manaca-1b-instruct` release — for every task category, published transparently in the model card regardless of which model scores highest.

## Assumptions

- Existing published Brazilian Portuguese instruction datasets identified during research (translated Alpaca-style data, the Canarim Instruct Dataset) are assumed usable as a starting point for the blend in FR-002; their specific licenses must still be checked for compatibility with redistributing a model fine-tuned on them, before the dataset is finalized.
- The check of the official Manacá team's channels (FR-011) already found `menezesbruno/manaca-1b-instruct` (experimental v0.1) during specification, confirming this risk is real rather than hypothetical. This spec's response is to fold it into evaluation as a comparison point (FR-004, SC-008) rather than change scope — the project continues as Concept Option B; changing scope further in response to future official releases is a future decision, out of scope for this feature.
- Manacá-Instruct-PT is assumed to require a CC BY-NC 4.0 license (matching the official release's precedent) because the dataset blend in FR-002 is expected to include similarly-sourced non-commercial data; this must be confirmed, not assumed, before publication (FR-009).
- Any API, web/CLI interface, RAG/document-Q&A layer, or multiple task-specialized adapters are out of scope for this feature (per the confirmed "go" decision's handoff); they may be specified as separate, later features.
- The Dell G3's GTX 1050 has 4GB VRAM and the machine has 32GB of system RAM (confirmed by the author), assumed sufficient to run a Q4_K_M-quantized ~1.7B-parameter model, with or without partial GPU offload.
- Disclosing the model as a "personal/learning project" in the model card is sufficient transparency for this initial public release; this framing may be revisited in a future iteration if the project matures.
- One iteration round (a revised dataset mix and/or training configuration, followed by a full evaluation re-run) is budgeted if the first training pass does not meet the quality bar; further iteration beyond that round is out of scope for this feature.
- The fixed evaluation prompt set is assumed to total approximately 50–100 prompts (per the author's own original planning in manaca-local-projeto.md §37), split into roughly 15–20 prompts per task category for the new-capability group and roughly 20–30 prompts for the forgetting-check group — enough for the 70%/10% thresholds (FR-004) to be meaningful without making manual review of the open-ended categories impractical.
