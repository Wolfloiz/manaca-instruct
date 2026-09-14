# Phase 0 Research: Manacá-Instruct-PT (Core Lifecycle v1)

Resolves the technical unknowns surfaced by `plan.md`'s Technical Context. Builds on `.specify/assessments/manaca-instruct-pt/research.md` (assessment-stage research) rather than repeating it — this file is implementation-facing, not idea-viability-facing.

## 1. Dataset source licenses (blocks FR-002 / FR-009)

**Decision**: Treat both candidate dataset sources — `dominguesm/alpaca-data-pt-br` and `dominguesm/Canarim-Instruct-PTBR-Dataset` — as **CC BY-NC-4.0**, and set the published Manacá-Instruct-PT model's license to **CC BY-NC-4.0** accordingly.

**Rationale**: Both datasets are confirmed CC BY-NC-4.0 licensed. The Canarim dataset's README explicitly states this is because portions derive from or are influenced by OpenAI model outputs (Self-Instruct/Alpaca-style generation), and OpenAI's usage policy restricts using its model outputs to train competing models commercially. This matches the precedent already observed in the official `menezesbruno/manaca-1b-instruct` release, which also landed on CC BY-NC-4.0 for the same underlying reason (its SFT mix included Alpaca-PT). There is no remaining ambiguity here — spec.md's FR-009 "assumed CC BY-NC-4.0 unless verified otherwise" is now confirmed, not just assumed, for both candidate sources named in FR-002.

**Alternatives considered**:
- *Use only a permissively-licensed dataset to enable a fully open (CC BY or Apache 2.0) release* — rejected for this feature: no permissively-licensed PT-BR instruction dataset covering all five task categories at the needed scale was identified in assessment research; sourcing/generating one from scratch would violate FR-002's "not authored entirely from scratch" requirement and blow the medium appetite budget agreed in `concept.md`. Left as a possible future iteration, not this feature.
- *Ignore the license and publish under CC BY-NC-4.0's stricter cousin or an ambiguous "research only" label* — rejected: FR-009 requires the model card to state the license correctly; CC BY-NC-4.0 is a standard, well-understood license and is what the precedent-setting official release already uses.

## 2. QLoRA hyperparameter starting configuration (blocks train_qlora.py design)

**Decision**: Start from the ranges already specified by the author's own project document (`manaca-local-projeto.md` §16): 4-bit NF4 quantization, LoRA rank 8–16, LoRA alpha 16–32, dropout 0.05, batch size 1–2, gradient accumulation 8–32, learning rate 1e-4–2e-4, 1–3 epochs — with the single iteration round budgeted by FR-005 used to adjust within these ranges if the first pass misses the FR-004 thresholds, not to explore a wider search space.

**Rationale**: This range is independently corroborated by a controlled profiling study fine-tuning a similarly-sized model (Qwen2.5-1.5B-Instruct, LoRA/QLoRA) on an 8GB-VRAM consumer GPU (RTX 4060), which found batch sizes up to 2 and sequence lengths up to 2048 tokens feasible with a comparable configuration — cited in `.specify/assessments/manaca-instruct-pt/research.md`. No new hyperparameter search is warranted before the first training run; starting from a validated range keeps the appetite on the "medium" side agreed in `concept.md`, rather than opening a large hyperparameter-tuning rabbit hole flagged as a risk there.

**Alternatives considered**:
- *Full hyperparameter sweep before the first run* — rejected: `concept.md`'s Option B explicitly caps iteration at one round to avoid an open-ended tuning loop; a sweep belongs to a future iteration if the single planned round is insufficient.
- *Full fine-tuning instead of LoRA/QLoRA* — rejected: exceeds the 8GB VRAM budget on the RTX 5050 (per `manaca-local-projeto.md` §4's own math on activation/optimizer memory) and was never in scope per the "go" decision's handoff (Concept Option B is explicitly QLoRA-based).

## 3. Rule-based grading approach for grammar correction & classification (blocks src/grading/rule_based.py, FR-004)

**Decision**: Grammar correction is scored by normalized edit distance (Python stdlib `difflib.SequenceMatcher` ratio, or `rapidfuzz` if `difflib`'s performance is inadequate at ~1,000+ eval comparisons) between the model's output and the expected corrected sentence, with a similarity threshold (e.g. ≥0.9) counted as a pass. Classification is scored by exact string match (case-insensitive, whitespace-normalized) between the model's output label and the expected label from a fixed label set (e.g. "reclamação", "dúvida", "elogio", "solicitação", per `manaca-local-projeto.md` §8.5's example categories).

**Rationale**: These two categories have a well-defined "correct answer" (a specific corrected sentence; a specific label from a small fixed set), which is exactly the condition the Question 1 clarification (`spec.md`'s Clarifications section) specified for rule-based scoring. Edit-distance for grammar correction tolerates minor acceptable variation (e.g. optional Oxford-comma-equivalent punctuation differences) without requiring exact string equality, which would be too brittle. Exact match is appropriate for classification since the label set is small and closed.

**Alternatives considered**:
- *Exact match for grammar correction too* — rejected: a corrected sentence can have more than one acceptable surface form (e.g. two ways to fix subject-verb agreement); exact match would produce false negatives and undermine the 70% threshold's meaningfulness.
- *LLM-as-judge for these two categories as well* — rejected by the Question 1 clarification answer (option D), which explicitly reserved rule-based scoring for exactly these two categories and manual review for the rest; introducing a third grading mechanism here would also add a new model dependency not otherwise needed by this feature.

## 4. GGUF conversion & quantization tooling (blocks src/quantize.py, FR-006)

**Decision**: Use llama.cpp's `convert_hf_to_gguf.py` to convert the merged (adapter-merged, standalone) model to an F16 GGUF file, then `llama-quantize` to produce the Q4_K_M artifact plus one additional comparison level (Q5_K_M, chosen as the standard "one step up" comparison point per common practice). Do **not** attempt to convert or quantize the LoRA adapter directly, and do not attempt Q4_K_S or lower on a QLoRA-derived model without first validating output quality — a real, documented limitation surfaced during research where GGUF quantization below a certain aggressiveness has produced degraded results specifically for QLoRA-trained (as opposed to fully-fine-tuned) models.

**Rationale**: This is the standard, well-documented llama.cpp workflow (merge → F16 GGUF → quantize), and matches FR-006's requirement for "at least Q4_K_M plus one additional comparison level." Flagging the QLoRA-specific quantization-quality risk here means it surfaces in tasks/testing rather than being discovered mid-benchmark on the Dell G3.

**Alternatives considered**:
- *Quantize directly from the LoRA adapter without merging first* — rejected: FR-006 explicitly requires merging before quantization, and llama.cpp's GGUF tooling operates on standalone model weights, not adapters.
- *Skip the F16 intermediate and quantize directly from the safetensors checkpoint* — rejected: the standard llama.cpp path requires the F16 GGUF conversion step first; skipping it is not a supported shortcut.

## 5. Evaluation results storage format (blocks src/evaluate.py, eval/results/)

**Decision**: One JSONL file per evaluation run, one line per (prompt, model) pair, following the shape already sketched by the author's own project document (`manaca-local-projeto.md` §31): `{"id", "task", "model", "prompt", "expected" (if applicable), "output", "score", "grading_method"}`, where `model` is one of `manaca-1b-base`, `manaca-instruct-pt`, or `manaca-1b-instruct` (the official release) and `grading_method` is `rule_based` or `manual_review`.

**Rationale**: Reuses a format the author already designed, extended minimally to carry the `grading_method` field needed by the Question 1 clarification's hybrid approach and the three-way (`SC-008`) comparison. JSONL keeps each run appendable and diffable, and is trivial to load with `datasets` or plain Python for the model-card comparison tables.

**Alternatives considered**: CSV — rejected because `expected`/`output` text fields routinely contain commas and newlines, making CSV escaping more error-prone than JSONL for this data.

## 6. Publishing mechanism (blocks src/publish.py, FR-009/FR-010)

**Decision**: Use the `huggingface_hub` Python library (`create_repo` + `upload_folder`/`upload_file`) to push the merged model, GGUF artifacts, and model card (`README.md` with YAML front matter for license/tags) to a new Hugging Face model repository, authenticated via a personal access token supplied through environment variable or `huggingface-cli login` — not committed to the repository.

**Rationale**: This is the standard, documented way to publish a model to the Hub, satisfies FR-010's "no undocumented steps" requirement (the model card documents standard `from_pretrained`/`AutoModelForCausalLM` or GGUF/llama.cpp loading, not a bespoke process), and requires no new infrastructure beyond a Hugging Face account the author already has (implied by the public-release goal in `problem.md`).

**Alternatives considered**: Manual upload via the Hugging Face web UI — rejected as the primary path since it isn't scriptable/reproducible (undermines `problem.md`'s "reproducible pipeline" goal), though it remains a viable fallback if `huggingface_hub` upload hits an issue.
