"""Orchestrate dataset preparation: combine Agent 1 + Agent 2's filter modules,
add author-reviewed seed rows, drop degenerate/duplicate/eval-overlapping rows,
write train/validation splits, an optional development prompt set, and a report.

Usage (specs/002-data-quality-iteration/quickstart.md):

    python -m src.prepare_dataset --sources alpaca-pt-br canarim --seed-dir data/seed --out-dir data/ \
        --dev-out data/dev/dev_prompts.jsonl

Pipeline order (contracts/dataset-preparation.md): source filters → seed rows → quality
filter → eval-overlap check → dedupe (triple, then pair) → shuffle → cap → split →
dev set → report. Every stage is a pure function over lists of rows, so the whole
orchestration is unit-testable on synthetic rows; only `main()` touches the network.

Feature 001's version deduplicated nothing and its eval-overlap check compared raw
strings that could never match (eval prompts are "instruction: text"); the v2 audit
counted 58 duplicate triples, 25 rows shared with validation and 37 degenerate
answers in the data that was actually trained on. Hence this rewrite.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from src.dataset_filters.grammar_rewriting import filter_grammar_and_rewriting, load_raw_alpaca_pt_br
from src.dataset_filters.open_ended_tasks import filter_open_ended_tasks, load_raw_canarim
from src.dataset_filters.quality import is_degenerate_output
from src.run_manifest import sha256_of
from src.schema_validation import TASK_CATEGORIES, validate_evaluation_prompt, validate_instruction_example
from src.text_normalize import normalize

TARGET_TOTAL_MIN = 3000
TARGET_TOTAL_MAX = 5000
VALIDATION_FRACTION = 0.1
MIN_PER_CATEGORY = 350
DEV_PER_CATEGORY = 10

SEED_SOURCE = "seed-llm"
SOURCE_LICENSES = {
    "alpaca-pt-br": "CC BY-NC-4.0",  # specs/001-manaca-instruct-tuning/research.md §1
    "canarim": "CC BY-NC-4.0",  # idem
    SEED_SOURCE: "author-reviewed synthetic (see data/seed/README.md)",
}

DROP_REASONS = (
    "no_output",
    "exclude_regex",
    "label_not_in_instruction",
    "missing_input",
    "degenerate_output",
    "overlap_with_eval",
    "duplicate_triple",
    "duplicate_pair",
    "over_cap",
)
STAGES = ("raw", "after_filter", "after_quality", "after_eval_dedupe", "after_dedupe", "after_cap", "train", "validation")


@dataclass
class EvalKeys:
    """Normalized forms of every frozen evaluation prompt, in both shapes a training row could collide with."""

    prompts: set[str] = field(default_factory=set)
    pairs: set[tuple[str, str]] = field(default_factory=set)


def _split_prompt(row: dict) -> tuple[str, str]:
    if "instruction" in row and "input" in row:
        return row["instruction"], row["input"]
    instruction, sep, text = row["prompt"].partition(": ")
    return (instruction, text) if sep else (row["prompt"], "")


def _load_eval_prompt_keys(eval_dir: Path) -> EvalKeys:
    keys = EvalKeys()
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
                keys.prompts.add(normalize(row["prompt"]))
                instruction, text = _split_prompt(row)
                keys.pairs.add((normalize(instruction), normalize(text)))
    return keys


def _combined_text(example: dict) -> str:
    return f"{example['instruction']}: {example['input']}" if example["input"] else example["instruction"]


def _dedupe_against_eval(examples: Iterable[dict], eval_keys: EvalKeys, stats: Counter | None = None) -> list[dict]:
    kept = []
    for ex in examples:
        pair = (normalize(ex["instruction"]), normalize(ex["input"]))
        if pair in eval_keys.pairs or normalize(_combined_text(ex)) in eval_keys.prompts:
            if stats is not None:
                stats["overlap_with_eval"] += 1
            continue
        kept.append(ex)
    return kept


def _filter_quality(examples: Iterable[dict], stats: Counter | None = None) -> list[dict]:
    kept = []
    for ex in examples:
        if is_degenerate_output(ex["output"]):
            if stats is not None:
                stats["degenerate_output"] += 1
            continue
        kept.append(ex)
    return kept


def _dedupe_examples(examples: Iterable[dict], stats: Counter | None = None) -> list[dict]:
    """Drop exact-content duplicates before any shuffle, so the result is seed-independent
    and no content can land on both sides of the train/validation split."""
    seen_triples: set[tuple[str, str, str]] = set()
    seen_pairs: set[tuple[str, str]] = set()
    kept = []
    for ex in examples:
        pair = (normalize(ex["instruction"]), normalize(ex["input"]))
        triple = (*pair, normalize(ex["output"]))
        if triple in seen_triples:
            if stats is not None:
                stats["duplicate_triple"] += 1
            continue
        if pair in seen_pairs:
            if stats is not None:
                stats["duplicate_pair"] += 1
            continue
        seen_triples.add(triple)
        seen_pairs.add(pair)
        kept.append(ex)
    return kept


def _cap_per_category(examples: list[dict], target_total: int, stats: Counter | None = None) -> list[dict]:
    """Roughly even split across the 5 categories, capped at target_total overall.

    Seed rows are kept ahead of public rows within a category: the first v3 run
    showed the cap discarding 170 of 197 author-reviewed seed rows (classification
    has ~7,100 public rows for 1,000 slots), which would leave FR-011's four-label
    examples almost absent from the training data. The sort is stable, so the
    seeded shuffle still decides the order inside each group.
    """
    per_category_cap = target_total // len(TASK_CATEGORIES)
    # sorted(): TASK_CATEGORIES is a set, and set iteration order changes with
    # PYTHONHASHSEED between processes. The category order here feeds the seeded
    # split shuffle, so an unsorted dict made two identical runs produce different
    # train/validation files (SC-005 fingerprint check).
    by_category: dict[str, list[dict]] = {c: [] for c in sorted(TASK_CATEGORIES)}
    for ex in examples:
        by_category[ex["task_category"]].append(ex)

    result = []
    for category, rows in by_category.items():
        rows = sorted(rows, key=lambda ex: ex["source"] != SEED_SOURCE)
        result.extend(rows[:per_category_cap])
        if stats is not None:
            stats["over_cap"] += max(0, len(rows) - per_category_cap)
    return result


def _count_by_category(examples: Iterable[dict]) -> Counter:
    return Counter(ex["task_category"] for ex in examples)


def build_dataset(
    raw_alpaca_rows: Iterable[dict],
    raw_canarim_rows: Iterable[dict],
    eval_keys: EvalKeys,
    seed_rows: Iterable[dict] = (),
    target_total: int = TARGET_TOTAL_MAX,
    seed: int = 42,
    stats: Counter | None = None,
    stage_counts: dict[str, Counter] | None = None,
) -> list[dict]:
    """Pure orchestration logic — no network/filesystem access. Fully unit-testable.

    `stats` (drop reasons) and `stage_counts` (per-stage category counts) are filled in
    when given; they feed the preparation report.
    """
    stats = stats if stats is not None else Counter()
    stage_counts = stage_counts if stage_counts is not None else {}

    examples = list(filter_grammar_and_rewriting(raw_alpaca_rows, stats=stats)) + list(
        filter_open_ended_tasks(raw_canarim_rows, stats=stats)
    )
    stage_counts["raw"] = _count_by_category(examples)

    examples = examples + list(seed_rows)
    for ex in examples:
        validate_instruction_example(ex)
    stage_counts["after_filter"] = _count_by_category(examples)

    examples = _filter_quality(examples, stats)
    stage_counts["after_quality"] = _count_by_category(examples)

    examples = _dedupe_against_eval(examples, eval_keys, stats)
    stage_counts["after_eval_dedupe"] = _count_by_category(examples)

    examples = _dedupe_examples(examples, stats)
    stage_counts["after_dedupe"] = _count_by_category(examples)

    rng = random.Random(seed)
    rng.shuffle(examples)

    examples = _cap_per_category(examples, target_total, stats)
    stage_counts["after_cap"] = _count_by_category(examples)

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


def build_dev_prompts(validation: list[dict], per_category: int = DEV_PER_CATEGORY, seed: int = 42) -> list[dict]:
    """Development prompt set (002 FR-005): sampled from the validation split only, never from
    training rows, so tuning decisions are made on data the trainer did not see."""
    rng = random.Random(seed)
    by_category: dict[str, list[dict]] = {c: [] for c in TASK_CATEGORIES}
    for ex in validation:
        by_category[ex["task_category"]].append(ex)

    prompts = []
    for category in sorted(TASK_CATEGORIES):
        rows = by_category[category][:]
        rng.shuffle(rows)
        for n, ex in enumerate(rows[:per_category], start=1):
            prompt = {
                "id": f"dev-{category}-{n:03d}",
                "group": "dev",
                "task_category": category,
                "prompt": _combined_text(ex),
                "instruction": ex["instruction"],
                "input": ex["input"],
                "expected": ex["output"],
                "grading_method": "rule_based" if category == "classification" else "manual_review",
                "source_id": ex["id"],
            }
            validate_evaluation_prompt(prompt)
            prompts.append(prompt)
    return prompts


def _load_seed_rows(seed_dir: Path | None) -> list[dict]:
    if seed_dir is None or not seed_dir.exists():
        return []
    rows = []
    for path in sorted(seed_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                validate_instruction_example(row)
                rows.append(row)
    return rows


def _write_jsonl(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_report(
    *,
    seed: int,
    source_rows_in: dict[str, int],
    train: list[dict],
    validation: list[dict],
    stats: Counter,
    stage_counts: dict[str, Counter],
    fingerprints: dict[str, str],
) -> dict:
    final_rows = train + validation
    kept_by_source = Counter(ex["source"] for ex in final_rows)
    sources = {
        name: {
            "license": SOURCE_LICENSES.get(name, "UNKNOWN — add to SOURCE_LICENSES before use"),
            "rows_in": rows_in,
            "rows_kept": kept_by_source.get(name, 0),
        }
        for name, rows_in in source_rows_in.items()
    }
    train_counts = _count_by_category(train)
    val_counts = _count_by_category(validation)
    by_category = {}
    for category in sorted(TASK_CATEGORIES):
        entry = {stage: stage_counts.get(stage, Counter()).get(category, 0) for stage in STAGES[:-2]}
        entry["train"] = train_counts.get(category, 0)
        entry["validation"] = val_counts.get(category, 0)
        by_category[category] = entry
    warnings = [
        f"{category}: {entry['train'] + entry['validation']} < {MIN_PER_CATEGORY} — remedy per FR-012 "
        "(widen the category's selection with a precision check, then additional public sources), or document the shortfall"
        for category, entry in by_category.items()
        if entry["train"] + entry["validation"] < MIN_PER_CATEGORY
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "seed": seed,
        "sources": sources,
        "by_category": by_category,
        "dropped_by_reason": {reason: stats.get(reason, 0) for reason in DROP_REASONS},
        "fingerprints": fingerprints,
        "warnings": warnings,
    }


def render_report_markdown(report: dict) -> str:
    lines = [
        "# Dataset preparation report",
        "",
        f"Generated {report['generated_at']} (seed {report['seed']}). Stage semantics: `raw` = keyword-matched public rows "
        "with a usable output (after per-source exclusions); `after_filter` = raw + seed rows; then quality filter, "
        "eval-overlap check, dedupe, cap, split.",
        "",
        "## Sources",
        "",
        "| source | license | rows in | rows kept |",
        "|---|---|---:|---:|",
    ]
    for name, entry in report["sources"].items():
        lines.append(f"| {name} | {entry['license']} | {entry['rows_in']} | {entry['rows_kept']} |")
    lines += ["", "## Per category", "", "| category | " + " | ".join(STAGES) + " |", "|---|" + "---:|" * len(STAGES)]
    for category, entry in report["by_category"].items():
        lines.append(f"| {category} | " + " | ".join(str(entry[stage]) for stage in STAGES) + " |")
    lines += ["", "## Dropped by reason", "", "| reason | rows |", "|---|---:|"]
    for reason, count in report["dropped_by_reason"].items():
        lines.append(f"| {reason} | {count} |")
    lines += ["", "## Fingerprints", ""]
    for path, digest in report["fingerprints"].items():
        lines.append(f"- `{path}`: `{digest}`")
    lines += ["", "## Warnings", ""]
    lines += [f"- {w}" for w in report["warnings"]] or ["- none"]
    return "\n".join(lines) + "\n"


def write_report(report: dict, out_dir: Path) -> None:
    (out_dir / "dataset_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "dataset_report.md").write_text(render_report_markdown(report), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", nargs="+", default=["alpaca-pt-br", "canarim"])
    parser.add_argument("--seed-dir", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=Path("data"))
    parser.add_argument("--dev-out", type=Path, default=None)
    parser.add_argument("--dev-per-category", type=int, default=DEV_PER_CATEGORY)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    eval_keys = _load_eval_prompt_keys(args.out_dir / "eval")
    seed_rows = _load_seed_rows(args.seed_dir)

    print("Downloading raw datasets (network access required)...")
    raw_alpaca = load_raw_alpaca_pt_br() if "alpaca-pt-br" in args.sources else []
    raw_canarim = load_raw_canarim() if "canarim" in args.sources else []

    stats: Counter = Counter()
    stage_counts: dict[str, Counter] = {}
    examples = build_dataset(
        raw_alpaca, raw_canarim, eval_keys, seed_rows=seed_rows, seed=args.seed, stats=stats, stage_counts=stage_counts
    )
    train, validation = split_train_validation(examples, seed=args.seed)

    train_path = args.out_dir / "train.jsonl"
    validation_path = args.out_dir / "validation.jsonl"
    _write_jsonl(train, train_path)
    _write_jsonl(validation, validation_path)

    if args.dev_out is not None:
        _write_jsonl(build_dev_prompts(validation, args.dev_per_category, seed=args.seed), args.dev_out)

    source_rows_in = {}
    if "alpaca-pt-br" in args.sources:
        source_rows_in["alpaca-pt-br"] = len(raw_alpaca)
    if "canarim" in args.sources:
        source_rows_in["canarim"] = len(raw_canarim)
    if seed_rows:
        source_rows_in[SEED_SOURCE] = len(seed_rows)

    report = build_report(
        seed=args.seed,
        source_rows_in=source_rows_in,
        train=train,
        validation=validation,
        stats=stats,
        stage_counts=stage_counts,
        fingerprints={str(train_path): sha256_of(train_path), str(validation_path): sha256_of(validation_path)},
    )
    write_report(report, args.out_dir)

    print(f"Wrote {len(train)} training examples and {len(validation)} validation examples.")
    for warning in report["warnings"]:
        print(f"WARNING: {warning}", file=sys.stderr)
    if not (TARGET_TOTAL_MIN <= len(examples) <= TARGET_TOTAL_MAX):
        print(
            f"WARNING: total example count {len(examples)} is outside the target "
            f"{TARGET_TOTAL_MIN}-{TARGET_TOTAL_MAX} range from the Clarifications session.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
