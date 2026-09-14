"""Source and filter simplification/summarization/classification examples
from dominguesm/Canarim-Instruct-PTBR-Dataset (falling back to alpaca-pt-br
for categories it's thin on, per research.md §1).

Same two-stage seam pattern as src/dataset_filters/grammar_rewriting.py
(Agent 1's module): a network-touching loader plus a pure, unit-testable filter.
"""

from __future__ import annotations

import re
from typing import Iterable, Iterator

SOURCE_NAME = "canarim"
HF_DATASET_ID = "dominguesm/Canarim-Instruct-PTBR-Dataset"

_SIMPLIFICATION_KEYWORDS = re.compile(
    r"simplifiqu|simplificar|linguagem simples|mais simples|mais clara", re.IGNORECASE
)
_SUMMARIZATION_KEYWORDS = re.compile(r"resuma|resumir|resumo|sintetiz|condense", re.IGNORECASE)
_CLASSIFICATION_KEYWORDS = re.compile(r"classifiqu|classificar|categoriz", re.IGNORECASE)


def load_raw_canarim():
    """Pull the raw dataset from Hugging Face. Not called by this pass's tests — network seam.

    See grammar_rewriting.py's load_raw_alpaca_pt_br() for why this is left as
    real (not stubbed) code that simply isn't invoked without a download in scope.
    """
    from datasets import load_dataset

    return load_dataset(HF_DATASET_ID, split="train")


def _classify(instruction: str) -> str | None:
    if _SIMPLIFICATION_KEYWORDS.search(instruction):
        return "simplification"
    if _SUMMARIZATION_KEYWORDS.search(instruction):
        return "summarization"
    if _CLASSIFICATION_KEYWORDS.search(instruction):
        return "classification"
    return None


def filter_open_ended_tasks(raw_rows: Iterable[dict]) -> Iterator[dict]:
    """Classify raw Canarim rows into simplification/summarization/classification InstructionExamples.

    Raw row shape (per research.md's Canarim README summary): {"instruction": str,
    "output": str, "context": str (optional)} — `context` is normalized to the
    shared `input` field name used by InstructionExample.
    """
    seen_ids: set[str] = set()
    for i, row in enumerate(raw_rows):
        category = _classify(row["instruction"])
        if category is None:
            continue
        if not row.get("output", "").strip():
            continue

        example_id = f"{SOURCE_NAME}-{i:06d}"
        if example_id in seen_ids:
            continue
        seen_ids.add(example_id)

        yield {
            "id": example_id,
            "source": SOURCE_NAME,
            "task_category": category,
            "instruction": row["instruction"].strip(),
            "input": row.get("context", row.get("input", "")).strip(),
            "output": row["output"].strip(),
        }
