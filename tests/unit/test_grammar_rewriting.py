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


# --- feature 002 (FR-006): whole-word matching, code-task exclusion, drop-reason stats


def _classify_one(instruction, stats=None):
    rows = list(filter_grammar_and_rewriting([{"instruction": instruction, "input": "x", "output": "y"}], stats=stats))
    return rows[0]["task_category"] if rows else None


def test_previsao_no_longer_matches_revisao_substring():
    assert _classify_one("Dada uma previsão do tempo, liste possíveis atividades ao ar livre.") is None
    assert _classify_one("Encontre a previsão do tempo para Nova York hoje") is None


def test_forecast_instructions_are_excluded_even_when_revise_matches():
    rows = [
        {"instruction": "Revise o conjunto de dados e determine a previsão mais precisa.", "input": "x", "output": "y"},
        {"instruction": "Previsões de classificação: preveja a nota de uma revisão.", "input": "x", "output": "y"},
    ]
    assert list(filter_grammar_and_rewriting(rows)) == []


def test_code_fixing_instructions_are_excluded_from_grammar():
    assert _classify_one("Encontre os erros no código a seguir e corrija-os.") is None
    assert _classify_one("Corrija o bug na função abaixo") is None


def test_genuine_revision_and_correction_still_match():
    assert _classify_one("Corrija os erros de concordância na frase") == "grammar_correction"
    assert _classify_one("Revisão gramatical: ajuste o parágrafo") == "grammar_correction"
    assert _classify_one("Edite o texto para gramática, ortografia e clareza.") == "grammar_correction"


def test_review_instructions_no_longer_match_grammar():
    """T038 audit: "revisão" in alpaca-pt-br is almost always "review" (film/book/product)."""
    assert _classify_one("Gerar uma revisão do livro dado.") is None
    assert _classify_one("Avalie a revisão do filme a seguir.") is None
    assert _classify_one("Revise o poema para torná-lo mais lírico") is None


def test_sentence_building_exercises_are_excluded_from_grammar():
    assert _classify_one("Organize as palavras abaixo em uma frase gramaticalmente correta.") is None
    assert _classify_one("Crie uma frase usando as seguintes palavras de forma gramaticalmente correta.") is None
    assert _classify_one("Adicione a próxima frase à frase dada de forma gramaticalmente correta.") is None


def test_grammar_rows_require_an_input_text():
    from collections import Counter

    stats = Counter()
    rows = [
        {"instruction": "Como funciona um corretor ortográfico?", "input": "", "output": "Ele compara..."},
        {"instruction": "Corrija a frase gramaticalmente.", "input": "Ele vai à loja.", "output": "Ele vai à loja."},
    ]
    kept = list(filter_grammar_and_rewriting(rows, stats=stats))
    assert [r["input"] for r in kept] == ["Ele vai à loja."]
    assert stats["missing_input"] == 1


def test_stats_count_exclusions_and_empty_outputs():
    from collections import Counter

    stats = Counter()
    rows = [
        {"instruction": "Corrija o código a seguir", "input": "", "output": "x"},  # exclude_regex
        {"instruction": "Corrija a frase", "input": "os menino", "output": ""},  # no_output
        {"instruction": "Traduza para o inglês", "input": "oi", "output": "hi"},  # no category: not counted
        {"instruction": "Corrija a ortografia", "input": "ele viajo", "output": "Ele viajou."},
    ]
    kept = list(filter_grammar_and_rewriting(rows, stats=stats))
    assert len(kept) == 1
    assert stats == Counter({"exclude_regex": 1, "no_output": 1})
