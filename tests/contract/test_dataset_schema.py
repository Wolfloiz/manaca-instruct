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
    "id": "grupo_a-classification-003",
    "group": "grupo_a",
    "task_category": "classification",
    "prompt": "Classifique: Meu pedido ainda não chegou.",
    "expected": "reclamação",
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


# --- feature 002 additions: optional instruction/input split fields and the "dev" group
# (specs/002-data-quality-iteration/contracts/evaluation-presentation.md)


def test_split_fields_that_reconstruct_prompt_pass():
    validate_evaluation_prompt(
        {**VALID_GRUPO_A_RULE_BASED, "instruction": "Classifique", "input": "Meu pedido ainda não chegou."}
    )


def test_split_fields_must_appear_together():
    with pytest.raises(SchemaError, match="together"):
        validate_evaluation_prompt({**VALID_GRUPO_A_RULE_BASED, "instruction": "Classifique"})
    with pytest.raises(SchemaError, match="together"):
        validate_evaluation_prompt({**VALID_GRUPO_A_RULE_BASED, "input": "Meu pedido ainda não chegou."})


def test_split_fields_that_do_not_reconstruct_prompt_rejected():
    with pytest.raises(SchemaError, match="reconstruct"):
        validate_evaluation_prompt(
            {**VALID_GRUPO_A_RULE_BASED, "instruction": "Classifique", "input": "Meu pedido não chegou."}
        )


def test_grupo_b_rows_must_not_carry_split_fields():
    with pytest.raises(SchemaError, match="grupo_b"):
        validate_evaluation_prompt(
            {**VALID_GRUPO_B, "instruction": "Explique", "input": "o que é inteligência artificial"}
        )


def test_dev_group_accepted_with_task_category_and_empty_input_form():
    validate_evaluation_prompt(
        {
            "id": "dev-summarization-001",
            "group": "dev",
            "task_category": "summarization",
            "prompt": "Resuma o texto a seguir",
            "instruction": "Resuma o texto a seguir",
            "input": "",
            "expected": "Um resumo de referência.",
            "grading_method": "manual_review",
            "source_id": "canarim-000123",
        }
    )


def test_dev_group_requires_valid_task_category():
    with pytest.raises(SchemaError, match="dev task_category"):
        validate_evaluation_prompt(
            {**VALID_GRUPO_A_RULE_BASED, "id": "dev-x-001", "group": "dev", "task_category": None}
        )
