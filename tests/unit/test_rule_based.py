import pytest

from src.grading.rule_based import score_classification, score_rule_based


def test_classification_exact_match_passes():
    assert score_classification("reclamação", "reclamação") == 1.0


def test_classification_case_and_accent_insensitive():
    assert score_classification("Reclamacao", "reclamação") == 1.0
    assert score_classification("  RECLAMAÇÃO  ", "reclamação") == 1.0


def test_classification_wrong_label_fails():
    assert score_classification("elogio", "reclamação") == 0.0


def test_dispatch_routes_classification():
    assert score_rule_based("classification", "elogio", "elogio") == 1.0


def test_dispatch_rejects_grammar_correction():
    # moved to manual_review 2026-09-15 — see rule_based.py's module docstring
    with pytest.raises(ValueError):
        score_rule_based("grammar_correction", "x", "x")


def test_dispatch_rejects_open_ended_categories():
    with pytest.raises(ValueError):
        score_rule_based("summarization", "x", "y")
