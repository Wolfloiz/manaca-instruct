from src.prepare_dataset import build_dataset, split_train_validation

RAW_ALPACA = [
    {"instruction": "Corrija o texto a seguir.", "input": "os menino foi na escola", "output": "Os meninos foram à escola."},
    {"instruction": "Reescreva de maneira profissional.", "input": "fala pro cliente que vai atrasar", "output": "Informe ao cliente que haverá um atraso."},
    {"instruction": "Corrija a ortografia.", "input": "ele viajo ontem", "output": "Ele viajou ontem."},
]

RAW_CANARIM = [
    {"instruction": "Simplifique o texto a seguir.", "context": "A implementação supracitada deverá ser realizada posteriormente.", "output": "A implementação mencionada deverá ser feita depois."},
    {"instruction": "Resuma o texto abaixo.", "context": "texto longo...", "output": "resumo curto"},
    {"instruction": "Classifique a mensagem como reclamação, dúvida, elogio ou solicitação.", "context": "Meu pedido ainda não chegou.", "output": "reclamação"},
]


def test_build_dataset_combines_both_sources():
    examples = build_dataset(RAW_ALPACA, RAW_CANARIM, eval_keys=set())
    sources = {ex["source"] for ex in examples}
    assert sources == {"alpaca-pt-br", "canarim"}
    categories = {ex["task_category"] for ex in examples}
    assert categories == {"grammar_correction", "rewriting", "simplification", "summarization", "classification"}


def test_build_dataset_excludes_rows_matching_eval_prompts():
    eval_keys = {("Corrija o texto a seguir. os menino foi na escola", "")}
    examples = build_dataset(RAW_ALPACA, RAW_CANARIM, eval_keys=eval_keys)
    combined_texts = [f"{ex['instruction']} {ex['input']}".strip() for ex in examples]
    assert "Corrija o texto a seguir. os menino foi na escola" not in combined_texts
    # the other 5 examples remain
    assert len(examples) == 5


def test_build_dataset_produces_no_duplicate_ids():
    examples = build_dataset(RAW_ALPACA, RAW_CANARIM, eval_keys=set())
    ids = [ex["id"] for ex in examples]
    assert len(ids) == len(set(ids))


def test_split_train_validation_respects_fraction():
    examples = [{"id": f"x-{i}"} for i in range(100)]
    train, validation = split_train_validation(examples, validation_fraction=0.1)
    assert len(validation) == 10
    assert len(train) == 90
    assert set(ex["id"] for ex in train).isdisjoint(ex["id"] for ex in validation)


def test_split_train_validation_handles_empty_input():
    train, validation = split_train_validation([])
    assert train == []
    assert validation == []
