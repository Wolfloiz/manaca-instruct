# Seed de classificação (4 rótulos) — proveniência

Arquivo: `classification_4class.jsonl` (197 linhas, `source: seed-llm`, `task_category: classification`).
Exemplos sintéticos de mensagens de atendimento ao cliente, gerados por um modelo de linguagem e revisados
um a um pelo autor (specs/002 FR-011; contracts/dataset-preparation.md § `data/seed/`).

## Modelo gerador

- **Modelo gerador**: Qwen2.5-7B-Instruct (Alibaba/Qwen), quantização GGUF Q4_K_M
  (`bartowski/Qwen2.5-7B-Instruct-GGUF`, arquivo `Qwen2.5-7B-Instruct-Q4_K_M.gguf`), executado localmente
  com `llama.cpp` (`llama-server`, `-ngl 99 -c 4096`), temperatura 0.9, `max_tokens` 900.
- **Data de geração**: 2026-09-16.
- **Termos de uso consultados**: Apache License 2.0 — arquivo `LICENSE` de
  <https://huggingface.co/Qwen/Qwen2.5-7B-Instruct> (o repositório GGUF usado,
  <https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF>, declara a mesma licença). A Apache 2.0 não impõe
  restrição sobre o uso dos outputs do modelo nem sobre treinar outros modelos com eles.
- **Conclusão de compatibilidade**: compatível — os outputs podem ser usados para treinar um modelo redistribuído
  sob CC BY-NC 4.0.

## Prompt de geração

Uma chamada por lote de 10 mensagens, com o rótulo e um cenário de empresa sorteado (loja online de roupas,
banco / cartão de crédito, operadora de internet e celular, plano de saúde, aplicativo de entrega de comida,
software por assinatura (SaaS), companhia aérea, secretaria de universidade, RH de uma empresa, seguradora de carro,
clínica veterinária, academia de ginástica, loja de eletrônicos, prefeitura / serviço público, hotel / pousada,
escola de idiomas). Texto do prompt (`{N}`, `{cenário}`, `{rótulo}`, `{definição}` e `{últimas 8 mensagens}`
substituídos por chamada):

```
Gere {N} mensagens curtas e variadas de clientes para o atendimento de uma empresa do tipo: {cenário}.
Todas as mensagens devem ser do tipo **{rótulo}** ({definição}).
Regras: português do Brasil, tom natural de cliente real (formal e informal misturados), entre 4 e 25 palavras,
sem nomes de empresas reais, sem números de pedido/telefone, cada mensagem sobre uma situação diferente,
e sem usar a palavra do rótulo na mensagem. Não repita as mensagens: {últimas 8 mensagens}.
Responda SOMENTE com um array JSON de strings.
```

Definições passadas em `{definição}`:

- reclamação — o cliente relata um problema, insatisfação ou falha (sem pedir explicitamente uma ação)
- dúvida — o cliente faz uma pergunta para obter uma informação
- elogio — o cliente agradece ou elogia o serviço, produto ou atendimento
- solicitação — o cliente pede que algo seja feito (cancelar, enviar, alterar, emitir, agendar...)

Duplicatas exatas (texto normalizado em minúsculas) foram descartadas na geração.

## Revisão e contagens

Cada candidata foi revisada pelo autor com três decisões possíveis — manter, editar (texto e/ou rótulo) ou
descartar — vendo, ao lado, a mensagem de avaliação mais parecida (`rapidfuzz.token_set_ratio` contra as 16
mensagens de classificação de `data/eval/grupo_a_prompts.jsonl`).

| | total |
|---|---:|
| geradas | 207 |
| mantidas sem alteração | 147 |
| editadas (texto e/ou rótulo) | 50 |
| descartadas | 10 |
| **no arquivo final** | **197** |

Por rótulo no arquivo final: reclamação 66, dúvida 46, elogio 50, solicitação 35.

## Confirmação

Confirmo que cada linha mantida no arquivo foi comparada com as 16 mensagens de classificação de
`data/eval/grupo_a_prompts.jsonl` e que nenhuma delas reutiliza ou parafraseia uma mensagem de avaliação.
