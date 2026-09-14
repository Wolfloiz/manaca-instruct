# Idea Intake: Manacá-Instruct-PT — Instruction-Tuned Version of the Manacá-1B Base Model

- **Slug**: manaca-instruct-pt
- **Created**: 2026-09-14
- **Source**: repo path — `manaca-local-projeto.md` and `roadmap-execucao.md` (project root)
- **Type**: new-capability

## Idea (as captured)

From `manaca-local-projeto.md`:

> "A proposta deste projeto é transformar o modelo **Manacá-1B-base** em um pequeno modelo de linguagem especializado em tarefas de português brasileiro, treinado localmente e posteriormente implantado em hardware mais modesto. [...] A ideia central é criar um **Manacá-Instruct-PT**, capaz de executar instruções em português como: corrigir textos; melhorar clareza; reescrever em diferentes tons; resumir; simplificar linguagem; classificar textos; responder perguntas sobre documentos; atuar como base de um assistente local em português."

Pipeline proposed: `Manacá-1B-base → dataset de instruções PT-BR → SFT → QLoRA → Manacá-Instruct-PT → avaliação → merge → GGUF → Dell G3 (llama.cpp) → API (FastAPI) → interface → RAG (opcional)`.

Base model: `menezesbruno/manaca-1b-base` (Hugging Face), ~1.7B parameters, causal LM, base (not instruction-tuned), PT-BR, 4096-token context. Official upstream repo: `https://github.com/Instituto-IA-LNCC/manaca-1b-base` (referenced as text in the source document, not fetched — per URL Trust Policy this is treated as unverified reference material, not a live source).

Hardware: primary dev/training machine is an ASUS TUF Gaming F16 (RTX 5050 Laptop, 8GB VRAM, Blackwell), used for QLoRA fine-tuning via Transformers + PEFT + TRL (explicitly *not* the official Megatron-LM pretraining pipeline — the source document is careful to separate "official Manacá pipeline" from "this project's extensions"). Secondary deployment-validation machine is a Dell G3 (i5 8th gen, GTX 1050, 32GB RAM) for GGUF/llama.cpp inference testing, chosen to validate whether a model trained on modern hardware can be compressed and deployed on older hardware.

From `roadmap-execucao.md`:

> "Nada implementado ainda — apenas o documento de planejamento. Nenhum ambiente, script, dataset ou repositório existia antes desta estrutura de pastas."

This second document is an execution-estimate companion to the first, modeling delivery with "3 código agents working in parallel + 1 person," and explicitly calling out the real bottleneck: "Agentes de código paralelizam a criação de artefatos [...], mas não paralelizam: o treinamento em si — GPU única [...] e sequencial; a curadoria de qualidade do dataset PT-BR [...]; os testes físicos no Dell G3." It estimates: 3–5 days for the minimal Base-vs-Fine-Tuned milestone (Phases 1–4), ~1.5–2 weeks for a full v1 without RAG (through Phase 10), and ~2.5–3 weeks including optional RAG (Phase 11).

## Restated

The idea is to take the existing PT-BR base language model "Manacá-1B-base" and produce an instruction-following variant ("Manacá-Instruct-PT") through QLoRA/PEFT supervised fine-tuning on a self-built PT-BR instruction dataset (grammar correction, rewriting, summarization, simplification, classification), evaluate it against the base model to check for gains vs. catastrophic forgetting, then quantize it to GGUF and deploy it locally — first on a modern gaming laptop (RTX 5050, for training) and then on an older laptop (GTX 1050, via llama.cpp, to validate low-end deployability) — with an optional later phase adding a FastAPI service, a simple web UI, and a RAG layer for document Q&A.

## Origin & Context

- **Raised by**: [NEEDS CLARIFICATION: the two source documents are unsigned planning docs in the repo; no author/owner name is recorded in either file. Given the repo owner's account (luizhfmonteiro@gmail.com) and the personal/portfolio framing throughout ("ótima para demonstração de portfólio"), this appears to be a solo personal/learning project, but this is inferred, not stated.]
- **Trigger**: [NEEDS CLARIFICATION: no explicit trigger event is recorded — no complaint, outage, or external ask. The documents read as a self-initiated learning/portfolio project built around a specific already-published base model (`menezesbruno/manaca-1b-base`) and specific hardware the author already owns.]

## First-Glance Unknowns

- [NEEDS CLARIFICATION: Is there a real, current need for a PT-BR instruction-following assistant, or is the primary goal learning/portfolio value? This materially changes how "relevance" should be judged later.]
- [NEEDS CLARIFICATION: Does an instruction-tuned PT-BR variant of this specific base model already exist publicly (from the official Manacá team or others), which would reduce novelty?]
- [NEEDS CLARIFICATION: What is the actual quality/reliability of `menezesbruno/manaca-1b-base` as a foundation — no benchmark numbers or known limitations are cited in either source document.]
- [NEEDS CLARIFICATION: Where will the PT-BR instruction dataset come from — the documents describe format and categories but not a data source, licensing, or volume beyond "100–300 exemplos," and note dataset quality curation is a manual, non-parallelizable bottleneck.]
- [NEEDS CLARIFICATION: Is 8GB VRAM (RTX 5050) actually sufficient for QLoRA fine-tuning a 1.7B model at usable batch sizes/context length — asserted in the doc but not yet validated (Phase 1/"baseline" is still unexecuted per the roadmap doc).]
- [NEEDS CLARIFICATION: What does "success" look like beyond the single illustrative example in §38 (one grammar-correction prompt) — no quantitative target/threshold is defined for the eval metrics listed in §19.]
- [NEEDS CLARIFICATION: Is RAG/API/UI in scope for an initial relevance/viability assessment, or should this intake be scoped strictly to the core Manacá-Instruct-PT fine-tuning objective (§5), treating RAG/API/UI as out-of-scope future extensions per the source document's own phasing?]
