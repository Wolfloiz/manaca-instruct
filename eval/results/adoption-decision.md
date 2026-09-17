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
- Candidatos v3 (`qlora-v3a-blind`, `qlora-v3b-blind`): a preencher no T050.
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

## Regra FR-020 e resultado — a preencher no T051

| candidato | classificação ≥ 8/16 | full_rate grupo A ≥ 0.20 | nenhuma categoria abaixo da v2 (mean) | queda grupo_b ≤ 10% | resultado |
|---|---|---|---|---|---|
| qlora-v3a | | | | | |
| qlora-v3b | | | | | |

Atribuição de cada diferença observada (dados / objetivo / checkpoint / não atribuível): a preencher.
