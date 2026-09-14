from src.dataset_filters.open_ended_tasks import filter_open_ended_tasks
from src.schema_validation import validate_instruction_example

RAW_ROWS = [
    {"instruction": "Simplifique o texto a seguir.", "context": "A implementação supracitada deverá ser realizada posteriormente.", "output": "A implementação mencionada deverá ser feita depois."},
    {"instruction": "Resuma o texto abaixo.", "context": "texto longo sobre um assunto qualquer...", "output": "resumo curto"},
    {"instruction": "Classifique a mensagem como reclamação, dúvida, elogio ou solicitação.", "context": "Meu pedido ainda não chegou.", "output": "reclamação"},
    {"instruction": "Corrija o texto.", "context": "ele viajo ontem", "output": "Ele viajou ontem."},  # not this module's category
    {"instruction": "Simplifique isso.", "context": "texto", "output": ""},  # empty output -> dropped
]


def test_filters_only_the_three_owned_categories():
    results = list(filter_open_ended_tasks(RAW_ROWS))
    categories = {r["task_category"] for r in results}
    assert categories == {"simplification", "summarization", "classification"}
    assert len(results) == 3  # rows 0, 1, 2 — row 3 wrong category, row 4 empty output


def test_output_rows_conform_to_instruction_example_schema():
    for row in filter_open_ended_tasks(RAW_ROWS):
        validate_instruction_example(row)


def test_context_field_normalized_to_input():
    results = list(filter_open_ended_tasks(RAW_ROWS))
    simplification_row = next(r for r in results if r["task_category"] == "simplification")
    assert simplification_row["input"] == "A implementação supracitada deverá ser realizada posteriormente."


def test_ids_are_unique_and_source_tagged():
    results = list(filter_open_ended_tasks(RAW_ROWS))
    ids = [r["id"] for r in results]
    assert len(ids) == len(set(ids))
    assert all(r["source"] == "canarim" for r in results)
