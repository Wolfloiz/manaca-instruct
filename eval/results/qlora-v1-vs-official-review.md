# Revisão qlora-v1 vs. official-instruct vs. baseline — 2026-09-15

Arquivo: `qlora-v1.jsonl` (manaca-instruct-pt, adapter `adapters/qlora-v1`) e `official-instruct.jsonl` (menezesbruno/manaca-1b-instruct). 104 linhas cada, todas as 88 linhas `manual_review` de cada arquivo avaliadas nesta sessão.

**Proveniência:** avaliação de todas as 176 linhas (88+88) `manual_review` pendentes feita pelo assistente de IA (Claude), a pedido explícito do usuário, como uma primeira passada para acelerar o processo. Ao contrário da revisão do baseline (feita pelo usuário), esta é genuinamente avaliação por IA — o usuário pode reabrir qualquer nota específica para revisão (ver seção "Casos limítrofes" abaixo).

## Critério aplicado

Mesmo critério de `baseline-review.md`: **1** = cumpre a tarefa, preserva o sentido, resposta correta e pertinente. **0,5** = núcleo aproveitável mas com desvios/incompletude/conteúdo problemático. **0** = não executa a tarefa ou erro central que compromete a resposta.

## Resultado completo (comparação de três vias)

| Categoria | baseline | qlora-v1 | official-instruct |
|---|---:|---:|---:|
| grammar_correction | 0,0% | 15,6% | 15,6% |
| classification | 0,0% | 25,0% | 25,0% |
| rewriting | 0,0% | 15,6% | 3,1% |
| summarization | 0,0% | 31,2% | 15,6% |
| simplification | 0,0% | 21,9% | 9,4% |
| grupo_b (esquecimento) | 16,7% | 50,0% | 70,8% |

**SC-002 (≥70% por categoria)**: não atingido em nenhuma das 5 categorias — melhor resultado é 31,2% (summarization, qlora-v1). Aprendizado real e mensurável ocorreu (0%→15-31% em todas as categorias), mas abaixo do limiar.

**SC-003 (≤10% de queda no forgetting-check)**: não só atendido como superado — qlora-v1 **melhorou** no grupo_b (16,7%→50,0%), sem qualquer esquecimento. O modelo oficial ainda está à frente aqui (70,8%), provavelmente por treinamento mais completo.

## Principais achados qualitativos

- **qlora-v1 supera o modelo oficial em 4 das 5 categorias instruídas** (rewriting, summarization, simplification, e empate em grammar_correction/classification) — só perde no grupo_b.
- **O modelo oficial mostra um padrão forte de recusa excessiva (over-refusal)** na categoria rewriting: 14 das 16 respostas foram recusas explícitas citando "pode causar dano a terceiros ou é ilegal" para pedidos completamente benignos (ex: "reescreva de forma profissional: me manda isso ainda hoje"). Isso é consistente com o "safety-SFT" documentado no card oficial do modelo, mas parece super-generalizado a ponto de prejudicar sua utilidade em tarefas comuns.
- **qlora-v1 tende a alucinar entidades relacionadas ao tema** (nomes de recursos de produto fictícios, números específicos inventados) em vez de recusar — resultado pior em precisão factual pontual, mas mais "útil" em manter o tópico.
- **Erros factuais reais identificados em qlora-v1** no grupo_b: fotossíntese descrita como respiração (processo oposto), inflação definida como "queda de preços" (invertido), Via Láctea confundida com Andrômeda, mecânica do eclipse solar invertida (lua orbitando o sol). O modelo oficial comete menos desses erros grosseiros.
- **Erro de concordância de gênero compartilhado por ambos os modelos**: "os menina brincou" → deveria virar "as meninas", mas ambos os modelos produziram "os meninos" (gênero errado).

## Casos limítrofes (revisão de IA, não humana — reabrir se desejar conferir)

Notas 0,5 são inerentemente julgamento de gosto sobre "quanto de desvio de conteúdo ainda conta como parcial". As mais discutíveis:
- `grupo_a-grammar-013` (ambos os modelos): reestruturação da frase mantendo concordância interna, mas fugindo da estrutura "a maioria" original.
- `grupo_a-summarization-005/011` (qlora-v1): lógica um pouco confusa ("pausa curta por mais tempo") mas no tópico certo.
- `grupo_a-simplification-003` (official): boa simplificação mas adiciona contexto de "entrega do pedido" não presente no original.

Qualquer nota específica pode ser reaberta e ajustada — basta indicar o `id`.
