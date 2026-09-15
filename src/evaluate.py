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

`_load_model`/`_generate` use deferred imports (torch/transformers/peft loaded
inside the function, not at module level) so this module stays importable —
and unit-testable — without those heavy dependencies installed; only a real
run needs them (tasks.md T024/T039/T040).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Iterator

import yaml

from src.grading.rule_based import score_rule_based
from src.prompt_format import format_prompt
from src.schema_validation import RULE_BASED_CATEGORIES, validate_evaluation_prompt, validate_evaluation_result

KNOWN_MODELS = {
    "manaca-1b-base": "menezesbruno/manaca-1b-base",
    "manaca-instruct-pt": None,  # base model + --adapter path, resolved at load time
    "manaca-1b-instruct": "menezesbruno/manaca-1b-instruct",
}

DEFAULT_INFERENCE_CONFIG_PATH = Path("configs/inference.yaml")


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


def _format_inference_prompt(prompt_text: str) -> str:
    """### Instrução / ### Resposta template, via the shared src/prompt_format.py.

    Applied uniformly to all three evaluated models (base, our instruct, and the
    official instruct release) for a controlled comparison. This is what
    manaca-instruct-pt was actually fine-tuned to expect (train_qlora.py formats
    every training example the same way) — evaluating it without this template
    would unfairly handicap it relative to the untuned base model, which doesn't
    care about the template either way. The official menezesbruno/manaca-1b-instruct
    release may have been trained on a different (e.g. Alpaca-style) template, so
    this is a known, documented limitation of the three-way comparison, not an
    oversight — see MODEL_CARD.md's Known limitations section.
    """
    return format_prompt(prompt_text)


def _load_inference_config(path: Path = DEFAULT_INFERENCE_CONFIG_PATH) -> dict:
    if not path.exists():
        return {"max_new_tokens": 256, "do_sample": False, "temperature": 1.0, "top_p": 1.0, "repetition_penalty": 1.1}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_model(model_name: str, adapter_path: str | None):
    """Load a model+tokenizer via transformers, optionally with a LoRA adapter via peft.

    Per manaca-local-projeto.md's own baseline example (§2.6/§12): bfloat16,
    device_map="auto" so it lands on the GPU when CUDA is available.
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if model_name == "manaca-instruct-pt":
        if adapter_path is None:
            raise ValueError("manaca-instruct-pt requires --adapter")
        base_repo = KNOWN_MODELS["manaca-1b-base"]
    else:
        base_repo = KNOWN_MODELS[model_name]

    tokenizer = AutoTokenizer.from_pretrained(base_repo)
    model = AutoModelForCausalLM.from_pretrained(
        base_repo,
        dtype=torch.bfloat16,
        device_map="auto",
    )

    if model_name == "manaca-instruct-pt":
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, adapter_path)

    model.eval()
    inference_config = _load_inference_config()
    return model, tokenizer, inference_config


def _generate(model, tokenizer, prompt: str, inference_config: dict) -> tuple[str, float]:
    """Generate a response and return (output_text, latency_ms).

    Decodes only the newly generated tokens (not the echoed prompt), matching
    what a downloader following the model card's usage snippet would see.
    """
    import torch

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    prompt_length = inputs["input_ids"].shape[1]

    start = time.monotonic()
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=inference_config.get("max_new_tokens", 256),
            do_sample=inference_config.get("do_sample", False),
            temperature=inference_config.get("temperature", 1.0),
            top_p=inference_config.get("top_p", 1.0),
            repetition_penalty=inference_config.get("repetition_penalty", 1.0),
            no_repeat_ngram_size=inference_config.get("no_repeat_ngram_size", 0),
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        )
    latency_ms = (time.monotonic() - start) * 1000

    generated_tokens = output[0][prompt_length:]
    text = tokenizer.decode(generated_tokens, skip_special_tokens=True)
    return text.strip(), latency_ms


def run_evaluation(model_key: str, adapter_path: str | None, prompt_files: list[Path], run_id: str) -> list[dict]:
    if model_key not in KNOWN_MODELS:
        raise ValueError(f"Unknown --model {model_key!r}; must be one of {sorted(KNOWN_MODELS)}")

    model, tokenizer, inference_config = _load_model(model_key, adapter_path)

    results = []
    for prompt_row in _read_prompts(prompt_files):
        formatted_prompt = _format_inference_prompt(prompt_row["prompt"])
        output, latency_ms = _generate(model, tokenizer, formatted_prompt, inference_config)

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
