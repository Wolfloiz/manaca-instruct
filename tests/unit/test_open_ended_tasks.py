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


# --- feature 002 (T030): tightened selection after the qlora-v2 audit
from collections import Counter


def _only(rows):
    return list(filter_open_ended_tasks(rows))


def test_trivia_instruction_is_not_simplification():
    rows = [{"instruction": "Você receberá uma pista de curiosidades e a categoria a que pertence. Simplifique.", "context": "pista", "output": "resposta"}]
    assert _only(rows) == []


def test_math_simplification_is_excluded():
    rows = [{"instruction": "Simplifique a expressão aritmética dada.", "context": "2x + 2x", "output": "4x"}]
    assert _only(rows) == []


def test_simplification_without_context_is_dropped():
    rows = [{"instruction": "Simplifique o texto a seguir.", "output": "algo mais simples"}]
    assert _only(rows) == []


def test_classification_label_listed_in_instruction_is_kept():
    rows = [{"instruction": "Classifique a avaliação como positivo ou negativo.", "context": "Péssimo atendimento.", "output": "Negativo"}]
    assert [r["output"] for r in _only(rows)] == ["Negativo"]


def test_classification_with_corrupted_output_is_dropped():
    rows = [{"instruction": "Classifique o e-mail como spam ou não spam.", "context": "…", "output": "E-mail : ssrsrsrsrsrsrsrs"}]
    assert _only(rows) == []


def test_classification_with_label_not_offered_is_dropped():
    rows = [{"instruction": "Classifique a língua do texto. inglês, chinês, japonês etc.", "context": "Sou", "output": "E-mail"}]
    assert _only(rows) == []


def test_classification_label_match_is_accent_and_case_insensitive():
    rows = [{"instruction": "Classifique como reclamação, dúvida, elogio ou solicitação.", "context": "Adorei!", "output": "ELOGIO."}]
    assert len(_only(rows)) == 1


def test_stats_counts_each_drop_reason():
    stats = Counter()
    rows = [
        {"instruction": "Simplifique isso.", "context": "texto", "output": ""},  # no_output
        {"instruction": "Simplifique a equação dada.", "context": "x+x", "output": "2x"},  # exclude_regex
        {"instruction": "Simplifique o texto a seguir.", "output": "simples"},  # missing_input
        {"instruction": "Classifique como spam ou não spam.", "context": "…", "output": "ssrsrsrsrs"},  # label_not_in_instruction
        {"instruction": "Corrija o texto.", "context": "x", "output": "y"},  # unmatched: not counted
        {"instruction": "Resuma o texto abaixo.", "context": "texto", "output": "resumo"},  # kept
    ]
    kept = list(filter_open_ended_tasks(rows, stats=stats))
    assert len(kept) == 1
    assert stats == Counter({"no_output": 1, "exclude_regex": 1, "missing_input": 1, "label_not_in_instruction": 1})
