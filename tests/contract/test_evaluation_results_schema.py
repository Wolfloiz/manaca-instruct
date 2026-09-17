"""Contract tests for specs/001-manaca-instruct-tuning/contracts/evaluation-results-schema.md."""

import pytest

from src.schema_validation import SchemaError, validate_evaluation_result

VALID_RULE_BASED_RESULT = {
    "id": "grupo_a-classification-003",
    "task_category": "classification",
    "model": "manaca-instruct-pt",
    "prompt": "Classifique: Meu pedido ainda não chegou.",
    "expected": "reclamação",
    "output": "reclamação",
    "grading_method": "rule_based",
    "score": 1,
    "run_id": "qlora-v1",
}

VALID_PENDING_MANUAL_REVIEW_RESULT = {
    "id": "grupo_b-001",
    "task_category": None,
    "model": "manaca-1b-base",
    "prompt": "Explique o que é inteligência artificial em poucas palavras.",
    "expected": None,
    "output": "a inteligência artificial no brasil é um campo de estudo...",
    "grading_method": "manual_review",
    "score": None,  # not yet graded — contracts/evaluation-results-schema.md allows this
    "run_id": "baseline",
}


def test_valid_rule_based_result_passes():
    validate_evaluation_result(VALID_RULE_BASED_RESULT)  # no raise


def test_pending_manual_review_result_passes():
    validate_evaluation_result(VALID_PENDING_MANUAL_REVIEW_RESULT)  # no raise


def test_rule_based_result_with_null_score_rejected():
    bad = dict(VALID_RULE_BASED_RESULT, score=None)
    with pytest.raises(SchemaError):
        validate_evaluation_result(bad)


def test_unknown_model_rejected():
    bad = dict(VALID_RULE_BASED_RESULT, model="some-other-model")
    with pytest.raises(SchemaError):
        validate_evaluation_result(bad)


def test_invalid_score_value_rejected():
    bad = dict(VALID_RULE_BASED_RESULT, score=0.75)  # only null, 0, 0.5, 1 are valid
    with pytest.raises(SchemaError):
        validate_evaluation_result(bad)
