# Roadmap de Execução — Manacá Local

Este documento complementa o [manaca-local-projeto.md](./manaca-local-projeto.md) (visão/arquitetura oficial do projeto) com uma estimativa de execução considerando **3 agentes de código trabalhando em paralelo + 1 pessoa (você)**.

## Status no início do projeto

Nada implementado ainda — apenas o documento de planejamento. Nenhum ambiente, script, dataset ou repositório existia antes desta estrutura de pastas.

## O gargalo real

Agentes de código paralelizam a *criação de artefatos* (dataset, scripts, API, docs, RAG), mas não paralelizam:

- o treinamento em si — GPU única (RTX 5050, 8GB) e sequencial;
- a curadoria de qualidade do dataset PT-BR — exige revisão humana;
- os testes físicos no Dell G3 — segunda máquina, acesso manual.

Mais agentes não encurtam uma rodada de fine-tuning; encurtam o tempo até chegar nela.

## Estimativa por fase

| Fase | O que é | Paralelizável com 3 agentes? | Tempo |
|---|---|---|---|
| 1. Baseline | WSL2/CUDA/env, rodar modelo base | Não (você, na máquina) | 0,5–1 dia |
| 2. Dataset | 100–300 exemplos, 5 categorias, JSONL | Sim — 3 agentes geram categorias em paralelo, você revisa qualidade | 1–2 dias |
| 3. QLoRA v1 | Script de treino + rodar na GPU | Script: agente. Treino real: sequencial na GPU (1–3h/rodada + ajustes) | 1 dia |
| 4. Avaliação | Harness Base×Instruct, prompts fixos | Sim, em paralelo à fase 3 | 0,5 dia |
| 5. Iteração | Ajustar dataset/hiperparâmetros, retreinar | Parcial — mais rodadas de GPU sequenciais | 1–2 dias |
| 6. Merge | Script simples | Sim | poucas horas |
| 7. GGUF/quantização | Conversão llama.cpp | Sim (prep) + você roda | 0,5 dia |
| 8. Dell G3 | Deploy e benchmark na máquina antiga | Não (você, fisicamente) | 0,5 dia |
| 9. API FastAPI | Endpoints /generate, /health | Sim, 100% paralelizável | 0,5–1 dia |
| 10. Interface | Gradio/Streamlit | Sim | 0,5 dia |
| 11. RAG (opcional) | PDF→embeddings→FAISS→citação | Sim, mas é a etapa mais longa depois do dataset | 2–3 dias |

## Totais

- **Meta prática mínima** (Fases 1–4, Base vs Fine-Tuned funcionando): **3–5 dias corridos**, com algumas horas/dia de uso ativo — seu tempo na GPU é o limitador, não os agentes.
- **v1 completa sem RAG** (até Fase 10 — API + interface): **+1 semana**, total ≈ **1,5–2 semanas**.
- **Com RAG incluído** (Fase 11): **+3–4 dias**, total ≈ **2,5–3 semanas**.

Assume dedicação de algumas horas por dia (não full-time).

## Divisão sugerida entre os 3 agentes (fases 2–4 e 9–11)

- **Agente 1** — dataset: gera exemplos de correção gramatical e reescrita profissional; monta `prepare_dataset.py` e splits treino/validação/teste.
- **Agente 2** — dataset + avaliação: gera exemplos de simplificação, resumo e classificação; monta o conjunto de avaliação fixo e o harness comparador Base×Instruct.
- **Agente 3** — infraestrutura: `train_qlora.py`, `merge_adapter.py`, scripts de conversão GGUF, e depois API FastAPI / interface.
- **Você** — revisão de qualidade do dataset em português, setup do ambiente CUDA, execução das rodadas de treino na GPU, testes no Dell G3, decisões de hiperparâmetros a partir dos resultados de avaliação.
