# Problem Definition: Manacá-Instruct-PT — Instruction-Tuned Version of the Manacá-1B Base Model

- **Slug**: manaca-instruct-pt
- **Created**: 2026-09-14
- **Inputs used**: intake.md, research.md

## Problem Statement

The author has hands-on, project-based experience they want with the full LLM specialization lifecycle (dataset creation, supervised fine-tuning, QLoRA, evaluation, quantization, and local deployment) but no completed end-to-end project demonstrating it, and no working local PT-BR instruction-following assistant of their own. Today only the raw `menezesbruno/manaca-1b-base` model exists to build from — it is a base (next-token) model, not instruction-tuned, so prompts phrased as instructions (e.g. "Explique o que é X") are not reliably followed as instructions. The author confirmed (2026-09-14) that the project's purpose is dual: the hands-on lifecycle experience is the primary driver, but the resulting model must also be genuinely usable locally, not a throwaway exercise. The author further confirmed (2026-09-14) intent to publish the finished model publicly on Hugging Face, so other people — not only the author — are intended end users of the result.

## Affected Users & Stakeholders

- **Users**: The author themself (solo developer/learner, PT-BR speaker) — directly affected as a user of the resulting local PT-BR assistant and as the person gaining the hands-on lifecycle experience.
- **Users (public, confirmed 2026-09-14)**: Other Hugging Face users who download and run the published Manacá-Instruct-PT model — the author confirmed intent to publish the model publicly on Hugging Face for others to use, not just for personal/local use. — [source: user, 2026-09-14]
- **Stakeholders**: The author — owns all scope, timeline, and hardware decisions; also the audience deciding whether the "learning" goal is met.
- **Stakeholders (public downloaders)**: Anyone who finds and downloads the model from Hugging Face — their experience depends on model quality and usability (see Success Metrics), but they have no input into scope or requirements; the author sets the bar unilaterally. — [source: user, 2026-09-14]
- **Stakeholders (portfolio audience)**: Future reviewers of the author's portfolio (e.g. potential employers/collaborators) — interested in the finished repo/demo as evidence of capability, but not involved in defining requirements. — ASSUMPTION (confidence: low; inferred from repeated "demonstração de portfólio" framing in the source documents, not explicitly confirmed by the author)

## Goals

- Gain direct, practical experience executing every stage of the LLM specialization lifecycle end-to-end: dataset construction, SFT, QLoRA, evaluation methodology, model merging, GGUF quantization, and local deployment across two different hardware tiers.
- Produce a Manacá-Instruct-PT model that measurably improves on instruction-following for the defined PT-BR task categories (grammar correction, rewriting, summarization, simplification, classification) relative to the untuned Manacá-1B-base, per research.md's Data & Constraints section.
- Avoid severe catastrophic forgetting of the base model's original PT-BR language capabilities while gaining instruction-following ability (per project doc §30's Grupo A/Grupo B framing).
- Produce a model the author considers genuinely usable in real local use on the primary dev machine (RTX 5050) and, ideally, on the older deployment target (Dell G3 / GTX 1050) — not merely one that passes a fixed eval set.
- Leave behind a reproducible, documented pipeline (scripts, dataset, eval harness) as a durable portfolio/learning artifact.
- Publish the finished model publicly on Hugging Face so other people can download and use it, not only the author. — [source: user, 2026-09-14]

## Non-Goals

- Not competing with, or attempting to match the raw benchmark quality of, more mature already-shipped PT-BR instruction-tuned models (e.g. Tucano2-qwen 0.5B–3.7B with SFT+APO) — per research.md, those already exist and are more mature; this project's value is not contingent on beating them.
- Not reproducing or replacing the official Manacá pretraining pipeline (Megatron-LM, full corpus pretraining) — explicitly out of scope per the source project document §2.2–2.4.
- Not building a production-grade, multi-user, or externally-hosted service (e.g. a hosted API with uptime/SLA guarantees). Distribution to other people is via a downloadable Hugging Face model artifact, not a running service; any API/interface/RAG layer (project doc §24–27) remains a later, optional local extension, not part of this problem's success criteria. — revised 2026-09-14 given confirmed public-release goal
- Not providing ongoing support, moderation, or maintenance commitments to public downloaders — publishing the model does not imply an obligation to respond to issues or requests from the public. — ASSUMPTION (confidence: low; not yet confirmed by the author)
- Not blocked by, or required to preempt, a hypothetical future official Manacá-Instruct release — that risk is noted (see Open Questions) but does not change the learning-driven goal.

## Success Metrics

- Instruction-following gain: measurable improvement on the fixed evaluation prompt set (project doc §13) across all five task categories, Base vs. Instruct, using the scoring approach in project doc §19/§31 (baseline: unmeasured — the Phase 1 baseline run in project doc §12 has not yet been executed, per roadmap-execucao.md's "Nada implementado ainda").
- Minimal catastrophic forgetting: Grupo B ("capacidades originais") metrics from project doc §30 remain close to the untuned base model's scores, not just Grupo A gains (baseline: unmeasured).
- Successful cross-hardware deployment: the quantized GGUF model runs and produces coherent PT-BR instruction-following output on the Dell G3 / GTX 1050 target, with tokens/sec and VRAM/RAM usage recorded per project doc §23 (baseline: unmeasured — no GTX 1050-specific benchmark was found in research.md, and no run has occurred yet).
- Genuine usability, confirmed 2026-09-14: the model runs "sem gargalos" (without bottlenecks/stalls — reliable, responsive generation, not just occasionally-correct output) at approximately **70 tokens/second** — [source: user, 2026-09-14]. [NEEDS CLARIFICATION: which hardware this 70 tok/s target applies to (RTX 5050 dev machine, GTX 1050 Dell G3 deployment target, or both) and at what quantization level, since the two machines have very different expected throughput per research.md's Data & Constraints section.]
- Public release readiness: the model is published on Hugging Face with sufficient documentation (model card, intended use, known limitations) for other people to download and run it successfully. — [source: user, 2026-09-14]
- Lifecycle completeness (qualitative): every stage in the pipeline (dataset → SFT/QLoRA → eval → merge → GGUF → deployment) is actually executed and documented at least once, regardless of final model quality — this is how the "learning" goal is measured independent of the "usability" goal.

## Cost of Inaction

If this is never built, the author continues without direct, hands-on experience executing the full LLM specialization lifecycle on owned hardware, and without a personal, reproducible artifact demonstrating that experience. For pure task-completion needs (grammar correction, rewriting, summarization in PT-BR), the author has viable substitutes today — already-shipped, more mature instruction-tuned PT-BR models such as Tucano2-qwen, or general-purpose hosted assistants — so inaction carries effectively no capability cost for the "usable assistant" half of the goal. The cost of inaction falls entirely on the learning/portfolio half of the goal, which by definition cannot be satisfied by using someone else's finished model.

## Open Questions

- **RESOLVED (2026-09-14, source: user)**: Anyone besides the author is expected to use the finished model — the author intends to publish it publicly on Hugging Face. See Affected Users & Stakeholders and Goals.
- **RESOLVED (2026-09-14, source: user)**: The Dell G3's GTX 1050 has 4GB VRAM, matching research.md's medium-confidence assumption based on typical retail configurations for this generation.
- **RESOLVED (2026-09-14, source: user)**: The project should actively track whether the official Manacá team ships an instruct version, by monitoring the team's LinkedIn and/or GitHub (`Instituto-IA-LNCC/manaca-1b-base`) for announcements — a lightweight watch, not a blocking dependency. [NEEDS CLARIFICATION: what action to take if an official release does appear mid-project — this is a `/speckit-assess-shape` or `/speckit-assess-decide` risk-response decision, not yet made.]
- **RESOLVED (2026-09-14, source: user)**: The Hugging Face model card/documentation will disclose that this is a personal/learning project, at least for the initial release ("for now" — the author may revisit this framing later, e.g. if the model matures or scope changes).
- **OPEN — author does not yet know (2026-09-14, source: user)**: Which specific existing instruction dataset(s) will be used or adapted (e.g. translated Alpaca, Canarim, a custom mix). Explicitly deferred to `/speckit-assess-shape`, which should present the candidate options from research.md (dominguesm/alpaca-data-pt-br, Canarim Instruct Dataset ~300k, translated Dolly/OASST/HH-RLHF blends) for a scoping decision.
- **OPEN — author does not yet know (2026-09-14, source: user)**: Which hardware/quantization the ~70 tokens/second usability target applies to (RTX 5050 dev machine, GTX 1050 Dell G3 deployment target, or both), and whether an output-quality threshold beyond raw speed is also required. Explicitly deferred to `/speckit-assess-shape`.
