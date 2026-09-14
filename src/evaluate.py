"""Run the fixed evaluation prompt set against a given model and record results.

Usage (per specs/001-manaca-instruct-tuning/quickstart.md):

    python -m src.evaluate --model manaca-1b-base \
        --prompts data/eval/grupo_a_prompts.jsonl data/eval/grupo_b_prompts.jsonl \
        --run-id baseline --out eval/results/baseline.jsonl

    python -m src.evaluate --model manaca-instruct-pt --adapter adapters/qlora-v1 \
        --prompts data/eval/grupo_a_prompts.jsonl data/eval/grupo_b_prompts.jsonl \
        --run-id qlora-v1 --out eval/results/qlora-v1.jsonl

Implements FR-001/FR-003/FR-004 and the contracts/evaluation-results-schema.md
producer rules: rule_based rows are scored immediately; manual_review rows are
written with score: null for src/grading/review_cli.py to fill in later.

NOTE: model loading/generation is intentionally left as a documented seam
(`_load_model`, `_generate`) rather than implemented against real HF weights —
this file was authored during a scaffolding-only pass with no model downloads
or GPU execution in scope (see specs/001-manaca-instruct-tuning/tasks.md,
Phase 3). Wire `_load_model`/`_generate` to `transformers`/`peft` before the
first real run (T024).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Iterator

from src.grading.rule_based import score_rule_based
from src.schema_validation import RULE_BASED_CATEGORIES, validate_evaluation_prompt, validate_evaluation_result

KNOWN_MODELS = {
    "manaca-1b-base": "menezesbruno/manaca-1b-base",
    "manaca-instruct-pt": None,  # base model + --adapter path, resolved at load time
    "manaca-1b-instruct": "menezesbruno/manaca-1b-instruct",
}


def _read_prompts(paths: list[Path]) -> Iterator[dict]:
    for path in paths:
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                validate_evaluation_prompt(row)
                yield row


def _load_model(model_name: str, adapter_path: str | None):
    """Seam for the real transformers/peft loading code — not implemented in this pass."""
    raise NotImplementedError(
        "src/evaluate.py's _load_model is a documented seam, not yet wired to transformers/peft — "
        "see this file's module docstring. Implement before running against real weights (tasks.md T024/T039/T040)."
    )


def _generate(model, tokenizer, prompt: str, inference_config: dict) -> tuple[str, float]:
    """Seam for real generation — returns (output_text, latency_ms). Not implemented in this pass."""
    raise NotImplementedError("src/evaluate.py's _generate is a documented seam — see _load_model's docstring.")


def run_evaluation(model_key: str, adapter_path: str | None, prompt_files: list[Path], run_id: str) -> list[dict]:
    if model_key not in KNOWN_MODELS:
        raise ValueError(f"Unknown --model {model_key!r}; must be one of {sorted(KNOWN_MODELS)}")

    model, tokenizer, inference_config = _load_model(model_key, adapter_path)

    results = []
    for prompt_row in _read_prompts(prompt_files):
        output, latency_ms = _generate(model, tokenizer, prompt_row["prompt"], inference_config)

        result = {
            "id": prompt_row["id"],
            "task_category": prompt_row["task_category"],
            "model": model_key,
            "prompt": prompt_row["prompt"],
            "expected": prompt_row["expected"],
            "output": output,
            "grading_method": prompt_row["grading_method"],
            "run_id": run_id,
            "latency_ms": latency_ms,
        }

        if prompt_row["grading_method"] == "rule_based":
            if prompt_row["task_category"] not in RULE_BASED_CATEGORIES:
                raise ValueError(
                    f"{prompt_row['id']}: grading_method is rule_based but task_category "
                    f"{prompt_row['task_category']!r} is not in {sorted(RULE_BASED_CATEGORIES)}"
                )
            result["score"] = score_rule_based(prompt_row["task_category"], output, prompt_row["expected"])
        else:
            result["score"] = None  # filled in later by src/grading/review_cli.py

        validate_evaluation_result(result)
        results.append(result)

    return results


def write_results_jsonl(results: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in results:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=sorted(KNOWN_MODELS))
    parser.add_argument("--adapter", default=None, help="LoRA adapter path, required when --model manaca-instruct-pt")
    parser.add_argument("--prompts", nargs="+", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    if args.model == "manaca-instruct-pt" and not args.adapter:
        parser.error("--adapter is required when --model manaca-instruct-pt")

    results = run_evaluation(args.model, args.adapter, args.prompts, args.run_id)
    write_results_jsonl(results, args.out)
    print(f"Wrote {len(results)} results to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
