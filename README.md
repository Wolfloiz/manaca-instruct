# Manacá Local — Manacá-Instruct-PT

Fine-tuning [`menezesbruno/manaca-1b-base`](https://huggingface.co/menezesbruno/manaca-1b-base) — an
open Brazilian-Portuguese base language model — into an instruction-following model
("Manacá-Instruct-PT") using QLoRA, as a hands-on project through the full LLM specialization
lifecycle: dataset curation, supervised fine-tuning, evaluation, quantization, and cross-hardware
deployment.

**Published model**: [`loizlabz/manaca-instruct-pt`](https://huggingface.co/loizlabz/manaca-instruct-pt)
(merged weights + Q4_K_M / Q5_K_M GGUF; the model card carries the blind evaluation table against
`qlora-v2` and the official `menezesbruno/manaca-1b-instruct`, the usage snippets, and the
limitations — read it before using the model).

This is a **personal/learning project**, not an official release. See
[`manaca-local-projeto.md`](manaca-local-projeto.md) for the original project vision and
[`roadmap-execucao.md`](roadmap-execucao.md) for the execution estimate.

## Project trail

This project went through the full [Spec Kit](https://github.com/github/spec-kit) assessment and
specification pipeline before any code was written:

1. [`.specify/assessments/manaca-instruct-pt/`](.specify/assessments/manaca-instruct-pt/) — intake,
   research, problem definition, concept shaping, and the go/no-go decision
2. [`specs/001-manaca-instruct-tuning/`](specs/001-manaca-instruct-tuning/) — spec, plan, research,
   data model, contracts, tasks

Read [`specs/001-manaca-instruct-tuning/spec.md`](specs/001-manaca-instruct-tuning/spec.md) first —
it's the single source of truth for what this feature does and why.

## Status

Scaffolding and script code are in place; **no dataset has been downloaded and no model has been
trained yet**. See [`specs/001-manaca-instruct-tuning/tasks.md`](specs/001-manaca-instruct-tuning/tasks.md)
for exactly what's done vs. still pending (checkbox state is kept current there, not here).

The five target task categories: grammar correction, rewriting, summarization, simplification,
classification — all in Brazilian Portuguese.

## Getting started

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # then install the CUDA build of torch matching your GPU driver
```

Then follow [`specs/001-manaca-instruct-tuning/quickstart.md`](specs/001-manaca-instruct-tuning/quickstart.md)
end to end — it's the runnable validation path for every user story, in priority order, starting
with establishing a baseline on the untouched base model.

## Repository layout

```text
configs/         QLoRA + inference generation settings
data/eval/       fixed, frozen evaluation prompts (never used for training)
data/            training/validation splits (produced by src/prepare_dataset.py)
src/             pipeline scripts — see specs/001-manaca-instruct-tuning/plan.md for the full map
eval/results/    evaluation run outputs (base vs. instruct vs. official-instruct)
adapters/        trained LoRA adapter checkpoints
models/          merged model + quantized GGUF artifacts
benchmarks/      per-machine throughput/resource measurements
tests/           contract tests (shared JSONL schemas) + unit tests
```

## License

The base model (`menezesbruno/manaca-1b-base`) is CC BY 4.0. The instruction datasets used to
fine-tune it are CC BY-NC-4.0, so the published Manacá-Instruct-PT model is CC BY-NC-4.0 too —
see [`MODEL_CARD.md`](MODEL_CARD.md) for the full attribution.
