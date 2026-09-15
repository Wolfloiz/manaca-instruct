from src.evaluate import _format_inference_prompt
from src.prompt_format import format_prompt
from src.train_qlora import _format_prompt


def test_inference_form_without_input_ends_at_resposta_marker():
    assert format_prompt("Corrija o texto: os menino foi") == (
        "### Instrução:\nCorrija o texto: os menino foi\n\n### Resposta:\n"
    )


def test_inference_form_with_input_adds_entrada_block():
    assert format_prompt("Corrija o texto", "os menino foi") == (
        "### Instrução:\nCorrija o texto\n\n### Entrada:\nos menino foi\n\n### Resposta:\n"
    )


def test_training_form_appends_output_after_resposta_marker():
    assert format_prompt("Corrija o texto", "os menino foi", "Os meninos foram") == (
        "### Instrução:\nCorrija o texto\n\n### Entrada:\nos menino foi\n\n### Resposta:\nOs meninos foram"
    )


def test_empty_input_omits_entrada_block_even_in_training_form():
    assert "### Entrada:" not in format_prompt("Explique", "", "resposta")


def test_matches_train_qlora_format_prompt():
    for example in (
        {"instruction": "Corrija", "input": "os menino foi", "output": "Os meninos foram"},
        {"instruction": "Explique o que é um verbo", "input": "", "output": "Um verbo é..."},
    ):
        assert format_prompt(example["instruction"], example["input"], example["output"]) == _format_prompt(example)


def test_matches_evaluate_inference_prompt():
    for text in ("Corrija gramaticalmente o texto: os menino foi", "Qual é a capital do Brasil?"):
        assert format_prompt(text) == _format_inference_prompt(text)
