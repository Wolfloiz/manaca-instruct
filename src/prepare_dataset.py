"""Orchestrate dataset preparation: combine Agent 1 + Agent 2's filter modules,
dedupe against the frozen evaluation prompts, and write train/validation splits.

Usage (per specs/001-manaca-instruct-tuning/quickstart.md):

    python -m src.prepare_dataset --sources alpaca-pt-br canarim --out-dir data/

Implements FR-002 and data-model.md's InstructionExample validation rules:
- task_category in the fixed 5-value set (checked per-row by the filter modules
  via src/schema_validation.py)
- no (instruction, input) overlap with data/eval/grupo_a_prompts.jsonl or
  grupo_b_prompts.jsonl (data-model.md's InstructionExample rule)
- total count in the 3,000-5,000 range, roughly evenly split across categories
  (Clarifications session, 2026-09-14)

NOTE: `load_raw_alpaca_pt_br()`/`load_raw_canarim()` touch the network. This
module's `main()` is not executed against real data in this scaffolding-only
pass (tasks.md Phase 4 scope note) — `build_dataset()` below is exercised by
tests against synthetic raw rows instead.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Iterable

from src.dataset_filters.grammar_rewriting import filter_grammar_and_rewriting, load_raw_alpaca_pt_br
from src.dataset_filters.open_ended_tasks import filter_open_ended_tasks, load_raw_canarim
from src.schema_validation import TASK_CATEGORIES, validate_instruction_example

TARGET_TOTAL_MIN = 3000
TARGET_TOTAL_MAX = 5000
VALIDATION_FRACTION = 0.1


def _load_eval_prompt_keys(eval_dir: Path) -> set[tuple[str, str]]:
    """(instruction-ish text, input) pairs that must never appear in training data.

    Eval prompts store a single combined `prompt` string rather than separate
    instruction/input fields, so the overlap check compares against that
    combined text — sufficient to catch verbatim reuse, which is the failure
    mode data-model.md's rule guards against.
    """
    keys: set[tuple[str, str]] = set()
    for filename in ("grupo_a_prompts.jsonl", "grupo_b_prompts.jsonl"):
        path = eval_dir / filename
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                keys.add((row["prompt"].strip(), ""))
    return keys


def _dedupe_against_eval(examples: Iterable[dict], eval_keys: set[tuple[str, str]]) -> list[dict]:
    kept = []
    for ex in examples:
        combined = f"{ex['instruction']} {ex['input']}".strip()
        if (combined, "") in eval_keys or (ex["instruction"].strip(), "") in eval_keys:
            continue
        kept.append(ex)
    return kept


def _cap_per_category(examples: list[dict], target_total: int) -> list[dict]:
    """Roughly even split across the 5 categories, capped at target_total overall."""
    per_category_cap = target_total // len(TASK_CATEGORIES)
    by_category: dict[str, list[dict]] = {c: [] for c in TASK_CATEGORIES}
    for ex in examples:
        by_category[ex["task_category"]].append(ex)

    result = []
    for category, rows in by_category.items():
        result.extend(rows[:per_category_cap])
    return result


def build_dataset(
    raw_alpaca_rows: Iterable[dict],
    raw_canarim_rows: Iterable[dict],
    eval_keys: set[tuple[str, str]],
    target_total: int = TARGET_TOTAL_MAX,
    seed: int = 42,
) -> list[dict]:
    """Pure orchestration logic — no network/filesystem access. Fully unit-testable."""
    examples = list(filter_grammar_and_rewriting(raw_alpaca_rows)) + list(filter_open_ended_tasks(raw_canarim_rows))

    for ex in examples:
        validate_instruction_example(ex)

    examples = _dedupe_against_eval(examples, eval_keys)

    rng = random.Random(seed)
    rng.shuffle(examples)

    examples = _cap_per_category(examples, target_total)

    seen_ids = set()
    for ex in examples:
        if ex["id"] in seen_ids:
            raise ValueError(f"duplicate InstructionExample id after combining sources: {ex['id']!r}")
        seen_ids.add(ex["id"])

    return examples


def split_train_validation(examples: list[dict], validation_fraction: float = VALIDATION_FRACTION, seed: int = 42):
    rng = random.Random(seed)
    shuffled = examples[:]
    rng.shuffle(shuffled)
    n_val = max(1, int(len(shuffled) * validation_fraction)) if shuffled else 0
    return shuffled[n_val:], shuffled[:n_val]


def _write_jsonl(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", nargs="+", default=["alpaca-pt-br", "canarim"])
    parser.add_argument("--out-dir", type=Path, default=Path("data"))
    args = parser.parse_args(argv)

    eval_keys = _load_eval_prompt_keys(args.out_dir / "eval")

    print("Downloading raw datasets (network access required)...")
    raw_alpaca = load_raw_alpaca_pt_br() if "alpaca-pt-br" in args.sources else []
    raw_canarim = load_raw_canarim() if "canarim" in args.sources else []

    examples = build_dataset(raw_alpaca, raw_canarim, eval_keys)
    train, validation = split_train_validation(examples)

    _write_jsonl(train, args.out_dir / "train.jsonl")
    _write_jsonl(validation, args.out_dir / "validation.jsonl")

    print(f"Wrote {len(train)} training examples and {len(validation)} validation examples.")
    if not (TARGET_TOTAL_MIN <= len(examples) <= TARGET_TOTAL_MAX):
        print(
            f"WARNING: total example count {len(examples)} is outside the target "
            f"{TARGET_TOTAL_MIN}-{TARGET_TOTAL_MAX} range from the Clarifications session.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
