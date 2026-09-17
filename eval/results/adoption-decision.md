# Decisão de adoção — iteração 002 (data quality)

Documento vivo da US1 → US4 (specs/002 FR-019, FR-020). Cita apenas arquivos `-blind`.

## Presentation (FR-019) — decidido em 2026-09-16

Experimento: `qlora-v2` avaliado nas duas apresentações (`combined` = prompt em linha única, como em 001;
`split` = `### Instrução` / `### Entrada` separados) e graduado às cegas, intercalado, numa única sessão
(`review_cli --blind --interleave --shuffle-seed 7`). Relatório: `presentation-experiment.md`
(`qlora-v2-blind.jsonl`, `qlora-v2-split-blind.jsonl`, 0 linhas sem nota).

Deltas por categoria (`split` − `combined`):

| categoria | mean combined | mean split | Δ mean | full_rate combined | full_rate split | Δ full_rate |
|---|---:|---:|---:|---:|---:|---:|
| grammar_correction | 0.438 | 0.344 | −0.094 | 0.375 | 0.312 | −0.063 |
| classification | 0.250 | 0.188 | −0.062 | 0.250 | 0.188 | −0.062 |
| rewriting | 0.062 | 0.062 | 0.000 | 0.000 | 0.000 | 0.000 |
| summarization | 0.062 | 0.156 | +0.094 | 0.000 | 0.000 | 0.000 |
| simplification | 0.094 | 0.062 | −0.032 | 0.000 | 0.000 | 0.000 |
| grupo_b | 0.333 | 0.271 | −0.062 | 0.083 | 0.042 | −0.041 |

Regra FR-019: `split` se alguma categoria diferir em ≥ 2/16 = 0.125 em `mean` ou `full_rate`. Maior |Δ| = 0.094
(gramática e resumo). **Apresentação selecionada: `combined`.** A tabela final e os candidatos v3 são avaliados
em `combined`; os resultados `split` ficam documentados apenas como medição.

Consequência: a linha do modelo oficial na tabela final é `official-instruct-blind.jsonl` (regraduação cega do
arquivo `official-instruct.jsonl` de 001, congelado). Uma avaliação `official-instruct-split` foi iniciada antes
da decisão e abandonada (4/88 notas); seus arquivos foram removidos do repositório neste commit porque o
resultado `.jsonl` estava corrompido (sobrescrito por um script) e não entram em nenhuma tabela.

## Proveniência das notas cegas

- `qlora-v2-blind.jsonl`, `qlora-v2-split-blind.jsonl`: 100% graduados pelo autor.
- `official-instruct-blind.jsonl`: 53 linhas graduadas pelo autor; as **35 restantes foram graduadas por IA
  (Claude Code) a pedido do autor**, calibrando pelas 53 notas já dadas, e aceitas sem recontagem. Ids:
  grammar 004, 005, 006, 008, 009, 011, 013, 014, 016; rewriting 006, 013, 014; summarization 003, 009, 010,
  011, 014, 015; simplification 008, 010, 011, 012, 013, 015, 016; grupo_b 001, 002, 004, 005, 006, 008, 009,
  010, 011, 015. Notas 1 dadas pela IA: grupo_b-002, 004, 010. O `research.md` §6 rejeita LLM-as-judge; esta
  exceção fica registrada aqui e deve constar no model card.
- `qlora-v3a-blind.jsonl`, `qlora-v3b-blind.jsonl`: 176 notas do autor, sessão única intercalada (`--shuffle-seed 11`);
  7 notas dadas na CLI e 169 anotadas fora dela seguindo a mesma ordem de apresentação da CLI (verificado: posição → linha
  bate 169/169) e gravadas nos arquivos `-blind` pelas funções da própria CLI.
- `qlora-v2-split.manifest.json` está com `git_dirty: true` por um defeito do `run_manifest` na época (o próprio
  `qlora-v2-split.jsonl`, ainda não rastreado, contava como sujeira); o commit citado é o correto. Corrigido antes
  das avaliações dos candidatos, que são regeradas com `git_dirty: false`.

## Candidatos (T046–T047)

| run | commit | dados (sha256 train / validation) | objetivo | eval_loss por época | best / adapter |
|---|---|---|---|---|---|
| qlora-v3a | `f4971b7` | `9b3d3ca3…` / `4d0e9801…` (= `dataset_report.json`) | full-sequence (`completion_only_loss: false`) | 1.836 → 1.654 → 1.614 | 3 / 3 |
| qlora-v3b | `24a3bbd` | idem | response-only (`completion_only_loss: true`) | 1.628 → 1.573 → 1.559 | 3 / 3 |

Os eval_loss de v3a e v3b não são comparáveis entre si (v3b só conta tokens de resposta). Como `best_epoch ==
adapter_epoch` nos dois, não há linha `-best` (T049 não se aplica).

## Tabela final (T051) — `final-table.md`, apresentação `combined`, todas as linhas cegas

| categoria | v2 mean / full | v3a mean / full | v3b mean / full | oficial mean / full |
|---|---:|---:|---:|---:|
| grammar_correction | 0.438 / 0.375 | **0.031 / 0.000** | **0.062 / 0.000** | 0.125 / 0.000 |
| classification | 0.250 / 4/16 | 0.625 / **10/16** | 0.750 / **12/16** | 0.250 / 4/16 |
| rewriting | 0.062 / 0.000 | 0.094 / 0.000 | 0.125 / 0.125 | 0.000 / 0.000 |
| summarization | 0.062 / 0.000 | 0.094 / 0.000 | 0.156 / 0.000 | 0.031 / 0.000 |
| simplification | 0.094 / 0.000 | 0.188 / 0.000 | 0.219 / 0.062 | 0.031 / 0.000 |
| grupo_b (24) | 0.333 / 0.083 | 0.500 / 0.333 | 0.438 / 0.333 | 0.333 / 0.125 |
| **grupo A full_rate (80)** | 4/80 = 0.050 | 10/80 = **0.125** | 15/80 = **0.188** | 4/80 = 0.050 |

## Regra FR-020 e resultado (T051, 2026-09-16)

| candidato | classificação ≥ 8/16 | full_rate grupo A ≥ 0.20 | nenhuma categoria abaixo da v2 (mean) | queda grupo_b ≤ 10% | resultado |
|---|---|---|---|---|---|
| qlora-v3a | ✓ 10/16 | ✗ 0.125 | ✗ grammar 0.031 < 0.438 | ✓ (+50%) | **declined** |
| qlora-v3b | ✓ 12/16 | ✗ 0.188 | ✗ grammar 0.062 < 0.438 | ✓ (+31%) | **declined** |

**Resultado: `declined` para os dois candidatos.** Nenhum satisfaz o FR-020; `qlora-v2` permanece o modelo final da
feature 001 (FR-023) salvo se um run condicional (FR-021, no máximo três) qualificar. O cenário 3 da US4 (v3b falha
onde v3a passa) não se aplica — os dois falham nas mesmas duas regras.

### Atribuição das diferenças observadas

v2 → v3a muda apenas os dados; v3a → v3b muda apenas o objetivo (FR-018). Contagens pareadas em `final-table.md`.

| diferença | fator | evidência |
|---|---|---|
| Classificação 4/16 → 10/16 (v3a) e 12/16 (v3b); v2 respondia "reclamação" em 12/16, os v3 usam os quatro rótulos | **dados** (seed de 197 exemplos nos quatro rótulos) | 8 melhoraram / 2 pioraram v2→v3a; v3a→v3b +2 é 5/3, dentro do ruído |
| Gramática 0.438 → 0.031 / 0.062; 6/16 inteiramente corretas → 0/16 | **dados** | 0 melhoraram / 8 pioraram v2→v3a; v3a→v3b 2/1. Mecanismo não verificado: as linhas de gramática caíram de 681 para 355 no treino (17,2% → 10,5% da mistura); pela proxy "output ≈ input" as linhas v3 são *mais* limpas (59% vs 34%), e não há vazamento no v2 (0/16 prompts de gramática com vizinho ≥ 75 no treino v2) — a suspeita é o volume/peso da categoria, não a qualidade |
| grupo_b 0.333 → 0.500 (v3a) / 0.438 (v3b); full_rate 0.083 → 0.333 | **dados**; o objetivo custa um pouco (v3a→v3b 2 melhoraram / 5 pioraram) | 7/1 v2→v3a |
| Simplificação 0.094 → 0.188 / 0.219; resumo 0.062 → 0.094 / 0.156; reescrita 0.062 → 0.094 / 0.125 | **dados**, com contribuição fraca do **objetivo** em resumo (4/2) e reescrita (2/2, mas 2 respostas inteiramente corretas só no v3b) | diferenças pequenas, ≤ 5 prompts |
| Todas as categorias exceto gramática: v3b ≥ oficial | dados | — |

### Próximo passo (T053)

Os bloqueios são dois: a regressão de gramática (fator: dados) e o `full_rate` do grupo A abaixo de 0.20 (v3b em
0.188 — faltam 2 respostas inteiramente corretas em 80). Runs condicionais devem mirar um dos dois com um único fator
cada; a decisão e a justificativa de cada run ficam registradas aqui antes de rodar.
