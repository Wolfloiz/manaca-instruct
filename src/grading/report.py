"""Per-run, per-category grading report over evaluation results files
(specs/002-data-quality-iteration/contracts/blind-review-and-report.md).

Usage:
    python -m src.grading.report eval/results/qlora-v2-blind.jsonl eval/results/qlora-v2-split-blind.jsonl \\
        --pair qlora-v2 qlora-v2-split --markdown-out eval/results/presentation-experiment.md

Reports two metrics side by side because the qlora-v2 audit found that the
partial-credit mean alone hid that only 7/80 group-A answers were fully correct:
`mean` (0.5 counts half) and `full_rate` (share graded exactly 1). Never mixes
rows from different run ids into one aggregate (001's consumer rule), never
drops still-ungraded rows silently (`n_null`), and marks which runs were graded
under the blind protocol so the model card cannot present the two as equivalent.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from src.schema_validation import TASK_CATEGORIES

CATEGORY_ORDER = ["grammar_correction", "classification", "rewriting", "summarization", "simplification", "grupo_b"]
BLIND_SUFFIX = "-blind"
BLIND_RUN_PREFIX = "qlora-v3"
FOOTNOTE = "Means include partial credit (0.5); `full_rate` counts only answers graded 1."


def _load_run(path: Path) -> tuple[str, list[dict]]:
    with path.open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    run_ids = {r["run_id"] for r in rows}
    if len(run_ids) != 1:
        raise ValueError(f"{path}: one results file must hold exactly one run_id, found {sorted(run_ids)}")
    return run_ids.pop(), rows


def _category_of(row: dict) -> str:
    return row["task_category"] if row["task_category"] in TASK_CATEGORIES else "grupo_b"


def protocol_for(path: Path, run_id: str) -> str:
    if path.stem.endswith(BLIND_SUFFIX) or run_id.startswith(BLIND_RUN_PREFIX):
        return "blind"
    return "earlier (non-blind)"


def summarize_run(rows: list[dict]) -> dict[str, dict]:
    """{category: {n, mean, full_rate, n1, n05, n0, n_null}} over one run's rows."""
    by_category: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_category[_category_of(row)].append(row)
    summary = {}
    for category, group in by_category.items():
        scores = [r["score"] for r in group if r["score"] is not None]
        summary[category] = {
            "n": len(group),
            "mean": sum(scores) / len(scores) if scores else None,
            "full_rate": sum(1 for s in scores if s == 1) / len(scores) if scores else None,
            "n1": sum(1 for s in scores if s == 1),
            "n05": sum(1 for s in scores if s == 0.5),
            "n0": sum(1 for s in scores if s == 0),
            "n_null": len(group) - len(scores),
        }
    return summary


def compare_runs(rows_a: list[dict], rows_b: list[dict]) -> dict[str, dict]:
    """Per category: improved / worsened / tied / not_comparable from A to B on shared prompt ids."""
    scores_b = {r["id"]: r["score"] for r in rows_b}
    result: dict[str, dict] = defaultdict(lambda: {"improved": 0, "worsened": 0, "tied": 0, "not_comparable": 0})
    for row in rows_a:
        if row["id"] not in scores_b:
            continue
        bucket = result[_category_of(row)]
        a, b = row["score"], scores_b[row["id"]]
        if a is None or b is None:
            bucket["not_comparable"] += 1
        elif b > a:
            bucket["improved"] += 1
        elif b < a:
            bucket["worsened"] += 1
        else:
            bucket["tied"] += 1
    return dict(result)


def _fmt(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def render_markdown(runs: list[tuple[Path, str, list[dict]]], pairs: list[tuple[str, str]]) -> str:
    lines = ["| run | protocol | category | n | mean | full_rate | n1 | n05 | n0 | n_null |", "|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for path, run_id, rows in runs:
        summary = summarize_run(rows)
        protocol = protocol_for(path, run_id)
        for category in CATEGORY_ORDER:
            if category not in summary:
                continue
            s = summary[category]
            extra = f" ({s['n1']}/{s['n']} correct)" if category == "classification" else ""
            lines.append(
                f"| {run_id} | {protocol} | {category} | {s['n']} | {_fmt(s['mean'])} | {_fmt(s['full_rate'])}{extra} "
                f"| {s['n1']} | {s['n05']} | {s['n0']} | {s['n_null']} |"
            )

    by_run_id = {run_id: rows for _, run_id, rows in runs}
    for a, b in pairs:
        if a not in by_run_id or b not in by_run_id:
            raise ValueError(f"--pair {a} {b}: both run ids must be among the loaded files ({sorted(by_run_id)})")
        lines += ["", f"### {a} → {b}", "", "| category | improved | worsened | tied | not comparable |", "|---|---:|---:|---:|---:|"]
        comparison = compare_runs(by_run_id[a], by_run_id[b])
        for category in CATEGORY_ORDER:
            if category in comparison:
                c = comparison[category]
                lines.append(f"| {category} | {c['improved']} | {c['worsened']} | {c['tied']} | {c['not_comparable']} |")

    lines += ["", "Files: " + ", ".join(str(p) for p, _, _ in runs), "", FOOTNOTE, ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("results_files", type=Path, nargs="+")
    parser.add_argument("--pair", nargs=2, action="append", default=[], metavar=("RUN_A", "RUN_B"))
    parser.add_argument("--markdown-out", type=Path, default=None)
    args = parser.parse_args(argv)

    runs = []
    seen: dict[str, Path] = {}
    for path in args.results_files:
        run_id, rows = _load_run(path)
        if run_id in seen:
            raise SystemExit(
                f"run_id {run_id!r} appears in both {seen[run_id]} and {path}; pass only one of an original/-blind pair"
            )
        seen[run_id] = path
        runs.append((path, run_id, rows))

    markdown = render_markdown(runs, [tuple(p) for p in args.pair])
    print(markdown)
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(markdown, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
