"""Category-independent output-quality check (specs/002 contracts/dataset-preparation.md, FR-009).

The v2 audit found 37 training rows whose target answer was a degenerate run —
`E-mail : ssrsrsrsrs...`, `rochedo . . . . . . .` — 26 of them in classification.
A model trained on those learns to babble; this filter rejects them in every category.
"""

from __future__ import annotations

import re

# same char x6, a 2-char cycle x4 ("srsrsrsr" — the audit's own pattern; the contract's
# whitespace-delimited form alone misses it), or a token+space repeated x4
_REPEATED_RUN = re.compile(r"(.)\1{5,}|(..)\2{3,}|(\S+\s)\3{3,}")
_MIN_LENGTH_FOR_VARIETY_CHECK = 30
# absolute floor, not a ratio: distinct/length shrinks with length for any normal text (a ratio
# rule flagged 705 ordinary summaries on the real file); calibrated on data/train.jsonl, where
# <= 8 catches only "pica-pau-pau-pau-..." and >= 10 starts eating legitimate math answers
_MAX_DISTINCT_CHARS_FOR_DEGENERATE = 8


def is_degenerate_output(text: str) -> bool:
    if _REPEATED_RUN.search(text):
        return True
    if len(text) >= _MIN_LENGTH_FOR_VARIETY_CHECK and len(set(text)) <= _MAX_DISTINCT_CHARS_FOR_DEGENERATE:
        return True
    return False
