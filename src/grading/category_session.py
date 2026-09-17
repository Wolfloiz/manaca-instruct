"""Blind, interleaved grading session restricted to one task category (or to everything but one).

    python -m src.grading.category_session --category grammar_correction --shuffle-seed 17 \
        eval/results/qlora-v2.jsonl eval/results/qlora-v3a.jsonl ... eval/results/official-instruct.jsonl
    python -m src.grading.category_session --exclude grammar_correction --shuffle-seed 11 eval/results/qlora-v3b-rp11.jsonl

Why this exists (eval/results/adoption-decision.md, "Regraduação cega da gramática"): the grammar
grades of qlora-v2's first blind session did not follow the rubric used everywhere else, so the
category is re-graded for every run in one interleaved session, while the other categories keep
their grades. `review_cli` grades whole files, so this module:

1. copies only the selected rows of each *original* results file into a session directory
   (manual_review scores reset to null, rule-based scores kept) — resumable like review_cli;
2. runs `review_cli.review_blind` on those copies (same display, same shuffle, same `-blind` siblings);
3. merges every grade given back into the run's real `eval/results/<run_id>-blind.jsonl`, creating it
   from the original when it does not exist yet. Original files are never modified.

Re-running the command resumes the session (only still-pending rows are shown) and merges again.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.grading.review_cli import (
    _load_or_create_blind_copy,
    _load_rows,
    _save_rows,
    _sha256,
    blind_output_path,
    review_blind,
)

DEFAULT_WORKDIR = Path.home() / "manaca-regrade"


def _selected(row: dict, category: str, exclude: bool) -> bool:
    return (row["task_category"] != category) if exclude else (row["task_category"] == category)


def prepare_session_files(inputs: list[Path], workdir: Path, category: str, exclude: bool) -> list[Path]:
    """One session file per run with only the selected rows; created once, then reused (resume)."""
    workdir.mkdir(parents=True, exist_ok=True)
    session_files = []
    for path in inputs:
        session_path = workdir / path.name
        if not session_path.exists():
            rows = [r for r in _load_rows(path) if _selected(r, category, exclude)]
            if not rows:
                raise ValueError(f"{path}: no rows selected for category={category!r} exclude={exclude}")
            for row in rows:
                if row["grading_method"] == "manual_review":
                    row["score"] = None
            _save_rows(session_path, rows)
        session_files.append(session_path)
    return session_files


def merge_back(inputs: list[Path], session_files: list[Path]) -> dict[Path, int]:
    """Copy every grade present in a session's -blind file into the run's real -blind file."""
    merged: dict[Path, int] = {}
    for original, session_path in zip(inputs, session_files):
        session_blind = blind_output_path(session_path)
        if not session_blind.exists():
            continue
        graded = {r["id"]: r["score"] for r in _load_rows(session_blind) if r["grading_method"] == "manual_review" and r["score"] is not None}
        target, rows = _load_or_create_blind_copy(original)
        count = 0
        for row in rows:
            if row["id"] in graded:
                row["score"] = graded[row["id"]]
                count += 1
        _save_rows(target, rows)
        merged[target] = count
    return merged


def main(argv: list[str] | None = None, input_fn=input) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("results_files", type=Path, nargs="+", help="original (non -blind) results files")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--category", help="grade only this task_category")
    group.add_argument("--exclude", help="grade every category except this one")
    parser.add_argument("--shuffle-seed", type=int, required=True)
    parser.add_argument("--workdir", type=Path, default=None, help=f"session directory (default: {DEFAULT_WORKDIR}/<category>)")
    parser.add_argument("--merge-only", action="store_true", help="skip the interactive session; just merge existing grades")
    args = parser.parse_args(argv)

    category = args.category or args.exclude
    exclude = args.exclude is not None
    workdir = args.workdir or DEFAULT_WORKDIR / (("not-" if exclude else "") + category)
    for path in args.results_files:
        if path.stem.endswith("-blind"):
            parser.error(f"{path}: pass the original results file, not its -blind copy")

    before = {p: _sha256(p) for p in args.results_files}
    session_files = prepare_session_files(args.results_files, workdir, category, exclude)
    print(f"session dir {workdir}: {len(session_files)} runs, category={category!r} exclude={exclude}")

    if not args.merge_only:
        summary = review_blind(session_files, input_fn=input_fn, shuffle_seed=args.shuffle_seed, blind=True)
        for out_path, (graded, still_pending) in summary.items():
            print(f"{out_path.name}: graded {graded} this session, {still_pending} still pending")

    merged = merge_back(args.results_files, session_files)
    for target, count in merged.items():
        print(f"merged {count} grade(s) into {target}")
    for path in args.results_files:
        if _sha256(path) != before[path]:
            raise RuntimeError(f"{path} changed during the session (002 FR-022)")
    print("originals unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
