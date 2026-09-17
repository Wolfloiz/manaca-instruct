"""Interactive CLI to manually grade the manual_review rows in evaluation results files.

Per contracts/evaluation-results-schema.md: src/evaluate.py writes manual_review
rows with score: null; this is the only component permitted to fill them in
(data-model.md's validation rule against silent defaulting). Never auto-scores —
every row requires an explicit human judgment (1 = correct, 0.5 = partial,
0 = incorrect), matching the rubric in spec.md's FR-004.

Usage:
    python -m src.grading.review_cli eval/results/baseline.jsonl            # feature 001 mode: grades in place
    python -m src.grading.review_cli eval/results/qlora-v2.jsonl eval/results/qlora-v2-split.jsonl \\
        --blind --interleave --shuffle-seed 7                                # feature 002 mode

Feature 002 (specs/002 contracts/blind-review-and-report.md): `--blind` hides the
model, run id and file name from the reviewer; `--interleave` mixes several runs
into one session so the reviewer cannot tell which run an answer belongs to; and
in either of those modes grades are written to a `<run_id>-blind.jsonl` sibling
copy — the input files are never modified (002 FR-022), and their SHA256 is
printed before and after the session to prove it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

VALID_SCORES = {"1": 1.0, "0.5": 0.5, "0": 0.0}
BLIND_SUFFIX = "-blind"


class _QuitSession(Exception):
    pass


def _load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _save_rows(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prompt_for_score(row: dict, index: int, total: int, input_fn=input, blind: bool = False) -> float | None:
    """Returns a score, None for skip; raises _QuitSession on 'q'."""
    if blind:
        print(f"\n[{index}/{total}] task_category={row['task_category']}")
    else:
        print(f"\n[{index}/{total}] id={row['id']} task_category={row['task_category']} model={row['model']}")
    print(f"Prompt:   {row['prompt']}")
    if row.get("expected"):
        print(f"Expected: {row['expected']}")
    print(f"Output:   {row['output']}")
    while True:
        answer = input_fn("Score (1=correct, 0.5=partial, 0=incorrect, s=skip for now, q=quit): ").strip().lower()
        if answer == "s":
            return None
        if answer == "q":
            raise _QuitSession
        if answer in VALID_SCORES:
            return VALID_SCORES[answer]
        print("Please enter 1, 0.5, 0, s, or q.")


def _is_pending(row: dict) -> bool:
    return row["grading_method"] == "manual_review" and row["score"] is None


def review_file(path: Path, input_fn=input) -> tuple[int, int]:
    """Feature 001 in-place mode. Returns (graded_count, still_pending_count)."""
    rows = _load_rows(path)
    pending = [(i, r) for i, r in enumerate(rows) if _is_pending(r)]

    graded = 0
    try:
        for position, (row_index, row) in enumerate(pending, start=1):
            score = _prompt_for_score(row, position, len(pending), input_fn=input_fn)
            if score is not None:
                rows[row_index]["score"] = score
                graded += 1
                _save_rows(path, rows)  # save after every answer — never lose progress to a mid-session crash
    except _QuitSession:
        pass

    still_pending = sum(1 for r in rows if _is_pending(r))
    return graded, still_pending


def blind_output_path(input_path: Path) -> Path:
    if input_path.stem.endswith(BLIND_SUFFIX):
        raise ValueError(f"{input_path} is already a blind result file; pass the original run file instead")
    return input_path.with_name(f"{input_path.stem}{BLIND_SUFFIX}{input_path.suffix}")


def _load_or_create_blind_copy(input_path: Path) -> tuple[Path, list[dict]]:
    """The -blind sibling starts as a full copy with manual_review scores reset to null;
    rule_based scores are kept (they were computed, not judged). Resumed as-is if present."""
    out_path = blind_output_path(input_path)
    if out_path.exists():
        return out_path, _load_rows(out_path)
    rows = _load_rows(input_path)
    for row in rows:
        if row["grading_method"] == "manual_review":
            row["score"] = None
    _save_rows(out_path, rows)
    return out_path, rows


def review_blind(
    input_paths: list[Path], input_fn=input, shuffle_seed: int | None = None, blind: bool = True
) -> dict[Path, tuple[int, int]]:
    """Feature 002 mode: grade one or more runs into their `-blind` siblings, never touching the inputs.

    Returns {output_path: (graded_count, still_pending_count)} per input, in input order.
    """
    before = {p: _sha256(p) for p in input_paths}
    outputs: dict[Path, tuple[Path, list[dict]]] = {p: _load_or_create_blind_copy(p) for p in input_paths}

    pending: list[tuple[Path, int]] = [
        (in_path, i) for in_path, (_, rows) in outputs.items() for i, r in enumerate(rows) if _is_pending(r)
    ]
    if shuffle_seed is not None:
        random.Random(shuffle_seed).shuffle(pending)

    graded = {p: 0 for p in input_paths}
    try:
        for position, (in_path, row_index) in enumerate(pending, start=1):
            out_path, rows = outputs[in_path]
            score = _prompt_for_score(rows[row_index], position, len(pending), input_fn=input_fn, blind=blind)
            if score is not None:
                rows[row_index]["score"] = score
                graded[in_path] += 1
                _save_rows(out_path, rows)
    except _QuitSession:
        pass

    summary: dict[Path, tuple[int, int]] = {}
    for in_path in input_paths:
        out_path, rows = outputs[in_path]
        summary[out_path] = (graded[in_path], sum(1 for r in rows if _is_pending(r)))
        after = _sha256(in_path)
        status = "unchanged" if after == before[in_path] else "MODIFIED — this must not happen"
        print(f"{in_path}: sha256 before={before[in_path][:12]}… after={after[:12]}… ({status})")
        if after != before[in_path]:
            raise RuntimeError(f"{in_path} changed during a blind session (002 FR-022)")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("results_files", type=Path, nargs="+")
    parser.add_argument("--blind", action="store_true", help="hide model/run id/file name; write grades to <run>-blind.jsonl")
    parser.add_argument("--interleave", action="store_true", help="grade several runs in one mixed session (writes -blind files)")
    parser.add_argument("--shuffle-seed", type=int, default=None, help="deterministic presentation order; required with --interleave")
    args = parser.parse_args(argv)

    if args.interleave and args.shuffle_seed is None:
        parser.error("--interleave requires --shuffle-seed")
    if len(args.results_files) > 1 and not args.interleave:
        parser.error("several results files require --interleave")

    if args.blind or args.interleave:
        summary = review_blind(args.results_files, shuffle_seed=args.shuffle_seed, blind=True)
        for out_path, (graded, still_pending) in summary.items():
            print(f"{out_path}: graded {graded} this session, {still_pending} still pending")
        return 0

    graded, still_pending = review_file(args.results_files[0])
    print(f"\nGraded {graded} row(s) this session. {still_pending} manual_review row(s) still pending.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
