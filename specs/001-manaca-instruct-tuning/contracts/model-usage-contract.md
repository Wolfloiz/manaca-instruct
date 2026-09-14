# Contract: Published Model Usage (Hugging Face)

Governs what the Hugging Face model card (FR-009) promises a downloader, and what `src/publish.py` must therefore make true. This is the closest thing this feature has to a "public API" — satisfies FR-010 ("generate a response using only the model card's documentation, without contacting the author") and User Story 4's acceptance scenarios.

## What is published

- A model repository on Hugging Face Hub containing: the merged, fine-tuned model weights (safetensors); at least two GGUF quantization levels (`Q4_K_M` + one comparison level, per FR-006/research.md §4); a `README.md` model card with YAML front matter.

## Model card front matter (minimum required fields)

```yaml
license: cc-by-nc-4.0
language: [pt]
base_model: menezesbruno/manaca-1b-base
tags: [instruction-tuning, portuguese, gguf, qlora, personal-project]
```

## Model card body (minimum required sections, per FR-009)

1. **What this is** — one paragraph stating this is a personal/learning project (per the Clarifications-confirmed disclosure), built by fine-tuning `menezesbruno/manaca-1b-base`.
2. **Intended use** — the five supported task categories (grammar correction, rewriting, summarization, simplification, classification), in Brazilian Portuguese.
3. **How to use it** — a copy-pasteable code snippet for both loading paths this feature produces:
   - `transformers`/`AutoModelForCausalLM.from_pretrained(...)` for the merged safetensors model.
   - `llama.cpp`/GGUF loading (e.g. `llama-cli -m <file>.gguf -p "..."`) for the quantized artifacts.
4. **Evaluation results** — the SC-002/SC-003/SC-008 comparison tables: per-category pass rate for base vs. instruct vs. official-instruct, and the forgetting-check result, sourced directly from `eval/results/*.jsonl` (not hand-typed numbers that can drift from the underlying data).
5. **Known limitations** — any category that missed the 70% threshold or forgetting that exceeded 10% (per the Edge Cases in spec.md, reported honestly rather than omitted); the base model's documented weak reasoning performance (near-chance ARC-Challenge-PT, per `.specify/assessments/manaca-instruct-pt/research.md`); and the license's non-commercial restriction.
6. **License & attribution** — CC BY-NC-4.0, with attribution to `menezesbruno/manaca-1b-base` (CC BY 4.0) and a note on which datasets (Alpaca-PT-BR, Canarim) drove the NC restriction.

## Contract test

`src/publish.py` MUST refuse to push (fail before calling `huggingface_hub.upload_*`) if any of the following are missing at publish time: the front-matter `license` field, at least one worked code example per loading path, or a populated evaluation-results section sourced from an actual `eval/results/*.jsonl` file for the `FineTuningRun` being published. This turns FR-009/FR-010 into a pre-publish gate rather than a post-hoc documentation task that can be skipped under time pressure.
