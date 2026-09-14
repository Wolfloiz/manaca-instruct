"""Interactive CLI to manually grade the manual_review rows in an evaluation results file.

Per contracts/evaluation-results-schema.md: src/evaluate.py writes manual_review
rows with score: null; this is the only component permitted to fill them in
(data-model.md's validation rule against silent defaulting). Never auto-scores —
every row requires an explicit human judgment (1 = correct, 0.5 = partial,
0 = incorrect), matching the rubric in spec.md's FR-004.

Usage:
    python -m src.grading.review_cli eval/results/baseline.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VALID_SCORES = {"1": 1.0, "0.5": 0.5, "0": 0.0}


def _load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _save_rows(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _prompt_for_score(row: dict, index: int, total: int, input_fn=input) -> float:
    print(f"\n[{index}/{total}] id={row['id']} task_category={row['task_category']} model={row['model']}")
    print(f"Prompt:   {row['prompt']}")
    if row.get("expected"):
        print(f"Expected: {row['expected']}")
    print(f"Output:   {row['output']}")
    while True:
        answer = input_fn("Score (1=correct, 0.5=partial, 0=incorrect, s=skip for now): ").strip().lower()
        if answer == "s":
            return None
        if answer in VALID_SCORES:
            return VALID_SCORES[answer]
        print("Please enter 1, 0.5, 0, or s.")


def review_file(path: Path, input_fn=input) -> tuple[int, int]:
    """Returns (graded_count, still_pending_count)."""
    rows = _load_rows(path)
    pending = [(i, r) for i, r in enumerate(rows) if r["grading_method"] == "manual_review" and r["score"] is None]

    graded = 0
    for position, (row_index, row) in enumerate(pending, start=1):
        score = _prompt_for_score(row, position, len(pending), input_fn=input_fn)
        if score is not None:
            rows[row_index]["score"] = score
            graded += 1
            _save_rows(path, rows)  # save after every answer — never lose progress to a mid-session crash

    still_pending = sum(1 for r in rows if r["grading_method"] == "manual_review" and r["score"] is None)
    return graded, still_pending


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_file", type=Path)
    args = parser.parse_args(argv)

    graded, still_pending = review_file(args.results_file)
    print(f"\nGraded {graded} row(s) this session. {still_pending} manual_review row(s) still pending.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
