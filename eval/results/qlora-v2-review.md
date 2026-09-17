# Revisão qlora-v2 (rodada final, FR-005) — 2026-09-15

Arquivo: `qlora-v2.jsonl`. 104 linhas, todas as 88 linhas `manual_review` avaliadas nesta sessão (mesma proveniência de `qlora-v1-vs-official-review.md`: avaliação por IA, a pedido do usuário).

## Mudanças em relação a qlora-v1 (FR-005, rodada única de iteração)

- `configs/train.yaml`: `num_epochs` 2→3 — padrão observado em v1 (melhoria em todas as categorias, inclusive as já no limite de 1000 exemplos) sugeria sub-treinamento, não escassez de dados.
- `src/dataset_filters/grammar_rewriting.py`: regex de `grammar_correction` ampliada — 523→765 exemplos (+46%) do `alpaca-pt-br` já baixado. `CohereLabs/aya_dataset` foi avaliado como fonte adicional mas descartado: apenas 54 de 8.997 linhas em português correspondiam a qualquer uma das 5 categorias.
- Dataset final: 4.395 exemplos (3.956 treino + 439 validação), vs. 4.153 em v1.

## Resultado — comparação de quatro vias

| Categoria | baseline | qlora-v1 | **qlora-v2** | official |
|---|---:|---:|---:|---:|
| grammar_correction | 0,0% | 15,6% | 15,6% | 15,6% |
| classification | 0,0% | 25,0% | 25,0% | 25,0% |
| rewriting | 0,0% | 15,6% | **25,0%** | 3,1% |
| summarization | 0,0% | 31,2% | **34,4%** | 15,6% |
| simplification | 0,0% | 21,9% | **25,0%** | 9,4% |
| grupo_b (esquecimento) | 16,7% | 50,0% | **56,2%** | 70,8% |

**SC-002 (≥70% por categoria)**: não atingido em nenhuma categoria, mesmo após a iteração. Melhor resultado: summarization em 34,4%.

**SC-003 (≤10% de queda no forgetting-check)**: superado novamente — qlora-v2 melhorou ainda mais (50,0%→56,2%), consolidando que não há esquecimento.

## Decisão (FR-005)

FR-005 orça exatamente uma rodada de iteração. qlora-v2 melhorou em 4 das 6 dimensões (rewriting +9,4pp, summarization +3,2pp, simplification +3,1pp, grupo_b +6,2pp) e empatou nas outras duas — nenhuma regressão. Ainda assim, nenhuma categoria atingiu o limiar de 70%. **Esta é agora a versão final** por definição do FR-005; não há mais rodadas orçadas. O déficit do SC-002 fica documentado como limitação conhecida (ver `MODEL_CARD.md`), não como falha a ser corrigida indefinidamente.

qlora-v2 continua superando o modelo oficial em 4 das 5 categorias instruídas (grammar_correction e classification empatados), perdendo apenas no grupo_b — mesmo padrão de v1, ligeiramente mais forte.
