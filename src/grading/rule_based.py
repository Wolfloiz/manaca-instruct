"""Rule-based scoring for the one closed-answer task category (classification).

Originally covered grammar_correction too (Clarifications Q1, option D), but
that was moved to manual_review on 2026-09-15: edit-distance-to-a-single-
reference couldn't tell a genuinely good correction (different valid
phrasing) apart from an off-topic failure — both land at low similarity.
Reading qlora-v1's real grammar_correction outputs found ~31% genuine fixes
that this scorer reported as 0%. See research.md §3's update and
src/schema_validation.py's RULE_BASED_CATEGORIES comment.
"""

from __future__ import annotations

from src.text_normalize import normalize


def _normalize_label(text: str) -> str:
    """Case/whitespace/accent-insensitive normalization for classification labels.

    strip_trailing_period=False keeps this scorer byte-identical to feature 001's, so
    classification scores of new runs stay comparable with the frozen v2/official ones.
    """
    return normalize(text, strip_trailing_period=False)


def score_classification(output: str, expected: str) -> float:
    """Exact match after case/whitespace/accent normalization."""
    return 1.0 if _normalize_label(output) == _normalize_label(expected) else 0.0


def score_rule_based(task_category: str, output: str, expected: str) -> float:
    """Dispatch to the right scorer. Raises for any category this module doesn't own."""
    if task_category == "classification":
        return score_classification(output, expected)
    raise ValueError(
        f"rule_based.py only scores classification, got {task_category!r} — "
        "this category should be manual_review (grammar_correction moved there 2026-09-15)."
    )
