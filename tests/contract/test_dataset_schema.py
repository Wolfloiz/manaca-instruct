"""Contract tests for specs/001-manaca-instruct-tuning/contracts/dataset-schema.md."""

import pytest

from src.schema_validation import SchemaError, validate_evaluation_prompt, validate_instruction_example

VALID_EXAMPLE = {
    "id": "alpaca_pt_br-000123",
    "source": "alpaca-pt-br",
    "task_category": "grammar_correction",
    "instruction": "Corrija o texto a seguir.",
    "input": "os menino foi na escola ontem",
    "output": "Os meninos foram à escola ontem.",
}

VALID_GRUPO_A_RULE_BASED = {
    "id": "grupo_a-grammar-003",
    "group": "grupo_a",
    "task_category": "grammar_correction",
    "prompt": "Corrija: os relatório foi enviado ontem",
    "expected": "O relatório foi enviado ontem.",
    "grading_method": "rule_based",
}

VALID_GRUPO_B = {
    "id": "grupo_b-001",
    "group": "grupo_b",
    "task_category": None,
    "prompt": "Explique o que é inteligência artificial em poucas palavras.",
    "expected": None,
    "grading_method": "manual_review",
}


def test_valid_instruction_example_passes():
    validate_instruction_example(VALID_EXAMPLE)  # no raise


def test_instruction_example_missing_key_rejected():
    bad = dict(VALID_EXAMPLE)
    del bad["output"]
    with pytest.raises(SchemaError):
        validate_instruction_example(bad)


def test_instruction_example_bad_task_category_rejected():
    bad = dict(VALID_EXAMPLE, task_category="translation")  # not one of the 5 fixed categories
    with pytest.raises(SchemaError):
        validate_instruction_example(bad)


def test_valid_grupo_a_rule_based_prompt_passes():
    validate_evaluation_prompt(VALID_GRUPO_A_RULE_BASED)  # no raise


def test_valid_grupo_b_prompt_passes():
    validate_evaluation_prompt(VALID_GRUPO_B)  # no raise


def test_rule_based_prompt_without_expected_rejected():
    bad = dict(VALID_GRUPO_A_RULE_BASED, expected=None)
    with pytest.raises(SchemaError):
        validate_evaluation_prompt(bad)


def test_grupo_b_prompt_with_task_category_rejected():
    bad = dict(VALID_GRUPO_B, task_category="grammar_correction")
    with pytest.raises(SchemaError):
        validate_evaluation_prompt(bad)
