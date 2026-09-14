---
license: cc-by-nc-4.0
language: [pt]
base_model: menezesbruno/manaca-1b-base
tags: [instruction-tuning, portuguese, gguf, qlora, personal-project]
---

<!--
TEMPLATE — fill in the <FILL: ...> placeholders before publishing (T058).
Validated by src/publish.py's validate_model_card() (contracts/model-usage-contract.md's
pre-publish gate) before any Hugging Face push is attempted. Do not remove the
"## Evaluation results" heading or either code block below — the gate checks for them.
-->

# Manacá-Instruct-PT

## What this is

**This is a personal/learning project**, not an official or production release. It fine-tunes
[menezesbruno/manaca-1b-base](https://huggingface.co/menezesbruno/manaca-1b-base) — an open,
Brazilian-Portuguese base language model from LNCC's AI Institute — into an instruction-following
model using QLoRA, as a hands-on exercise in the full LLM specialization lifecycle (dataset
curation, supervised fine-tuning, evaluation, quantization, and deployment).

An official instruction-tuned release, [menezesbruno/manaca-1b-instruct](https://huggingface.co/menezesbruno/manaca-1b-instruct),
also exists (experimental v0.1) — see **Evaluation results** below for an honest side-by-side
comparison against it, not just against the untuned base model.

## Intended use

Supports five Brazilian-Portuguese text tasks:

- Grammar correction
- Rewriting (e.g. informal → professional tone)
- Summarization
- Simplification (e.g. simplifying formal/bureaucratic language)
- Classification (e.g. sorting a message into a fixed category set)

Not intended for production use, medical/legal advice, or automated decision-making — see
**Known limitations** below.

## How to use it

### transformers

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("<FILL: repo-id>")
model = AutoModelForCausalLM.from_pretrained("<FILL: repo-id>")

prompt = "### Instrução:\nCorrija gramaticalmente o texto.\n\n### Entrada:\nos documento foi enviado ontem\n\n### Resposta:\n"
inputs = tokenizer(prompt, return_tensors="pt")
output = model.generate(**inputs, max_new_tokens=100)
print(tokenizer.decode(output[0], skip_special_tokens=True))
```

### llama.cpp (GGUF)

```bash
llama-cli \
  -m manaca-instruct-pt-Q4_K_M.gguf \
  -p "### Instrução:\nCorrija gramaticalmente o texto.\n\n### Entrada:\nos documento foi enviado ontem\n\n### Resposta:\n" \
  -n 100 -c 4096
```

## Evaluation results

Base model vs. this model vs. the official `menezesbruno/manaca-1b-instruct` release, on the fixed
80-prompt evaluation set (16 per category — see `data/eval/grupo_a_prompts.jsonl`), sourced directly
from `eval/results/*.jsonl` — not hand-typed.

| Category | manaca-1b-base | manaca-instruct-pt | manaca-1b-instruct (official) |
|---|---:|---:|---:|
| grammar_correction | <FILL> | <FILL> | <FILL> |
| rewriting | <FILL> | <FILL> | <FILL> |
| summarization | <FILL> | <FILL> | <FILL> |
| simplification | <FILL> | <FILL> | <FILL> |
| classification | <FILL> | <FILL> | <FILL> |
| **Forgetting-check (grupo_b, 24 prompts)** | <FILL: baseline> | <FILL: relative drop %> | <FILL> |

## Known limitations

- <FILL: any category that missed the 70% pass-rate threshold (spec.md FR-004/SC-002), stated plainly, not omitted>
- <FILL: forgetting-check result if it exceeded the 10% relative-drop threshold (FR-004/SC-003)>
- The base model shows near-chance performance on multiple-choice reasoning benchmarks
  (ARC-Challenge-PT ≈ 27%, per `.specify/assessments/manaca-instruct-pt/research.md`) — this is a
  real ceiling on tasks that need more than surface-level pattern completion, independent of
  fine-tuning quality.
- Trained on a ~3,000–5,000 example blend of `dominguesm/alpaca-data-pt-br` and
  `dominguesm/Canarim-Instruct-PTBR-Dataset`; not a large-scale or professionally curated dataset.
- <FILL: measured tokens/second on <FILL: quantization level> — honest number, not the ~70 tok/s
  aspirational target, per spec.md's Edge Cases section>

## License & attribution

CC BY-NC-4.0. This restriction is inherited from the training data: both `alpaca-pt-br` and
`Canarim-Instruct-PTBR-Dataset` are CC BY-NC-4.0 because their instruction data derives from
OpenAI model outputs, whose usage policy restricts training competing models commercially — the
same reason the official `menezesbruno/manaca-1b-instruct` release is also CC BY-NC-4.0.

Base model: [menezesbruno/manaca-1b-base](https://huggingface.co/menezesbruno/manaca-1b-base),
CC BY 4.0, © LNCC AI Institute / NII-LLM-jp.
