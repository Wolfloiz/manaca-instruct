"""Source and filter simplification/summarization/classification examples
from dominguesm/Canarim-Instruct-PTBR-Dataset (falling back to alpaca-pt-br
for categories it's thin on, per research.md §1).

Same two-stage seam pattern as src/dataset_filters/grammar_rewriting.py
(Agent 1's module): a network-touching loader plus a pure, unit-testable filter.

Feature 002 (T030) tightened the selection after the qlora-v2 audit measured the
defects the keyword-only rules let through: 173/566 "simplification" rows were
trivia questions ("pista de curiosidades"), 4 were math, 45 had no text to
simplify, and 26/905 classification rows had corrupted `ssrsrs…` answers with
0/905 answering one of the labels their own instruction offered.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, Iterator

from src.text_normalize import normalize

SOURCE_NAME = "canarim"
HF_DATASET_ID = "dominguesm/Canarim-Instruct-PTBR-Dataset"

_SIMPLIFICATION_KEYWORDS = re.compile(
    r"simplifiqu|simplificar|linguagem simples|mais simples|mais clara", re.IGNORECASE
)
_SIMPLIFICATION_EXCLUDE = re.compile(
    r"curiosidade|trivia|\bexpressão\b|\bequação\b|\bfração\b|\bpolinômio\b", re.IGNORECASE
)
_SUMMARIZATION_KEYWORDS = re.compile(r"resuma|resumir|resumo|sintetiz|condense", re.IGNORECASE)
_CLASSIFICATION_KEYWORDS = re.compile(r"classifiqu|classificar|categoriz", re.IGNORECASE)

CLASSIFICATION_MAX_LABEL_WORDS = 4


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


def _label_in_instruction(output: str, instruction: str) -> bool:
    """The evaluation asks for one of the labels enumerated in the instruction, so keep only
    training rows with that shape — it drops corrupted answers without a hand list."""
    normalized_output = normalize(output)
    return (
        bool(normalized_output)
        and len(output.split()) <= CLASSIFICATION_MAX_LABEL_WORDS
        and normalized_output in normalize(instruction)
    )


def _drop_reason(category: str, instruction: str, input_text: str, output: str) -> str | None:
    if not output.strip():
        return "no_output"
    if category == "simplification":
        if _SIMPLIFICATION_EXCLUDE.search(instruction):
            return "exclude_regex"
        if not input_text.strip():
            return "missing_input"
    if category == "classification" and not _label_in_instruction(output, instruction):
        return "label_not_in_instruction"
    return None


def filter_open_ended_tasks(raw_rows: Iterable[dict], stats: Counter | None = None) -> Iterator[dict]:
    """Classify raw Canarim rows into simplification/summarization/classification InstructionExamples.

    Raw row shape (per research.md's Canarim README summary): {"instruction": str,
    "output": str, "context": str (optional)} — `context` is normalized to the
    shared `input` field name used by InstructionExample.

    `stats`, when given, counts dropped rows per reason (`no_output`, `exclude_regex`,
    `missing_input`, `label_not_in_instruction`) for the preparation report; rows that
    match no category keyword are unselected, not dropped, and are not counted.
    """
    seen_ids: set[str] = set()
    for i, row in enumerate(raw_rows):
        category = _classify(row["instruction"])
        if category is None:
            continue
        input_text = row.get("context", row.get("input", "")) or ""
        output = row.get("output", "") or ""
        reason = _drop_reason(category, row["instruction"], input_text, output)
        if reason is not None:
            if stats is not None:
                stats[reason] += 1
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
            "input": input_text.strip(),
            "output": output.strip(),
        }
