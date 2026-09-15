"""Single text normalization shared by dataset deduplication, the classification
label-in-instruction filter, and rule-based grading (specs/002 contracts/dataset-preparation.md).

Accent-insensitive on purpose: `src/grading/rule_based.py` already graded
classification that way in feature 001 (`"Reclamacao"` == `"reclamação"`), and the
dedupe/filter rules must agree with the grader on what counts as "the same label".
"""

from __future__ import annotations

import unicodedata


def normalize(text: str, strip_trailing_period: bool = True) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    collapsed = " ".join(stripped.lower().split())
    if strip_trailing_period:
        # "reclamação." and "reclamação" are the same label for dedupe/filter purposes;
        # the grader passes strip_trailing_period=False to keep 001's scoring byte-identical
        return collapsed.rstrip(". ")
    return collapsed
