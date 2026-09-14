from src.dataset_filters.grammar_rewriting import filter_grammar_and_rewriting
from src.schema_validation import validate_instruction_example

RAW_ROWS = [
    {"instruction": "Corrija o texto a seguir.", "input": "os menino foi na escola", "output": "Os meninos foram à escola."},
    {"instruction": "Reescreva de maneira profissional.", "input": "fala pro cliente que vai atrasar", "output": "Informe ao cliente que haverá um atraso."},
    {"instruction": "Resuma o texto a seguir.", "input": "texto longo...", "output": "resumo curto"},  # not grammar/rewriting
    {"instruction": "Corrija a ortografia.", "input": "ele viajo ontem", "output": "Ele viajou ontem."},
    {"instruction": "Explique o que é o Sol.", "input": "", "output": ""},  # empty output -> dropped
]


def test_filters_only_grammar_and_rewriting_rows():
    results = list(filter_grammar_and_rewriting(RAW_ROWS))
    categories = {r["task_category"] for r in results}
    assert categories == {"grammar_correction", "rewriting"}
    assert len(results) == 3  # rows 0, 1, 3 — row 2 wrong category, row 4 empty output


def test_output_rows_conform_to_instruction_example_schema():
    for row in filter_grammar_and_rewriting(RAW_ROWS):
        validate_instruction_example(row)  # raises on violation


def test_ids_are_unique_and_source_tagged():
    results = list(filter_grammar_and_rewriting(RAW_ROWS))
    ids = [r["id"] for r in results]
    assert len(ids) == len(set(ids))
    assert all(r["source"] == "alpaca-pt-br" for r in results)


def test_unmatched_instruction_is_dropped():
    rows = [{"instruction": "Traduza para o inglês.", "input": "oi", "output": "hi"}]
    assert list(filter_grammar_and_rewriting(rows)) == []
