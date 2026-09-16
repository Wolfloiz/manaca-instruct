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
from collections import Counter
from typing import Iterable, Iterator

SOURCE_NAME = "alpaca-pt-br"
HF_DATASET_ID = "dominguesm/alpaca-data-pt-br"

# Whole-word matching (feature 002, FR-006): the v2 pattern `revis(e|ão|ar)` matched the
# substring of "previsão" and pulled 52 weather-forecast rows into grammar_correction.
# `revis*` itself was dropped after the v3 audit (T038): 139 of 676 grammar rows matched
# only through it, and the sample was film/book/product *reviews* ("revisão" translating
# "review"), not language revision. Genuine revision tasks still match on gramátic/
# ortograf/corrij/erro de ..., which every true correction in the audit sample carried.
_GRAMMAR_KEYWORDS = re.compile(
    r"\bcorrij|gramátic|gramatical|ortográfic|ortografia|"
    r"erro(s)? de (escrita|texto|concordância)|\bconserte\b|"
    r"escrev(a|er) corretamente|sintax(e|is)",
    re.IGNORECASE,
)
# "Encontre os erros no código a seguir e corrija-os" is a code task, not language correction
# (20 such rows in the v2 training set). `previs*` covers the forecast/prediction rows that
# still match on a genuine "Revise ..."/"... revisão" elsewhere in the instruction.
# The generation/reordering verbs cover "Organize as palavras em uma frase gramaticalmente
# correta" / "Crie uma frase ..." — grammar *exercises* that produce a sentence from scratch
# rather than correct a given one (64 rows in the first v3 build).
_GRAMMAR_EXCLUDE = re.compile(
    r"\b(código|code|programa|programação|função|script|sql|python|javascript|bug|previs\w*|"
    r"organiz\w*|reorganiz\w*|reorden\w*|agrup\w*|cri(e|ar)|ger(e|ar)|adicion\w*|"
    r"compo(nha|r)|constru\w*|form(e|ar)|liste|mnemônico)\b",
    re.IGNORECASE,
)
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


def _classify(instruction: str, stats: Counter | None = None) -> str | None:
    if _GRAMMAR_KEYWORDS.search(instruction):
        if _GRAMMAR_EXCLUDE.search(instruction):
            if stats is not None:
                stats["exclude_regex"] += 1
            return None
        return "grammar_correction"
    if _REWRITING_KEYWORDS.search(instruction):
        return "rewriting"
    return None


def filter_grammar_and_rewriting(raw_rows: Iterable[dict], stats: Counter | None = None) -> Iterator[dict]:
    """Classify raw Alpaca-PT-BR rows into grammar_correction/rewriting InstructionExamples.

    Raw row shape (Stanford-Alpaca-style): {"instruction": str, "input": str, "output": str}.
    Rows that don't match either category's keywords are dropped (they'll be
    covered by Agent 2's open_ended_tasks.py filter, or excluded entirely).
    `stats`, when given, counts drop reasons for the preparation report.
    """
    seen_ids: set[str] = set()
    for i, row in enumerate(raw_rows):
        category = _classify(row["instruction"], stats)
        if category is None:
            continue
        if not row.get("output", "").strip():
            if stats is not None:
                stats["no_output"] += 1
            continue  # no usable target output — skip rather than train on an empty label
        if category == "grammar_correction" and not row.get("input", "").strip():
            # Same rule simplification already applies: a correction needs a text to correct.
            # The 133 empty-input grammar rows in the first v3 build were meta questions
            # ("Como funciona um corretor ortográfico?"), rule lists, or word-ordering tasks.
            if stats is not None:
                stats["missing_input"] += 1
            continue

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
