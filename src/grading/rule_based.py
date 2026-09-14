"""Rule-based scoring for the two closed-answer task categories.

Per specs/001-manaca-instruct-tuning/research.md §3 (Clarifications Q1, option D):
grammar_correction and classification have a well-defined correct answer, so they
are scored automatically; the other three categories are manual_review (see
src/grading/review_cli.py).
"""

from __future__ import annotations

import difflib
import unicodedata

GRAMMAR_MATCH_THRESHOLD = 0.9


def _normalize_label(text: str) -> str:
    """Case/whitespace/accent-insensitive normalization for classification labels."""
    text = unicodedata.normalize("NFKD", text.strip().lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.split())


def score_grammar_correction(output: str, expected: str) -> float:
    """Normalized edit-distance ratio >= 0.9 counts as a pass (research.md §3).

    Tolerates minor acceptable surface variation (e.g. punctuation) that an
    exact-match comparison would wrongly fail.
    """
    ratio = difflib.SequenceMatcher(a=output.strip(), b=expected.strip()).ratio()
    return 1.0 if ratio >= GRAMMAR_MATCH_THRESHOLD else 0.0


def score_classification(output: str, expected: str) -> float:
    """Exact match after case/whitespace/accent normalization."""
    return 1.0 if _normalize_label(output) == _normalize_label(expected) else 0.0


def score_rule_based(task_category: str, output: str, expected: str) -> float:
    """Dispatch to the right scorer. Raises for any category this module doesn't own."""
    if task_category == "grammar_correction":
        return score_grammar_correction(output, expected)
    if task_category == "classification":
        return score_classification(output, expected)
    raise ValueError(
        f"rule_based.py only scores grammar_correction and classification, got {task_category!r} — "
        "this category should be manual_review per the Clarifications session."
    )
