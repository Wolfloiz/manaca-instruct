# Revisão do baseline — 2026-09-15

Arquivo: `baseline.jsonl`; execução: `baseline`; modelo: `manaca-1b-base`.

**Proveniência:** revisão humana feita pelo usuário, com o assistente de IA (Codex) usado apenas para facilitar o processo (execução do `review_cli`, organização/formatação dos resultados) — a IA não decidiu as notas. O campo `grading_method: manual_review` reflete corretamente a natureza da avaliação. As 71 notas pendentes foram preenchidas com decisões individuais explícitas do usuário. As 33 notas preexistentes foram preservadas.

## Critério aplicado

- **1:** cumpre a tarefa, preserva o sentido e fornece uma resposta correta e pertinente como um todo.
- **0,5:** contém uma resposta central aproveitável, mas apresenta desvios, incompletude ou conteúdo adicional problemático.
- **0:** não executa a tarefa ou apresenta erro central que compromete a resposta. Apenas mencionar o tema não basta.

Foi considerada a saída inteira, sem cortar trechos ruins. Em reescrita, resumo e simplificação, a fidelidade ao texto e a execução da transformação solicitada são essenciais. Nas perguntas gerais, um núcleo correto e reconhecível pode receber crédito parcial mesmo quando a continuação é inadequada.

## Resultado completo

| Categoria | Exemplos | Nota 1 | Nota 0,5 | Nota 0 | Média das notas | Pendentes |
|---|---:|---:|---:|---:|---:|---:|
| Correção gramatical | 16 | 0 | 0 | 16 | 0.00% | 0 |
| Classificação | 16 | 0 | 0 | 16 | 0.00% | 0 |
| Reescrita | 16 | 0 | 0 | 16 | 0.00% | 0 |
| Resumo | 16 | 0 | 0 | 16 | 0.00% | 0 |
| Simplificação | 16 | 0 | 0 | 16 | 0.00% | 0 |
| Conhecimentos gerais (grupo B) | 24 | 0 | 8 | 16 | 16.67% | 0 |

A média atribui peso 0,5 às respostas parciais; não é a porcentagem de respostas plenamente corretas. O grupo B obteve 4 pontos em 24 (16,67%), com oito respostas parciais e nenhuma plenamente correta. As cinco categorias do grupo A ficaram com média zero. A qualidade desta execução é insuficiente para uso como assistente de instruções: predominam desvios de assunto e falhas em executar a tarefa. O registro pode servir de comparação com execuções posteriores nas mesmas condições. Esta revisão não mede ganho após treino nem esquecimento; ambos exigem os resultados pós-treinamento.

## Justificativas das notas preenchidas

| ID | Nota | Justificativa |
|---|---:|---|
| grupo_a-rewriting-002 | 0 | Mantém linguagem informal e responde à situação em vez de reescrever o aviso ao cliente; depois desvia do assunto. |
| grupo_a-rewriting-003 | 0 | Produz anúncios imobiliários, sem reformular o pedido de envio ainda hoje. |
| grupo_a-rewriting-004 | 0 | Gera exercícios e notícias, sem formular o cancelamento solicitado. |
| grupo_a-rewriting-005 | 0 | Gera símbolos, CSS e textos desconexos; não expressa a urgência profissionalmente. |
| grupo_a-rewriting-006 | 0 | Oferece ajuda com um jogo e muda de assunto; não reformula o pedido de verificação. |
| grupo_a-rewriting-007 | 0 | Dá conselhos sobre uma tarefa escolar, sem reformular a reclamação e o pedido de desculpas. |
| grupo_a-rewriting-008 | 0 | Responde que aceita, alterando o interlocutor e o sentido; não reformula a saudação e a consulta. |
| grupo_a-rewriting-009 | 0 | Gera exercício de física e notícia, sem reformular a solicitação de ajuda por falta de tempo. |
| grupo_a-rewriting-010 | 0 | Elogia um trabalho e fala de música; não comunica a necessidade de corrigir um problema. |
| grupo_a-rewriting-011 | 0 | Instrui como escrever uma pergunta e muda de assunto; não reformula a condição de rapidez. |
| grupo_a-rewriting-012 | 0 | Gera perguntas pessoais e textos de blog, sem cobrar a resposta ao e-mail. |
| grupo_a-rewriting-013 | 0 | Conversa sobre um jogo, sem propor a reunião para concluir o assunto. |
| grupo_a-rewriting-014 | 0 | Gera símbolos e fragmentos incoerentes, sem reformular a despedida e a disponibilidade. |
| grupo_a-rewriting-015 | 0 | Gera exercício de física e notícia, sem reformular a solicitação de confirmação. |
| grupo_a-rewriting-016 | 0 | Responde negativamente e fala de aula; não propõe remarcar para a semana seguinte. |
| grupo_a-summarization-001 | 0 | Não resume o incidente do aplicativo; gera explicação lexical e relato sobre faculdade. |
| grupo_a-summarization-002 | 0 | Comenta genericamente mobilidade e introduz bicicletas elétricas; omite os fatos essenciais e excede duas frases. |
| grupo_a-summarization-003 | 0 | Substitui sensores em drones por câmeras e monitoramento de pessoas; não apresenta um resumo fiel. |
| grupo_a-summarization-004 | 0 | Gera explicação lexical e dicas de fotografia, sem os resultados financeiros. |
| grupo_a-summarization-005 | 0 | Não aborda o estudo sobre pausas e produtividade; produz texto sem relação com a fonte. |
| grupo_a-summarization-006 | 0 | Não resume a conquista do campeonato e seus fatores; gera explicação lexical e outros eventos esportivos. |
| grupo_a-summarization-007 | 0 | Não resume o incidente do aplicativo; gera explicação lexical, obras e texto administrativo. |
| grupo_a-summarization-008 | 0 | Emite opinião sobre interesses regionais e empresariais, sem resumir as medidas e valores do plano. |
| grupo_a-summarization-009 | 0 | Gera símbolos, atribuições e notícia de evento escolar; não resume a pesquisa em uma frase. |
| grupo_a-summarization-010 | 0 | Gera explicação lexical e reunião escolar, sem o ponto principal dos resultados financeiros. |
| grupo_a-summarization-011 | 0 | Descreve obras municipais, sem abordar o estudo sobre pausas e produtividade. |
| grupo_a-summarization-012 | 0 | Gera explicação lexical e conteúdo de maquiagem, sem produzir a manchete solicitada. |
| grupo_a-summarization-013 | 0 | Fala de alterações de CSS e maquiagem; não resume o incidente técnico e a correção. |
| grupo_a-summarization-014 | 0 | Acusa genericamente planos de arrecadação e muda de assunto; não apresenta o essencial do plano de mobilidade. |
| grupo_a-summarization-015 | 0 | Troca qualidade da água por nível da água e inventa precisão milimétrica e uso de IA; excede 30 palavras. |
| grupo_a-summarization-016 | 0 | Gera explicação lexical e notícia escolar, sem preservar os dados financeiros relevantes. |
| grupo_a-simplification-001 | 0 | Interpreta implementação como programação e muda de assunto; não comunica que será feita depois. |
| grupo_a-simplification-002 | 0 | Gera exercício e notícia, sem comunicar que a solicitação deve ser encaminhada no prazo. |
| grupo_a-simplification-003 | 0 | Discute gramática e gera exercícios, sem pedir que as pessoas cheguem com antecedência. |
| grupo_a-simplification-004 | 0 | Afirma que nada pode ser feito e gera exercício; não explica a formalização da discordância. |
| grupo_a-simplification-005 | 0 | Comenta a pergunta e lista vagas, sem explicar que a falha do sistema prejudicou a operação. |
| grupo_a-simplification-006 | 0 | Gera relato pessoal, sem solicitar a correção dos erros no cadastro. |
| grupo_a-simplification-007 | 0 | Nega a existência de obrigações, invertendo o sentido da cláusula original. |
| grupo_a-simplification-008 | 0 | Gera explicação lexical e exercícios, sem explicar que o silêncio será entendido como concordância. |
| grupo_a-simplification-009 | 0 | Inventa relatórios, alunos, datas e regras escolares; não preserva a instrução sobre cumprir o cronograma. |
| grupo_a-simplification-010 | 0 | Nega alteração e discute questões empresariais, sem comunicar as mudanças aos interessados. |
| grupo_a-simplification-011 | 0 | Dá orientação sobre aguardar decisão judicial, sem informar o envio dos documentos anexos. |
| grupo_a-simplification-012 | 0 | Gera solicitação de modelo de redação e relato de feira, sem disponibilizar o canal para dúvidas. |
| grupo_a-simplification-013 | 0 | Acrescenta exigência de análise de viabilidade e jargão; não simplifica a execução posterior. |
| grupo_a-simplification-014 | 0 | Gera símbolos e notícias, sem preservar o envio tempestivo da solicitação. |
| grupo_a-simplification-015 | 0 | Fala de fotografia e marketing, sem pedir o comparecimento com antecedência. |
| grupo_a-simplification-016 | 0 | Introduz análise judicial e notícia, sem explicar o registro formal da discordância. |
| grupo_b-001 | 0 | A explicação central generaliza indevidamente a aprendizagem da máquina e é seguida de texto desconexo. |
| grupo_b-002 | 0.5 | Responde Brasília corretamente, mas continua com turismo e textos de blog sem relação com a pergunta. |
| grupo_b-003 | 0 | Não apresenta uma curiosidade sobre o Atlântico; gera pergunta sobre peixes e conteúdo de fotografia. |
| grupo_b-004 | 0.5 | Inclui a ideia de sentir falta de alguém ou algo, mas restringe o sentimento a sofrimento e desvia para outros assuntos. |
| grupo_b-005 | 0 | Confunde conceitos centrais da fotossíntese e não oferece uma descrição correta do processo. |
| grupo_b-006 | 0 | Não distingue clima e tempo meteorológico; interpreta tempo como momento presente e muda de assunto. |
| grupo_b-007 | 0 | Atribui a cor do céu a uma explicação física e química incorreta, seguida de notícia sem relação. |
| grupo_b-008 | 0 | Não define metáfora nem dá um exemplo; gera exercícios sobre regência e notícia. |
| grupo_b-009 | 0.5 | Menciona as quatro estações, mas mistura perguntas, descrições climáticas inconsistentes e repetições; não entrega uma lista clara. |
| grupo_b-010 | 0 | Gera um exercício com informações contraditórias sobre a Amazônia, sem uma explicação breve e confiável. |
| grupo_b-011 | 0 | Mistura preços, demanda e dinheiro com relações incoerentes, sem definir inflação de forma correta e simples. |
| grupo_b-012 | 0.5 | Apresenta benefícios pertinentes no início, mas excede os três pedidos e inclui alegações e textos adicionais que prejudicam a resposta. |
| grupo_b-013 | 0.5 | Define algoritmo como sequência de instruções, mas emenda conteúdo técnico confuso e uma notícia desconexa. |
| grupo_b-014 | 0 | Não estabelece a diferença solicitada e inclui erros centrais sobre vírus e transmissão de doenças. |
| grupo_b-015 | 0 | Não explica o efeito estufa; produz afirmações e exercícios desconexos sobre ozônio e gases. |
| grupo_b-016 | 0 | Mistura colonização portuguesa e domínio espanhol de forma incorreta, sem um relato histórico confiável. |
| grupo_b-017 | 0.5 | Apresenta a ideia central de poder popular e representação, mas acrescenta afirmações históricas problemáticas e notícia desconexa. |
| grupo_b-018 | 0 | Confunde reciclagem com retirada e descarte de resíduos; comentários ambientais não resolvem a definição solicitada. |
| grupo_b-019 | 0 | Define continente como parte do planeta com grande quantidade de água e muda de assunto, sem responder corretamente. |
| grupo_b-020 | 0 | Atribui o bombeamento ao sangue, sem identificar corretamente a função do coração, e continua com conteúdo desconexo. |
| grupo_b-021 | 0 | Não descreve o alinhamento responsável pelo eclipse; substitui a explicação por fenômenos sem relação e afirmações incoerentes. |
| grupo_b-022 | 0 | Confunde galáxia e universo e gera um exercício desconexo; não identifica adequadamente a Via Láctea. |
| grupo_b-023 | 0.5 | Menciona tecnologia fotovoltaica, um exemplo pertinente, mas formula novas perguntas e termina em caracteres incoerentes. |
| grupo_b-024 | 0.5 | Apresenta uma definição pertinente de desenvolvimento sustentável, mas continua com notícias sem relação com a pergunta. |

## Verificação

- 104 registros validados contra o esquema; nenhum `score` pendente.
- Somente os 71 campos `score` anteriormente nulos foram alterados; demais campos e ordem preservados.
- As 32 notas automáticas e a nota preexistente de `grupo_a-rewriting-001` foram preservadas.
- SHA-256 do arquivo antes da revisão: `3f462419e51c90e2495d66330f45d69effffd342834a0762d28bcef080a5664c`.
- SHA-256 do arquivo após a revisão: `633416a44adb0fb7678b869ee64af4d2a1eee1eb8b4a58f271baf7a37345fbab`.
