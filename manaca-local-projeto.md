# Projeto: Manacá Local — Especialização de um LLM em Português Brasileiro

## 1. Visão geral

A proposta deste projeto é transformar o modelo **Manacá-1B-base** em um pequeno modelo de linguagem especializado em tarefas de português brasileiro, treinado localmente e posteriormente implantado em hardware mais modesto.

Modelo base:

- **Nome:** `menezesbruno/manaca-1b-base`
- **Origem:** Hugging Face
- **Tipo:** modelo causal de linguagem, base, não instruction-tuned
- **Tamanho:** aproximadamente 1,7 bilhão de parâmetros
- **Idioma principal:** português brasileiro
- **Contexto:** até 4096 tokens

O objetivo não é tentar criar um concorrente geral do ChatGPT, mas aproveitar as características do Manacá para construir um modelo pequeno, especializado e eficiente.

A ideia central é criar um **Manacá-Instruct-PT**, capaz de executar instruções em português como:

- corrigir textos;
- melhorar clareza;
- reescrever em diferentes tons;
- resumir;
- simplificar linguagem;
- classificar textos;
- responder perguntas sobre documentos;
- atuar como base de um assistente local em português.

O projeto também serve como laboratório prático para aprender o ciclo completo de desenvolvimento com LLMs:

```text
dataset
   ↓
preparação dos exemplos
   ↓
tokenização
   ↓
supervised fine-tuning
   ↓
QLoRA / LoRA
   ↓
avaliação
   ↓
merge dos adapters
   ↓
quantização
   ↓
GGUF
   ↓
llama.cpp / Ollama
   ↓
API
   ↓
aplicação local
```

---

# 2. Referência oficial do projeto Manacá

Antes de definir o pipeline deste projeto, é importante separar duas coisas:

1. o que faz parte do **projeto oficial do Manacá**;
2. o que será desenvolvido neste projeto como uma **extensão do modelo base**.

O repositório oficial do Manacá está em:

```text
https://github.com/Instituto-IA-LNCC/manaca-1b-base
```

O modelo publicado no Hugging Face está em:

```text
https://huggingface.co/menezesbruno/manaca-1b-base
```

## 2.1 O que o projeto oficial fornece

O projeto oficial documenta principalmente:

- preparação e construção do corpus;
- treinamento do tokenizer;
- pré-processamento para Megatron-LM;
- pré-treinamento do modelo;
- avaliação;
- ambiente reproduzível com Docker;
- comandos de automação com `make`.

O fluxo oficial é conceitualmente:

```text
corpus
   ↓
tokenizer
   ↓
pré-processamento
   ↓
Megatron-LM
   ↓
pré-treinamento
   ↓
avaliação
   ↓
Manacá-1B-base
```

Esse pipeline é importante como referência técnica, mas não será reproduzido integralmente neste projeto.

O pré-treinamento original trabalha com dezenas de bilhões de tokens e foi pensado para hardware significativamente maior do que uma RTX 5050 de 8 GB.

Portanto:

```text
pré-treinamento completo do zero
                ↓
          NÃO É O OBJETIVO
```

O objetivo será aproveitar os pesos já publicados.

---

## 2.2 Docker e ambiente oficial

O repositório oficial utiliza Docker e Docker Compose para manter os ambientes reproduzíveis.

O projeto oficial contém fluxos separados para:

```text
corpus
tokenizer
pré-treinamento
avaliação
```

Também utiliza comandos `make` para orquestrar diferentes etapas.

Exemplos encontrados na documentação oficial incluem fluxos equivalentes a:

```text
make build-corpus
make tokenizer
make preprocess-megatron
make pretrain
```

No nosso projeto, Docker será opcional na primeira versão.

A prioridade inicial será conseguir iterar rapidamente no TUF Gaming F16 utilizando:

```text
WSL2
  ↓
Ubuntu
  ↓
Python
  ↓
PyTorch
  ↓
Transformers
```

Depois que o pipeline estiver estável, ele poderá ser containerizado para melhorar a reprodutibilidade.

---

## 2.3 Megatron-LM no projeto oficial

O treinamento original utiliza **Megatron-LM**.

Essa tecnologia faz sentido para pré-treinamento distribuído em GPUs maiores e múltiplas GPUs.

Nosso projeto não utilizará Megatron-LM para o primeiro instruction tuning.

A divisão será:

```text
Pipeline oficial
    ↓
Megatron-LM
    ↓
pré-treinamento

Projeto Manacá Local
    ↓
Transformers + PEFT + TRL
    ↓
SFT + QLoRA
```

Essa diferença deve ficar explícita.

**QLoRA, PEFT e TRL são decisões deste projeto, não uma receita oficial dos autores do Manacá.**

---

## 2.4 Instruction tuning não faz parte do modelo base

O Manacá publicado é um **base model**.

Ele não deve ser tratado como se já fosse um chatbot.

O trabalho oficial se concentra no modelo base e sua avaliação.

O instruction tuning é uma etapa posterior e natural:

```text
Manacá-1B-base
       ↓
nosso dataset de instruções
       ↓
SFT
       ↓
QLoRA
       ↓
Manacá-Instruct-PT
```

Essa é justamente a principal contribuição proposta neste projeto.

---

## 2.5 Tokenizer oficial — regra obrigatória do projeto

Um dos pontos mais importantes da documentação oficial é utilizar o tokenizer distribuído junto com o modelo.

O tokenizer deve ser carregado assim:

```python
from transformers import AutoTokenizer

MODEL = "menezesbruno/manaca-1b-base"

tokenizer = AutoTokenizer.from_pretrained(MODEL)
```

Não devemos substituir esse tokenizer por um tokenizer genérico.

O Manacá utiliza normalização de texto e trabalha com lowercase por construção.

Portanto:

```text
tokenizer oficial
      ↓
obrigatório
```

Trocar o tokenizer pode alterar a segmentação dos tokens e degradar o comportamento do modelo.

Essa regra vale para:

- treinamento;
- validação;
- benchmarks;
- inferência;
- geração do dataset tokenizado;
- exportação do modelo.

---

## 2.6 Baseline oficial como referência

Antes de qualquer fine-tuning, o modelo original deve ser executado exatamente com seu tokenizer oficial.

O primeiro baseline será:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

MODEL = "menezesbruno/manaca-1b-base"

tokenizer = AutoTokenizer.from_pretrained(MODEL)

model = AutoModelForCausalLM.from_pretrained(
    MODEL,
    dtype=torch.bfloat16, // torch_dtype está depreciado
    device_map="auto"
)

prompt = "a inteligência artificial no brasil"

inputs = tokenizer(
    prompt,
    return_tensors="pt"
).to(model.device)

output = model.generate(
    **inputs,
    max_new_tokens=100,
    do_sample=False
)

print(
    tokenizer.decode(
        output[0],
        skip_special_tokens=True
    )
)
```

Esse teste servirá como ponto zero do projeto.

---

# 3. O que é oficial e o que é proposto por nós

Para evitar confusão, o projeto será documentado com a seguinte separação.

## Oficial

```text
Manacá-1B-base
tokenizer oficial
arquitetura original
pesos publicados
documentação de pré-treinamento
pipeline de avaliação
Megatron-LM
Docker
scripts oficiais
```

## Proposto neste projeto

```text
dataset instruction-following
SFT
QLoRA
PEFT
TRL
adapters LoRA
Manacá-Instruct-PT
benchmark Base × Instruct
exportação GGUF
implantação no Dell G3
FastAPI
interface
RAG
```

Essa separação também será importante caso o projeto seja publicado no GitHub.

---

# 4. Hardware disponível

O projeto será desenvolvido utilizando dois notebooks com papéis diferentes.

## Máquina principal — ASUS TUF Gaming F16

Esta será a máquina utilizada para desenvolvimento, inferência com GPU e fine-tuning.

Hardware relevante:

- **Notebook:** ASUS TUF Gaming F16
- **GPU:** NVIDIA GeForce RTX 5050 Laptop
- **VRAM:** 8 GB
- **Arquitetura da GPU:** Blackwell
- **Uso principal:** treinamento, QLoRA, inferência CUDA e experimentação

A RTX 5050 de 8 GB é suficiente para trabalhar confortavelmente com um modelo da escala do Manacá.

Como o Manacá tem cerca de 1,7B de parâmetros, seus pesos em FP16/BF16 ficam aproximadamente na faixa de:

```text
1,72 bilhões de parâmetros × 2 bytes
≈ 3,44 GB
```

Isso torna possível executar o modelo inteiro na GPU para inferência.

Para treinamento, porém, o consumo de memória aumenta devido a:

- ativações;
- gradientes;
- estados do otimizador;
- KV cache;
- buffers internos.

Por isso, o método recomendado é **QLoRA**.

---

## Máquina secundária — Dell G3

Esta máquina será usada principalmente para testes de implantação e inferência em hardware mais antigo.

Hardware:

- **Notebook:** Dell G3
- **CPU:** Intel Core i5 de 8ª geração
- **GPU:** NVIDIA GTX 1050
- **RAM:** 32 GB

Uso recomendado:

```text
Dell G3
   ↓
modelo quantizado
   ↓
GGUF
   ↓
llama.cpp ou Ollama
   ↓
inferência local
```

O Dell não será a principal máquina de treinamento.

Ele será utilizado para validar uma parte importante do projeto:

> Um modelo treinado em hardware moderno consegue ser comprimido e implantado em hardware antigo?

Isso torna o projeto mais interessante do ponto de vista técnico e de portfólio.

---

# 5. Objetivo principal

Criar uma versão instruction-tuned do Manacá.

Nome provisório:

```text
Manacá-Instruct-PT
```

Fluxo:

```text
Manacá-1B-base
       ↓
dataset de instruções em português
       ↓
Supervised Fine-Tuning
       ↓
QLoRA
       ↓
Manacá-Instruct-PT
       ↓
avaliação
       ↓
quantização GGUF
       ↓
implantação local
```

---

# 6. Por que fazer instruction tuning

O modelo original é um **base model**.

Isso significa que ele foi treinado principalmente para prever o próximo token.

Por exemplo:

```text
Entrada:

a inteligência artificial no brasil é
```

O modelo continua o texto.

Mas uma entrada como:

```text
Explique o que é inteligência artificial.
```

não necessariamente será tratada como uma instrução da mesma maneira que um modelo de chat faria.

O projeto, portanto, terá como primeiro grande objetivo ensinar o modelo a seguir instruções.

---

# 7. Dataset de treinamento

O dataset deve ser composto por exemplos contendo:

- instrução;
- entrada;
- resposta esperada.

Formato simples:

```json
{
  "instruction": "Corrija gramaticalmente o texto.",
  "input": "os menino foi na escola ontem",
  "output": "Os meninos foram à escola ontem."
}
```

Outro exemplo:

```json
{
  "instruction": "Reescreva o texto de maneira profissional.",
  "input": "fala pro cliente que vai atrasar",
  "output": "Informe ao cliente que haverá um atraso."
}
```

Outro:

```json
{
  "instruction": "Simplifique o texto.",
  "input": "A implementação supracitada deverá ser realizada posteriormente.",
  "output": "A implementação mencionada deverá ser feita posteriormente."
}
```

---

# 8. Categorias do dataset

O treinamento pode começar com aproximadamente cinco grandes categorias.

## 6.1 Correção gramatical

Exemplo:

```text
Instrução:
Corrija o português.

Entrada:
nós vai terminar isso amanhã

Resposta:
Nós vamos terminar isso amanhã.
```

---

## 6.2 Reescrita profissional

```text
Instrução:
Reescreva de maneira profissional.

Entrada:
oi queria saber se vcs resolveram aquele negócio

Resposta:
Olá, gostaria de saber se o problema mencionado já foi solucionado.
```

---

## 6.3 Simplificação

```text
Instrução:
Simplifique o texto.

Entrada:
A referida solicitação deverá ser encaminhada tempestivamente.

Resposta:
A solicitação deve ser enviada dentro do prazo.
```

---

## 6.4 Resumo

```text
Instrução:
Resuma o texto abaixo.

Entrada:
[texto longo]

Resposta:
[resumo]
```

---

## 6.5 Classificação

Exemplo:

```text
Instrução:
Classifique a mensagem como reclamação, dúvida, elogio ou solicitação.

Entrada:
Meu pedido ainda não chegou.

Resposta:
reclamação
```

---

# 9. Evolução futura do dataset

Depois da primeira versão, podem ser adicionadas especializações.

Exemplos:

```text
Manacá-Instruct-PT
        │
        ├── português geral
        ├── português profissional
        ├── atendimento ao cliente
        ├── linguagem jurídica
        ├── linguagem acadêmica
        └── documentos corporativos
```

Também podem ser criados adapters LoRA separados.

Exemplo:

```text
Manacá Base
     │
     ├── LoRA Gramática
     ├── LoRA Jurídico
     ├── LoRA Atendimento
     └── LoRA Acadêmico
```

Isso permite trocar especializações sem precisar manter uma cópia completa do modelo para cada tarefa.

---

# 10. Ambiente recomendado

Na máquina TUF Gaming F16, uma configuração recomendada é:

```text
Windows
   ↓
WSL2
   ↓
Ubuntu
   ↓
Python
   ↓
PyTorch + CUDA
```

Stack principal:

- Python 3.11
- PyTorch
- Transformers
- Accelerate
- PEFT
- TRL
- bitsandbytes
- datasets
- sentencepiece, caso necessário
- Jupyter ou VS Code

Ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

Instalação conceitual:

```bash
pip install torch
pip install transformers
pip install datasets
pip install accelerate
pip install peft
pip install trl
pip install bitsandbytes
```

As versões exatas devem ser definidas no momento da implementação para garantir compatibilidade com a RTX 5050 e o CUDA instalado.

---

# 11. Estrutura sugerida do projeto

```text
manaca-local/
│
├── README.md
│
├── requirements.txt
│
├── configs/
│   ├── train.yaml
│   └── inference.yaml
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── train.jsonl
│   ├── validation.jsonl
│   └── test.jsonl
│
├── notebooks/
│   ├── 01_model_test.ipynb
│   ├── 02_dataset_analysis.ipynb
│   └── 03_training_analysis.ipynb
│
├── src/
│   ├── prepare_dataset.py
│   ├── train_qlora.py
│   ├── inference.py
│   ├── evaluate.py
│   └── merge_adapter.py
│
├── adapters/
│
├── models/
│   ├── merged/
│   └── gguf/
│
├── api/
│   └── main.py
│
└── web/
```

---

# 12. Primeira etapa — executar o modelo original

Antes de treinar qualquer coisa, deve ser criado um baseline.

Objetivo:

> entender exatamente como o Manacá original se comporta.

Exemplo de teste:

```python
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL = "menezesbruno/manaca-1b-base"

tokenizer = AutoTokenizer.from_pretrained(MODEL)

model = AutoModelForCausalLM.from_pretrained(
    MODEL,
    torch_dtype=torch.bfloat16,
    device_map="auto"
)

prompt = "a inteligência artificial no brasil"

inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

output = model.generate(
    **inputs,
    max_new_tokens=100,
    temperature=0.7,
    top_p=0.9,
    do_sample=True
)

print(tokenizer.decode(output[0], skip_special_tokens=True))
```

Nesta fase devem ser registrados:

- VRAM utilizada;
- tempo de carregamento;
- tokens por segundo;
- consumo de RAM;
- qualidade das respostas;
- comportamento com prompts de instrução.

---

# 13. Criar um conjunto de avaliação fixo

Antes do treinamento, deve ser criado um conjunto de prompts que nunca fará parte dos dados de treino.

Exemplo:

```text
01 — Corrija:
"os relatório foi enviado ontem"

02 — Reescreva de maneira formal:
"me manda isso ainda hoje"

03 — Resuma:
[texto]

04 — Simplifique:
[texto complexo]

05 — Classifique:
"Gostaria de solicitar o cancelamento."
```

Esses prompts servirão para comparar:

```text
Manacá Base
      VS
Manacá Fine-Tuned
```

Isso é extremamente importante.

Sem um conjunto de avaliação fixo, fica difícil saber se o treinamento realmente melhorou o modelo.

---

# 14. Formatação dos prompts de treinamento

Pode ser utilizado inicialmente um formato simples:

```text
### Instrução:
{instruction}

### Entrada:
{input}

### Resposta:
{output}
```

Durante inferência:

```text
### Instrução:
Corrija gramaticalmente o texto.

### Entrada:
os documento foi enviado ontem

### Resposta:
```

O modelo então deverá aprender a completar a seção de resposta.

---

# 15. Fine-tuning com QLoRA

QLoRA é a abordagem recomendada para a RTX 5050 de 8 GB.

A lógica é:

```text
modelo original
      ↓
quantização para 4 bits
      ↓
pesos principais congelados
      ↓
pequenos adapters LoRA treináveis
      ↓
treinamento
```

Em vez de atualizar todos os bilhões de parâmetros, apenas uma pequena parte é treinada.

Benefícios:

- redução drástica de VRAM;
- treinamento mais rápido;
- adapters pequenos;
- possibilidade de múltiplas especializações;
- hardware doméstico suficiente.

---

# 16. Configuração inicial de QLoRA

Uma configuração inicial razoável para experimentar:

```text
quantização: 4-bit NF4

LoRA rank:
r = 8 ou 16

LoRA alpha:
16 ou 32

dropout:
0.05

batch size:
1 ou 2

gradient accumulation:
8 a 32

learning rate:
aproximadamente 1e-4 a 2e-4

epochs:
1 a 3
```

Esses valores são pontos de partida.

A configuração real deverá ser ajustada de acordo com:

- tamanho do dataset;
- uso de VRAM;
- estabilidade do treinamento;
- perda de validação;
- qualidade final.

---

# 17. Monitoramento durante o treinamento

Registrar pelo menos:

```text
training loss
validation loss
VRAM
tempo por step
learning rate
tokens processados
```

Também é útil salvar checkpoints.

Exemplo:

```text
checkpoints/
   checkpoint-500/
   checkpoint-1000/
   checkpoint-1500/
```

Assim é possível comparar versões do modelo.

---

# 18. Comparador Base × Fine-Tuned

Uma funcionalidade importante do projeto deve permitir executar o mesmo prompt nos dois modelos.

Exemplo:

```text
Prompt:

Corrija:
"os menino foi para escola"
```

Saída:

```text
┌──────────────────────┬──────────────────────┐
│ Manacá Base          │ Manacá-Instruct     │
├──────────────────────┼──────────────────────┤
│ resposta A           │ Os meninos foram... │
└──────────────────────┴──────────────────────┘
```

Essa comparação tem valor técnico e também é ótima para demonstração de portfólio.

---

# 19. Métricas do projeto

O projeto não deve depender apenas de avaliação subjetiva.

Podem ser utilizadas métricas específicas por tarefa.

Para correção:

- taxa de respostas corretas;
- comparação manual;
- distância de edição.

Para classificação:

- accuracy;
- precision;
- recall;
- F1.

Para resumo:

- avaliação humana;
- ROUGE, se fizer sentido.

Para instruções gerais:

- conjunto de benchmarks internos;
- avaliação humana A/B.

---

# 20. Merge do LoRA

Depois do treinamento, existem duas opções.

## Opção A — manter adapter separado

```text
Manacá Base
   +
LoRA
```

Vantagem:

- arquivo pequeno;
- permite várias especializações.

---

## Opção B — fazer merge

```text
Manacá Base
      +
LoRA
      ↓
modelo final
```

Isso cria uma versão standalone do modelo fine-tuned.

Ela será usada para exportação.

---

# 21. Quantização

Depois de validar o modelo final, ele será convertido para GGUF.

Objetivo:

```text
modelo treinado
      ↓
merge
      ↓
GGUF
      ↓
Q4_K_M
```

A quantização Q4_K_M será o primeiro formato testado.

Também podem ser comparados:

```text
Q4_K_M
Q5_K_M
Q6_K
Q8_0
```

Quanto menor a quantização:

```text
menos memória
mais velocidade
potencial perda de qualidade
```

Quanto maior:

```text
mais memória
potencialmente mais qualidade
```

---

# 22. Implantação no Dell G3

O Dell será utilizado para comprovar que o modelo final consegue rodar em hardware mais antigo.

Fluxo:

```text
Manacá-Instruct-PT
        ↓
GGUF Q4_K_M
        ↓
Dell G3
        ↓
llama.cpp
        ↓
CPU + possível GPU offload
```

Exemplo de execução:

```bash
llama-cli \
  -m manaca-instruct-pt-q4_k_m.gguf \
  -p "Corrija o texto: os documento chegou ontem" \
  -n 100 \
  -c 4096
```

A GTX 1050 poderá ser usada para offload caso seja vantajoso.

Exemplo conceitual:

```bash
-ngl 10
```

ou:

```bash
-ngl 20
```

O valor ideal dependerá da quantidade real de VRAM da GTX 1050.

---

# 23. Benchmark entre as máquinas

Uma etapa interessante será comparar os dois notebooks.

Tabela esperada:

| Métrica | TUF F16 | Dell G3 |
|---|---:|---:|
| GPU | RTX 5050 | GTX 1050 |
| Modelo | FP16/BF16 | GGUF Q4 |
| Tempo de carregamento | medir | medir |
| Tokens/s | medir | medir |
| RAM | medir | medir |
| VRAM | medir | medir |
| Contexto testado | medir | medir |

Isso transforma o projeto também em um estudo de implantação eficiente de LLMs.

---

# 24. API local

Depois do modelo estar funcionando, deve ser criada uma API.

Stack:

```text
FastAPI
```

Fluxo:

```text
Aplicação
   ↓
POST /generate
   ↓
FastAPI
   ↓
modelo local
   ↓
resposta JSON
```

Exemplo conceitual:

```json
POST /generate

{
  "instruction": "Corrija o texto.",
  "input": "os relatório foi enviado ontem"
}
```

Resposta:

```json
{
  "output": "Os relatórios foram enviados ontem."
}
```

---

# 25. Interface

Depois da API, pode ser criada uma interface simples.

Opções:

- Streamlit;
- Gradio;
- React;
- Next.js.

Para a primeira versão:

```text
Gradio ou Streamlit
```

são suficientes.

Interface:

```text
┌─────────────────────────────────────┐
│ Manacá Local                       │
├─────────────────────────────────────┤
│ Tarefa: [Correção ▼]               │
│                                     │
│ Texto:                              │
│ ┌─────────────────────────────────┐ │
│ │ os documento chegou ontem      │ │
│ └─────────────────────────────────┘ │
│                                     │
│            [Executar]               │
│                                     │
│ Resultado:                          │
│ ┌─────────────────────────────────┐ │
│ │ Os documentos chegaram ontem. │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

---

# 26. Segunda fase — RAG

Depois que o modelo instruction-tuned estiver funcionando bem, será adicionada uma camada de documentos.

Objetivo:

```text
PDF
 ↓
extração de texto
 ↓
chunks
 ↓
embeddings
 ↓
banco vetorial
 ↓
busca
 ↓
contexto
 ↓
Manacá
 ↓
resposta
```

Stack possível:

- PyMuPDF;
- sentence-transformers;
- FAISS ou Qdrant;
- FastAPI.

---

# 27. Assistente de documentos

Exemplo de pergunta:

```text
Qual é o prazo para solicitação de férias?
```

Sistema:

```text
Pergunta
   ↓
embedding
   ↓
busca vetorial
   ↓
trecho relevante
   ↓
prompt
   ↓
Manacá
```

Resposta esperada:

```text
Segundo a política de férias, a solicitação deve ser feita
com pelo menos 30 dias de antecedência.

Fonte: politica_ferias.pdf
Página: 7
```

A resposta deve sempre que possível indicar sua fonte.

---

# 28. Arquitetura final

```text
                      ┌───────────────────┐
                      │ Interface Web     │
                      └─────────┬─────────┘
                                │
                         ┌──────▼──────┐
                         │ FastAPI     │
                         └──────┬──────┘
                                │
                    ┌───────────▼───────────┐
                    │ Manacá-Instruct-PT    │
                    └───────────┬───────────┘
                                │
               ┌────────────────┴────────────────┐
               │                                 │
       tarefas de texto                    documentos
               │                                 │
        correção/resumo                         RAG
        reescrita/etc.                           │
                                                 ↓
                                             FAISS/Qdrant
```

---

# 29. Divisão de responsabilidades entre os computadores

## TUF Gaming F16

```text
RTX 5050 8 GB
      │
      ├── desenvolvimento
      ├── dataset
      ├── PyTorch
      ├── inferência CUDA
      ├── QLoRA
      ├── treinamento
      ├── avaliação
      └── merge
```

---

## Dell G3

```text
i5 8ª geração
GTX 1050
32 GB RAM
      │
      ├── GGUF
      ├── llama.cpp
      ├── testes CPU
      ├── GPU offload
      ├── servidor local
      └── benchmark
```

---


# 30. Avaliação pós-fine-tuning e catastrophic forgetting

O projeto deve medir não apenas se o modelo ficou melhor em seguir instruções.

Também é necessário verificar se ele perdeu capacidades que já possuía antes do fine-tuning.

Esse fenômeno é conhecido como:

```text
catastrophic forgetting
```

Uma forma simples de visualizar:

```text
Manacá Base
    │
    │ possui capacidades linguísticas originais
    ▼
Instruction tuning
    │
    ├── pode melhorar execução de instruções
    │
    └── pode degradar habilidades anteriores
```

Por isso, a avaliação terá dois grupos.

## Grupo A — novas capacidades

Testes criados especificamente para o modelo instruct:

- correção gramatical;
- reescrita;
- resumo;
- simplificação;
- classificação;
- seguimento de instruções;
- formato de resposta.

## Grupo B — capacidades originais

Sempre que possível, reutilizar avaliações e tarefas próximas às usadas pelo projeto oficial.

O objetivo é comparar:

```text
                 Base        Instruct
Português         medir         medir
Completions       medir         medir
Instruções        medir         medir
Classificação     medir         medir
Resumo            medir         medir
```

O resultado desejado é:

```text
ganho forte em instruction following
          +
perda mínima nas capacidades do modelo base
```

Se houver degradação significativa, possíveis ações incluem:

- reduzir learning rate;
- diminuir número de epochs;
- melhorar diversidade do dataset;
- inserir exemplos de continuação de texto;
- ajustar LoRA rank;
- reduzir quantidade de módulos treinados;
- misturar dados de domínio geral ao SFT.

---

# 31. Estratégia de avaliação comparativa

O modelo deve ser avaliado em pelo menos três momentos:

```text
checkpoint 0
Manacá Base

checkpoint 1
primeiro LoRA

checkpoint final
Manacá-Instruct-PT
```

Os mesmos prompts devem ser aplicados aos três.

Cada resultado deve registrar:

```text
prompt
modelo
resposta
latência
tokens gerados
tokens por segundo
avaliação
```

Uma tabela de resultados poderá ser mantida em CSV ou JSONL.

Exemplo:

```json
{
  "id": "grammar_001",
  "task": "grammar",
  "model": "manaca-instruct-v1",
  "prompt": "Corrija: os documento chegou ontem",
  "expected": "Os documentos chegaram ontem.",
  "output": "Os documentos chegaram ontem.",
  "score": 1
}
```

Esse formato permitirá automatizar futuras comparações.

---

# 32. Roadmap

## Fase 1 — Baseline

- instalar ambiente;
- baixar Manacá;
- executar na RTX 5050;
- testar prompts;
- medir desempenho.

Resultado:

```text
Manacá Base funcionando localmente.
```

---

## Fase 2 — Dataset

- definir tarefas;
- criar exemplos;
- limpar dataset;
- dividir treino/validação/teste.

Resultado:

```text
dataset-v1.jsonl
```

---

## Fase 3 — Primeiro QLoRA

- carregar modelo em 4 bits;
- configurar LoRA;
- executar fine-tuning;
- salvar adapter.

Resultado:

```text
manaca-instruct-lora-v1
```

---

## Fase 4 — Avaliação

Comparar:

```text
Base
vs
Fine-Tuned
```

Avaliar:

- correção;
- instruções;
- resumo;
- reescrita;
- classificação.

---

## Fase 5 — Iteração

- corrigir dataset;
- adicionar exemplos difíceis;
- ajustar hiperparâmetros;
- treinar v2.

---

## Fase 6 — Merge

Criar:

```text
manaca-instruct-pt-v1
```

---

## Fase 7 — GGUF

Converter e quantizar:

```text
manaca-instruct-pt-q4_k_m.gguf
```

---

## Fase 8 — Dell G3

Executar modelo quantizado.

Medir:

- RAM;
- VRAM;
- tokens/s;
- latência.

---

## Fase 9 — API

Criar FastAPI.

Endpoints:

```text
/generate
/health
/model-info
```

---

## Fase 10 — Interface

Criar interface local.

---

## Fase 11 — RAG

Adicionar:

- PDF;
- embeddings;
- FAISS/Qdrant;
- citações de fontes.

---

# 33. Resultado final esperado

Ao final do projeto haverá:

```text
1. Manacá base funcionando localmente
2. dataset próprio de instruction tuning
3. adapter QLoRA
4. Manacá-Instruct-PT
5. benchmark Base × Fine-Tuned
6. versão GGUF
7. execução no Dell G3
8. API REST
9. interface web
10. sistema opcional de RAG
```

---

# 34. Valor técnico do projeto

Este projeto envolve várias áreas relevantes de IA moderna:

- LLMs;
- Transformers;
- tokenização;
- supervised fine-tuning;
- LoRA;
- QLoRA;
- quantização;
- CUDA;
- PyTorch;
- avaliação de modelos;
- inferência local;
- GGUF;
- llama.cpp;
- APIs;
- RAG;
- embeddings;
- bancos vetoriais.

Em vez de simplesmente instalar um modelo pronto, o projeto demonstra todo o ciclo:

```text
modelo base
   ↓
especialização
   ↓
avaliação
   ↓
otimização
   ↓
implantação
```

---

# 35. Principal hipótese do projeto

A hipótese central pode ser apresentada da seguinte forma:

> Um modelo relativamente pequeno, treinado especificamente para português brasileiro e posteriormente especializado através de QLoRA, pode executar tarefas linguísticas úteis localmente e ser implantado em hardware doméstico de baixo custo.

O TUF Gaming F16 será utilizado para treinamento e desenvolvimento.

O Dell G3 será utilizado para demonstrar implantação eficiente.

---

# 36. Possíveis nomes

Alguns nomes possíveis:

```text
Manacá Local
Manacá Studio
Manacá Instruct
Manacá PT
Manacá Lab
Manacá Copilot
Manacá Português
```

Um bom nome inicial para o repositório seria:

```text
manaca-local-lab
```

E para o modelo:

```text
manaca-instruct-pt
```

---

# 37. Primeira meta prática

A primeira meta deve ser pequena.

Não começar pelo RAG.

Não começar pela interface.

Não começar pela API.

Começar por:

```text
1. carregar o Manacá;
2. rodar na RTX 5050;
3. criar 50 a 100 prompts de avaliação;
4. montar um pequeno dataset;
5. fazer o primeiro QLoRA;
6. comparar Base × Fine-Tuned.
```

Quando essa etapa estiver funcionando, o restante do projeto pode ser construído em cima dela.

---

# 38. Definição de sucesso da versão 1

A versão 1 estará concluída quando for possível executar:

```text
Entrada:

### Instrução:
Corrija gramaticalmente o texto.

### Entrada:
os documento foi enviado ontem

### Resposta:
```

E o modelo especializado responder consistentemente algo próximo de:

```text
Os documentos foram enviados ontem.
```

A partir daí, o projeto deixa de ser apenas um experimento com um modelo baixado e passa a ter um modelo próprio, especializado e mensurável.

---

# Conclusão

O projeto **Manacá Local** utilizará o ASUS TUF Gaming F16 com RTX 5050 como ambiente de desenvolvimento e treinamento, enquanto o Dell G3 com GTX 1050 e 32 GB de RAM servirá como alvo de implantação em hardware mais antigo.

A estratégia principal será:

```text
Manacá Base
    ↓
Dataset PT-BR
    ↓
QLoRA na RTX 5050
    ↓
Manacá-Instruct-PT
    ↓
Avaliação
    ↓
Merge
    ↓
GGUF Q4
    ↓
Dell G3
    ↓
API + aplicação local
```

O foco inicial deve permanecer na especialização do modelo e na avaliação objetiva dos resultados. RAG, API e interface entram posteriormente como extensões do modelo já treinado.

Isso mantém o projeto tecnicamente interessante, executável com o hardware disponível e adequado tanto para aprendizado quanto para demonstração em portfólio.

---

# Referências principais

## Repositório oficial

```text
https://github.com/Instituto-IA-LNCC/manaca-1b-base
```

## Modelo no Hugging Face

```text
https://huggingface.co/menezesbruno/manaca-1b-base
```

Estas referências devem ser consultadas novamente no momento da implementação para confirmar versões, dependências e recomendações atualizadas.
