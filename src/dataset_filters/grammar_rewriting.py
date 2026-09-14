"""Source and filter grammar_correction + rewriting examples from dominguesm/alpaca-data-pt-br.

Per specs/001-manaca-instruct-tuning/research.md §1: this dataset is CC BY-NC-4.0,
which sets the license for the published Manaca-Instruct-PT model (FR-009).

Two-stage design, matching src/evaluate.py's seam pattern:
- `load_raw_alpaca_pt_br()` touches the network (datasets.load_dataset) and is
  NOT exercised by this scaffolding-only pass's tests.
- `filter_grammar_and_rewriting()` is pure and fully unit-testable against
  synthetic rows shaped like the real dataset (instruction/input/output).
"""

from __future__ import annotations

import re
from typing import Iterable, Iterator

SOURCE_NAME = "alpaca-pt-br"
HF_DATASET_ID = "dominguesm/alpaca-data-pt-br"

_GRAMMAR_KEYWORDS = re.compile(r"corrij|gramátic|gramatical|ortográfic|ortografia", re.IGNORECASE)
_REWRITING_KEYWORDS = re.compile(
    r"reescreva|reescrever|reformul|parafrase|tom (mais|profissional)|de maneira profissional|forma formal",
    re.IGNORECASE,
)


def load_raw_alpaca_pt_br():
    """Pull the raw dataset from Hugging Face. Not called by this pass's tests — network seam.

    Real implementation (left plain, not a NotImplementedError stub, since it's a
    single well-defined call — just not invoked without the user's go-ahead to
    download data, per tasks.md's Phase 4 scope note).
    """
    from datasets import load_dataset  # local import: keep this module importable without the dep installed

    return load_dataset(HF_DATASET_ID, split="train")


def _classify(instruction: str) -> str | None:
    if _GRAMMAR_KEYWORDS.search(instruction):
        return "grammar_correction"
    if _REWRITING_KEYWORDS.search(instruction):
        return "rewriting"
    return None


def filter_grammar_and_rewriting(raw_rows: Iterable[dict]) -> Iterator[dict]:
    """Classify raw Alpaca-PT-BR rows into grammar_correction/rewriting InstructionExamples.

    Raw row shape (Stanford-Alpaca-style): {"instruction": str, "input": str, "output": str}.
    Rows that don't match either category's keywords are dropped (they'll be
    covered by Agent 2's open_ended_tasks.py filter, or excluded entirely).
    """
    seen_ids: set[str] = set()
    for i, row in enumerate(raw_rows):
        category = _classify(row["instruction"])
        if category is None:
            continue
        if not row.get("output", "").strip():
            continue  # no usable target output — skip rather than train on an empty label

        example_id = f"{SOURCE_NAME}-{i:06d}"
        if example_id in seen_ids:
            continue  # defensive: duplicate index should never happen, but never emit a duplicate id
        seen_ids.add(example_id)

        yield {
            "id": example_id,
            "source": SOURCE_NAME,
            "task_category": category,
            "instruction": row["instruction"].strip(),
            "input": row.get("input", "").strip(),
            "output": row["output"].strip(),
        }
