# Plano técnico: iteração de qualidade de dados, treino e avaliação (pós-qlora-v2)

**Data**: 2026-09-15 | **Origem**: `eval/results/qlora-v2-review.md` (auditoria da rodada final de `001-manaca-instruct-tuning`) | **Status**: proposta, nada implementado

**Relação com a feature 001**: FR-005 orça exatamente uma rodada de iteração e ela foi consumida (qlora-v1 → qlora-v2). Este plano é o desenho técnico de uma **nova feature** — qualquer treino `qlora-v3*` fica fora do escopo da 001. Antes de implementar, formalizar com `/speckit-specify` (este documento vira o insumo de `plan.md`/`tasks.md` da 002). A publicação do v2 (Fase 6 da 001) é uma decisão independente: publicar agora como v0.1 com as limitações documentadas, ou segurar até o v3 — ver §6.

## 0. O que foi verificado antes de planejar

Cada alegação da revisão foi checada contra `data/train.jsonl`, `data/validation.jsonl`, `data/eval/*.jsonl`, `eval/results/qlora-v2.jsonl` e o `trl` 1.13.0 / `peft` 0.20.0 / `transformers` 5.17.0 instalados em `.venv`:

| Alegação da revisão | Verificado | Detalhe |
|---|---|---|
| `revis(e\|ão\|ar)` casa `previsão` | **Sim** | 54 instruções de gramática contêm `previs*`; 52 delas só entraram por esse substring (ex.: `alpaca-pt-br-044116`, `-050101`, `-040372`) |
| Correção de código dentro de gramática | **Sim** | 20 linhas (ex.: `alpaca-pt-br-001653` "Encontre os erros no código a seguir e corrija-os") |
| Curiosidades em simplificação | **Sim** | 173/566 no treino contêm "pista de curiosidades"; +4 de matemática (`canarim-050196`, `-029577`); 45 com `input` vazio |
| Classificação sem rótulos do teste | **Sim** | 0/905 saídas são `reclamação`/`dúvida`/`elogio`/`solicitação`; no v2 o modelo respondeu `reclamação` 12/16 vezes (colapso na classe majoritária) |
| Saídas degeneradas | **Sim** | 26 com `ssrsrs…` (todas classificação), 37 no total com repetição de caractere/bigrama (`canarim-274024`, `-301183`…); `canarim-170450` pede idioma e recebe `E-mail` |
| Duplicatas | **Sim** | 58 triplas `(instruction,input,output)` excedentes no treino; 64 pares `(instruction,input)`; 25 triplas compartilhadas treino/validação |
| Formato treino ≠ avaliação | **Sim** | 2.696/3.956 exemplos de treino usam `### Entrada:`; `src/evaluate.py::_format_inference_prompt` nunca gera esse bloco |
| Validação não usada no treino | **Sim** | `_run_training` não passa `eval_dataset`; `eval_strategy` fica no default `"no"` |
| Perda na sequência inteira | **Sim** | dataset é `{"text": ...}` → `completion_only_loss=None` resolve para perda total; formato prompt-completion está disponível no `trl` 1.13.0 |
| `prepare_model_for_kbit_training` ausente | **Sim, parcialmente coberto** | `SFTTrainer` 1.13.0 converte os parâmetros treináveis para bf16 e só chama `enable_input_require_grads` com gradient checkpointing; **não** faz o cast de layer norms para fp32 nem ativa checkpointing |
| Revisão não é cega | **Sim** | `review_cli.py::_prompt_for_score` imprime `model=` e `run_id` para o revisor |

Achado adicional (não está na revisão): **454/905** exemplos de classificação já têm o formato desejado — a saída (normalizada) é um rótulo enumerado na própria instrução. Isso dá um filtro objetivo para a categoria (§2, C3), em vez de depender só de exclusões por palavra-chave.

## 1. Princípios e o que não muda

1. **Medir barato antes de treinar.** Os dois primeiros blocos (§2 A e B) não usam GPU para treino e respondem duas perguntas abertas da revisão: quanto o formato de prompt pesa, e quanto as notas atuais estão infladas.
2. **Um fator por execução.** v2 mudou dados e épocas juntos; as execuções propostas em §3 isolam dados limpos (v3a) de objetivo/seleção de checkpoint (v3b).
3. **Congelado:** texto dos 104 prompts em `data/eval/*.jsonl`; `eval/results/{baseline,qlora-v1,qlora-v2,official-instruct}.jsonl`; `adapters/qlora-v1`, `adapters/qlora-v2`; `models/gguf/*` do v2. Nenhuma mudança abaixo reescreve esses artefatos — novas execuções geram novos arquivos com novos `run_id`.
4. **Licença não muda:** `alpaca-pt-br` (CC BY-NC-4.0) continua na mistura, logo o modelo continua CC BY-NC-4.0. Dados autorais (C6) são do autor e não alteram isso.
5. **Rastreabilidade:** o commit que gerou o dataset do v2 está no histórico (`data/train.jsonl` versionado). Após C1–C6 o `train.jsonl` muda — o v2 continua reproduzível via `git`.

## 2. Mudanças de código

Cada item: arquivo → mudança → teste → critério de aceite. Tudo passa pelo fluxo worktree → PR → revisão → merge (agente dono indicado; "Você" = decisões/dados/GPU).

### A. Formatador de prompt compartilhado + experimento de formato (Agente 2; sem treino)

**A1.** Novo `src/prompt_format.py` com `format_prompt(instruction: str, input: str = "", output: str | None = None) -> str` — única fonte do template `### Instrução / ### Entrada / ### Resposta`. `src/train_qlora.py::_format_prompt` e `src/evaluate.py::_format_inference_prompt` passam a delegar para ele (comportamento atual preservado: `input=""` omite o bloco `### Entrada:`; `output=None` termina em `### Resposta:\n`).
- Teste: `tests/unit/test_prompt_format.py` — com/sem `input`, com/sem `output`; os testes existentes `test_format_prompt_matches_manaca_template` e `test_format_inference_prompt_matches_training_template` continuam passando sem alteração.

**A2.** `EvaluationPrompt` ganha campo **opcional** `input`. O campo `prompt` continua obrigatório e intocado (é a proveniência do texto congelado). Nos 80 prompts do grupo A, `instruction`/`input` são obtidos separando o `prompt` no primeiro `: ` **de forma autoral, uma vez, revisada por Você** — não por heurística em tempo de execução. Grupo B não recebe `input`.
- Arquivos: `data/eval/grupo_a_prompts.jsonl` (+`instruction`, +`input` em cada linha), `src/schema_validation.py::validate_evaluation_prompt` (aceita os dois campos opcionais; se um vier, o outro é obrigatório), `specs/001-.../data-model.md` e `contracts/dataset-schema.md` (documentar os campos).
- Teste: contrato — para cada linha do grupo A, `f"{instruction}: {input}" == prompt` (garante que a separação não alterou o texto congelado).

**A3.** `src/evaluate.py` ganha `--prompt-format {combined,split}` (default `combined` = comportamento atual). `split` usa `format_prompt(instruction, input)` quando os campos existem. O formato fica registrado no `run_id` por convenção (`<run>-split`), sem alterar o contrato de `EvaluationResult`.
- Teste: `run_evaluation` com `_load_model`/`_generate` mockados — verificar que `split` gera `### Entrada:` e `combined` não.

**Experimento E1 (Você):** `python -m src.evaluate --model manaca-instruct-pt --adapter adapters/qlora-v2 --prompt-format split --run-id qlora-v2-split --out eval/results/qlora-v2-split.jsonl`, depois grading cego (B1) das 88 linhas. Comparar com `qlora-v2.jsonl`. **Decisão:** se a diferença por categoria for ≥ 6,25 pp (2 exemplos em 16) em qualquer categoria, o descompasso de formato é um fator real e o treino v3 deve usar A1 nos dois lados; se for menor, o formato é secundário e os dados dominam.

### B. Avaliação cega e relatório reproduzível (Agente 2; sem GPU)

**B1.** `src/grading/review_cli.py`: flag `--blind` — não imprime `model` nem `run_id`; flag `--shuffle-seed N` embaralha a ordem de apresentação (a gravação continua na ordem original do arquivo). Opcionalmente `--interleave a.jsonl b.jsonl` para avaliar duas execuções misturadas, sem saber qual é qual — é o que a revisão pede ("ocultando a identidade do modelo").
- Teste: `_prompt_for_score(..., blind=True)` não contém `model=`; interleave preserva `id`→arquivo de origem ao salvar.

**B2.** Novo `src/grading/report.py` (`python -m src.grading.report eval/results/a.jsonl eval/results/b.jsonl ...`): por categoria e por execução imprime **média com crédito parcial** e **taxa de nota 1**, distribuição 1/0,5/0, e comparação por exemplo entre pares (melhorou/piorou/empatou — a revisão calculou 16/9/79 à mão). Saída em Markdown para colar no `MODEL_CARD.md`.
- Teste: dois arquivos sintéticos com notas conhecidas → tabela esperada.

**Tarefa (Você):** re-avaliar às cegas, no mínimo, as quatro notas contestadas (`grupo_b-008`, `grupo_a-simplification-003`, `grupo_a-rewriting-016`, `grupo_a-summarization-002`) e, idealmente, as 88 linhas de `manual_review` das 4 execuções com `--interleave`. Registrar em `eval/results/<run>-regrade.jsonl` (novos arquivos; os originais ficam).

### C. Qualidade de dados (Agente 1 filtros de alpaca; Agente 2 filtros de canarim; Agente 1 `prepare_dataset`)

**C1. Gramática** — `src/dataset_filters/grammar_rewriting.py`:
- `_GRAMMAR_KEYWORDS`: `revis(e|ão|ar)` → `\brevis(e|ar|ão|ando)\b`; demais termos também com `\b` onde fizer sentido (`\bcorrij`, `\bconserte\b`).
- Novo `_GRAMMAR_EXCLUDE = re.compile(r"\bcódigo\b|\bcode\b|\bprograma\b|\bfunção\b|\bscript\b|\bsql\b|\bpython\b|\bjavascript\b|\bbug\b", re.I)` aplicado antes de rotular como `grammar_correction`.
- Teste: `"Dada uma previsão do tempo, liste…"` → `None`; `"Encontre os erros no código a seguir e corrija-os"` → `None`; `"Revise a concordância do texto"` → `grammar_correction`.
- Aceite: 0 linhas com `previs*` na categoria; 0 com os termos de código; amostra de 30 linhas pós-filtro conferida por Você com ≥ 27 (90%) sendo correção linguística de fato.

**C2. Simplificação** — `src/dataset_filters/open_ended_tasks.py`:
- Novo `_SIMPLIFICATION_EXCLUDE = re.compile(r"curiosidade|trivia|\bexpressão\b|\bequação\b|\bfração\b|\bpolinômio\b", re.I)`.
- Exigir `input` não vazio para `simplification` (o texto a simplificar precisa existir; remove as 45 sem entrada, majoritariamente tarefas que não são simplificação de texto).
- Teste: a instrução "Você receberá uma pista de curiosidades…" → `None`; "Simplifique a expressão aritmética dada" → `None`; "Reescreva em linguagem simples" com `context` → `simplification`.
- Aceite: 0 linhas com `curiosidade`; contagem esperada ≈ 340–350 (566 − 173 − 4 − 45), a confirmar no relatório de C7.

**C3. Classificação** — `open_ended_tasks.py`:
- Manter a linha só se `len(output.split()) <= 4` **e** a saída normalizada (caixa/acentos/espaços, via a mesma `_normalize_label` de `src/grading/rule_based.py`, movida para `src/text_normalize.py` para reuso) aparece na instrução normalizada — i.e. o rótulo foi enumerado nas opções. Isso preserva os 454 exemplos bem formados e elimina os 26 `ssrsrs`, `canarim-170450` e afins sem lista manual de exclusões.
- Teste: `("Classifique como positivo ou negativo…", output="Negativo")` → mantém; `(…, output="E-mail : ssrsrsrs")` → descarta; `("Classifique a língua do texto…", output="E-mail")` → descarta.
- Aceite: 0 saídas com `ssrsrs`; 100% das saídas de classificação no treino aparecem na respectiva instrução.

**C4. Filtro genérico de saída degenerada** — novo `src/dataset_filters/quality.py::is_degenerate_output(text) -> bool`: `re.search(r"(.)\1{5,}|(\S+\s)\2{3,}", text)` **ou** razão `len(set(text)) / len(text) < 0.15` para `len(text) >= 30`. Aplicado em `prepare_dataset.build_dataset` a todas as categorias.
- Teste: `"rochedo . . . . . . . ."` → `True`; `"E-mail : ssrsrsrsrs"` → `True`; texto normal de 3 frases → `False`.
- Aceite: 0 linhas degeneradas nas 37 detectadas hoje (verificar por `id`).

**C5. Deduplicação antes de embaralhar/limitar/dividir** — `src/prepare_dataset.py::build_dataset`: novo passo `_dedupe_examples(examples)` após `_dedupe_against_eval` e **antes** de `rng.shuffle`, removendo duplicatas por tripla normalizada `(instruction, input, output)` e, em seguida, por par `(instruction, input)` (mantém a primeira ocorrência, determinístico). `split_train_validation` fica igual; como a deduplicação acontece antes, não há tripla compartilhada.
- Teste: 3 cópias da mesma tripla → 1; mesmo par com saídas diferentes → 1; teste de contrato novo `test_no_overlap_between_train_and_validation` sobre os arquivos gerados.
- Aceite: 0 triplas excedentes no treino; 0 compartilhadas com validação. **Pré-requisito de D1** (a validação passa a ser usada de verdade).

**C6. Semente autoral para as 4 classes do teste** — `data/seed/classification_4class.jsonl`, `source: "manual"`, `task_category: "classification"`, instrução no mesmo molde do teste ("Classifique a mensagem como reclamação, dúvida, elogio ou solicitação") com a mensagem em `input`, saída exatamente um dos 4 rótulos em minúsculas. Meta: ≥ 30 mensagens por classe (≥ 120), escritas por Você, **nenhuma copiada ou parafraseada dos 16 prompts de avaliação**. `prepare_dataset` ganha `--seed-dir data/seed` e carrega tudo que houver lá após os filtros, passando pelos mesmos `validate_instruction_example`, dedupe contra eval (C5/`_dedupe_against_eval`) e cap.
- `data-model.md`: `source` passa a admitir `manual`; nota de licença (dados do autor).
- Teste: contrato — nenhuma linha de `data/seed/*` tem `(instruction, input)` igual a um prompt de avaliação; distribuição de rótulos com no máximo 40% em uma classe.
- Aceite: v3 responde ≥ 3 rótulos distintos nos 16 prompts (v2 respondeu 1 rótulo válido). Isso é medido no teste congelado **após** o treino, não usado para escolher configuração.

**C7. Relatório de preparação** — `prepare_dataset.main` imprime e grava `data/dataset_report.md`: contagem por categoria antes/depois de cada filtro, número descartado por motivo (regex de exclusão, degenerado, duplicata, sem input, overlap com eval), e SHA256 de `train.jsonl`/`validation.jsonl`. Se qualquer categoria ficar com < 350 exemplos, o script avisa em stderr (não falha) — é o gatilho para Você decidir ampliar a fonte daquela categoria antes de treinar.
- Estimativa pós-limpeza: gramática ≈ 610, reescrita ≈ 880, resumo ≈ 890, simplificação ≈ 345, classificação ≈ 450 + 120 (C6) → ≈ 3.300 no total, ainda dentro dos 3.000–5.000 de FR-002.

### D. Treinador (Agente 3) — `src/train_qlora.py`

**D1. Usar a validação.** Novo argumento `--validation data/validation.jsonl` (obrigatório). `SFTConfig` recebe `eval_strategy="epoch"`, `per_device_eval_batch_size=training.batch_size`, `load_best_model_at_end=True`, `metric_for_best_model="eval_loss"`, `greater_is_better=False`, `save_total_limit=2`. O adapter salvo passa a ser o de menor `eval_loss`, não o da última época. `trainer_state.json` (já gravado pelo `Trainer`) documenta a curva.
- Teste: `_run_training` com `SFTTrainer` mockado — verificar `eval_dataset` não-nulo e os campos do `SFTConfig`.
- Depende de C5 (sem sobreposição treino/validação).

**D2. Perda apenas na resposta.** Nova chave `training.completion_only_loss: true` em `configs/train.yaml` (default `false` = comportamento do v2, mantém reprodutibilidade). Quando `true`, o dataset vai no formato prompt-completion: `{"prompt": format_prompt(instr, input), "completion": output}` — o `trl` 1.13.0 então calcula perda só na completion (`completion_only_loss=None` resolve para `True` nesse formato). EOS: verificado no código do `trl` instalado — `SFTTrainer` anexa `eos_token` à `completion` automaticamente (função interna `add_eos`, tanto para `text` quanto para `completion`), então o modelo continua aprendendo a parar; nada a fazer manualmente.
- Teste: com a flag, as linhas do dataset têm chaves `prompt`/`completion` e `dataset_text_field` não é passado; sem a flag, o caminho `text` atual permanece.

**D3. Manifesto da execução.** Novo `src/run_manifest.py::write_manifest(run_dir, config, dataset_paths, extra)` grava `adapters/<run-id>/run_manifest.json`: config completa, SHA256 do `train.jsonl`/`validation.jsonl`, `git rev-parse HEAD`, versões de `torch/transformers/peft/trl/bitsandbytes`, revisão do modelo-base (`huggingface_hub.model_info(...).sha`), flag de formato (A1/D2), `max_length`. `src/evaluate.py` grava o análogo `eval/results/<run-id>.manifest.json` (config de inferência, `--prompt-format`, adapter e seu manifesto). É o que a revisão pede em "registrar configuração… um fator por vez".
- Teste: manifesto contém as chaves esperadas; SHA256 bate com o arquivo.

**D4. Limpeza.** Remover `formatted = [...]  # noqa: F841` em `train()` (código morto).

**D5. (Só após v3b, se necessário) Preparação k-bit.** Chave `training.gradient_checkpointing: false` e chamada a `peft.prepare_model_for_kbit_training(model, use_gradient_checkpointing=...)` antes de `get_peft_model` — faz o cast de layer norms/embeddings para fp32 e habilita checkpointing, que o `SFTTrainer` 1.13.0 não faz. Rodar como execução separada, medindo VRAM e `eval_loss`; não empacotar com outras mudanças.

### E. Geração (Agente 2) — `src/evaluate.py`, só depois de D

**E1.** `--inference-config <yaml>` (default `configs/inference.yaml`) para comparar `repetition_penalty=1.3`/`no_repeat_ngram_size=3` com valores menos restritivos (`1.1`/`0`). Copiar trechos literais é necessário em correção e resumo, e `no_repeat_ngram_size=3` proíbe repetir qualquer trigrama da **entrada** — hipótese plausível para as trocas de conteúdo, mas não comprovada. Comparar no **conjunto de desenvolvimento** (E2), não no teste congelado.

**E2.** Conjunto de desenvolvimento: `data/dev/dev_prompts.jsonl` — 10 exemplos por categoria amostrados de `validation.jsonl` limpa (têm `output` de referência), no formato `EvaluationPrompt`, `grading_method: manual_review`. Serve para E1, D5 e qualquer ajuste de hiperparâmetro; o teste congelado só é usado uma vez por candidato final.

## 3. Sequência de execução

| Passo | O quê | Quem | Custo | Saída / decisão |
|---|---|---|---|---|
| 1 | A1–A3, B1–B2 (PRs) | Ag. 2 | ~meio dia | ferramentas prontas, 82+ testes verdes |
| 2 | E1: v2 com `--prompt-format split` + grading cego | Você | ~3 min GPU + 88 notas | mede o peso do formato (§2 A, decisão) |
| 3 | Re-avaliação cega das 4 execuções (`--interleave`), `report.py` | Você | ~350 notas | tabela honesta (média **e** taxa de nota 1) para o `MODEL_CARD.md` |
| 4 | C1–C5, C7 (PRs); C6 (dados autorais) | Ag. 1/2, Você | ~meio dia + 1–2 h de escrita | `data/dataset_report.md`; commit do novo `train.jsonl`/`validation.jsonl` |
| 5 | D1, D3, D4 (PRs) | Ag. 3 | ~2 h | treinador com validação e manifesto |
| 6 | **`qlora-v3a`**: dados limpos, treinador **igual ao v2** (perda total, 3 épocas, r16) | Você | ~10–15 min GPU | isola o efeito dos dados |
| 7 | D2 (PR) → **`qlora-v3b`**: dados limpos + perda na resposta + checkpoint por `eval_loss` | Ag. 3, Você | ~10–15 min GPU | isola o efeito do objetivo |
| 8 | Avaliar v3a e v3b no teste congelado (mesmo formato decidido no passo 2), grading cego, `report.py` | Você | ~180 notas | comparação v2 × v3a × v3b × oficial |
| 9 | Só se v3b ficar abaixo do alvo: D5, E1/E2, `target_modules: all-linear` — **uma por execução** | Ag. 3, Você | ~15 min GPU cada | |

**Critério de sucesso do plano (não de SC-002):** no passo 8, v3b deve mostrar (a) ≥ 3 rótulos distintos em classificação, (b) taxa de nota 1 no grupo A ≥ 20% (v2: 8,75%), (c) nenhuma categoria com média abaixo do v2, (d) grupo B sem queda > 10% relativa ao v2. Se (c) ou (d) falharem, o objetivo de perda (D2) é suspeito e v3a passa a ser o candidato.

## 4. Dependências entre itens

- C5 → D1 (validação só serve como `eval_dataset` sem sobreposição).
- A1 → D2 (o prompt do formato prompt-completion vem do formatador compartilhado).
- A2/A3 → passo 2 → decisão de formato → passos 6–8.
- B1/B2 → passos 3 e 8.
- C6 exige os prompts de avaliação já com `instruction`/`input` separados (A2) para o teste de contrato de não-sobreposição ser exato.

## 5. Riscos

- **Volume por categoria cai** (simplificação ≈ 345). Mitigação: C7 avisa; alternativa é ampliar o regex de simplificação com `\bem linguagem (simples|acessível)\b|\bpara (uma )?criança\b|\bem palavras simples\b`, verificando contagem e precisão antes de aceitar (mesmo método usado no v2 para gramática).
- **Grading cego ainda é de um único revisor**; a taxa de nota 1 é menos sensível a generosidade do que a média com crédito parcial, por isso as duas vão para o relatório.
- **Dados autorais (C6) enviesam para o domínio de atendimento** — é intencional (é o domínio do teste), mas o `MODEL_CARD.md` precisa dizer isso.

## 6. Decisão pendente (Você)

Publicar o v2 agora (Fase 6 da 001, com o `MODEL_CARD.md` preenchido pelas tabelas de B2, deixando explícito média × taxa de nota 1 e o colapso em classificação) **ou** adiar a publicação até o v3b. Este plano funciona nos dois casos; a diferença é só se o `MODEL_CARD.md` recebe os números do v2 ou do v3.
