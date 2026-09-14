import pytest

from src.grading.rule_based import score_classification, score_grammar_correction, score_rule_based


def test_grammar_exact_match_passes():
    assert score_grammar_correction("Os meninos foram à escola ontem.", "Os meninos foram à escola ontem.") == 1.0


def test_grammar_minor_variation_still_passes():
    # trailing punctuation/spacing difference should not fail a near-identical correction
    assert score_grammar_correction("Os meninos foram à escola ontem", "Os meninos foram à escola ontem.") == 1.0


def test_grammar_wrong_correction_fails():
    assert score_grammar_correction("Os menino foi na escola ontem", "Os meninos foram à escola ontem.") == 0.0


def test_classification_exact_match_passes():
    assert score_classification("reclamação", "reclamação") == 1.0


def test_classification_case_and_accent_insensitive():
    assert score_classification("Reclamacao", "reclamação") == 1.0
    assert score_classification("  RECLAMAÇÃO  ", "reclamação") == 1.0


def test_classification_wrong_label_fails():
    assert score_classification("elogio", "reclamação") == 0.0


def test_dispatch_routes_by_category():
    assert score_rule_based("classification", "elogio", "elogio") == 1.0
    assert score_rule_based("grammar_correction", "x", "x") == 1.0


def test_dispatch_rejects_open_ended_categories():
    with pytest.raises(ValueError):
        score_rule_based("summarization", "x", "y")
