"""Run the fixed evaluation prompt set against a given model and record results.

Usage (per specs/001-manaca-instruct-tuning/quickstart.md):

    python -m src.evaluate --model manaca-1b-base \
        --prompts data/eval/grupo_a_prompts.jsonl data/eval/grupo_b_prompts.jsonl \
        --run-id baseline --out eval/results/baseline.jsonl

    python -m src.evaluate --model manaca-instruct-pt --adapter adapters/qlora-v1 \
        --prompts data/eval/grupo_a_prompts.jsonl data/eval/grupo_b_prompts.jsonl \
        --run-id qlora-v1 --out eval/results/qlora-v1.jsonl

    # feature 002: present grupo_a prompts in the training structure (### Instrução / ### Entrada)
    python -m src.evaluate --model manaca-instruct-pt --adapter adapters/qlora-v2 \
        --prompts data/eval/grupo_a_prompts.jsonl data/eval/grupo_b_prompts.jsonl \
        --prompt-format split --run-id qlora-v2-split --out eval/results/qlora-v2-split.jsonl

Every run also writes `<out>.manifest.json` next to the results (specs/002
contracts/run-manifest-schema.md, evaluation fields) so a result file can be
traced to its adapter, prompt presentation, inference config and code version.

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
from src.run_manifest import build_manifest, write_manifest
from src.schema_validation import RULE_BASED_CATEGORIES, validate_evaluation_prompt, validate_evaluation_result

KNOWN_MODELS = {
    "manaca-1b-base": "menezesbruno/manaca-1b-base",
    "manaca-instruct-pt": None,  # base model + --adapter path, resolved at load time
    "manaca-1b-instruct": "menezesbruno/manaca-1b-instruct",
}

DEFAULT_INFERENCE_CONFIG_PATH = Path("configs/inference.yaml")

PROMPT_FORMATS = ("combined", "split")


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


def _format_row_prompt(row: dict, prompt_format: str) -> str:
    """`combined` = the frozen single-line prompt (feature 001's presentation); `split` = the
    authored instruction/input annotation rendered in the training structure (002 FR-003).

    A grupo_a row without the split fields is an error under `split`, not a silent fallback —
    mixing presentations inside one run would make the run id lie about what was measured.
    grupo_b rows never carry the fields and always use the combined form.
    """
    if prompt_format == "combined":
        return _format_inference_prompt(row["prompt"])
    if prompt_format != "split":
        raise ValueError(f"prompt_format must be one of {PROMPT_FORMATS}, got {prompt_format!r}")
    if "instruction" in row:
        return format_prompt(row["instruction"], row["input"])
    if row["group"] == "grupo_b":
        return _format_inference_prompt(row["prompt"])
    raise ValueError(
        f"{row['id']}: --prompt-format split requires instruction/input fields on every grupo_a row "
        "(see specs/002-data-quality-iteration/contracts/evaluation-presentation.md)"
    )


def _load_inference_config(path: Path = DEFAULT_INFERENCE_CONFIG_PATH) -> dict:
    if not path.exists():
        return {"max_new_tokens": 256, "do_sample": False, "temperature": 1.0, "top_p": 1.0, "repetition_penalty": 1.1}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _base_repo_for(model_name: str) -> str:
    return KNOWN_MODELS["manaca-1b-base"] if model_name == "manaca-instruct-pt" else KNOWN_MODELS[model_name]


def _load_model(model_name: str, adapter_path: str | None, inference_config_path: Path = DEFAULT_INFERENCE_CONFIG_PATH):
    """Load a model+tokenizer via transformers, optionally with a LoRA adapter via peft.

    Per manaca-local-projeto.md's own baseline example (§2.6/§12): bfloat16,
    device_map="auto" so it lands on the GPU when CUDA is available.
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if model_name == "manaca-instruct-pt" and adapter_path is None:
        raise ValueError("manaca-instruct-pt requires --adapter")
    base_repo = _base_repo_for(model_name)

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
    inference_config = _load_inference_config(inference_config_path)
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


def run_evaluation(
    model_key: str,
    adapter_path: str | None,
    prompt_files: list[Path],
    run_id: str,
    prompt_format: str = "combined",
    inference_config_path: Path = DEFAULT_INFERENCE_CONFIG_PATH,
) -> list[dict]:
    if model_key not in KNOWN_MODELS:
        raise ValueError(f"Unknown --model {model_key!r}; must be one of {sorted(KNOWN_MODELS)}")
    if prompt_format not in PROMPT_FORMATS:
        raise ValueError(f"Unknown --prompt-format {prompt_format!r}; must be one of {PROMPT_FORMATS}")

    model, tokenizer, inference_config = _load_model(model_key, adapter_path, inference_config_path)

    results = []
    for prompt_row in _read_prompts(prompt_files):
        formatted_prompt = _format_row_prompt(prompt_row, prompt_format)
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


def _adapter_manifest_path(adapter_path: str | None) -> str | None:
    if adapter_path is None:
        return None
    for candidate in (Path(adapter_path) / "run_manifest.json", Path(adapter_path).parent / "run_manifest.json"):
        if candidate.exists():
            return str(candidate)
    return None


def write_evaluation_manifest(
    out_path: Path,
    *,
    model_key: str,
    adapter_path: str | None,
    prompt_files: list[Path],
    run_id: str,
    prompt_format: str,
    inference_config_path: Path,
    rows_written: int,
) -> Path:
    """`<out>.manifest.json` per specs/002 contracts/run-manifest-schema.md (evaluation fields)."""
    manifest_path = out_path.with_suffix(".manifest.json")
    is_checkpoint = adapter_path is not None and "checkpoint-" in Path(adapter_path).name
    manifest = build_manifest(
        "evaluation",
        run_id,
        base_model=_base_repo_for(model_key),
        datasets=[Path(p) for p in prompt_files],
        config=_load_inference_config(inference_config_path),
        prompt_format=prompt_format,
        model=model_key,
        adapter_path=None if adapter_path is None else str(adapter_path),
        checkpoint=str(adapter_path) if is_checkpoint else None,
        adapter_manifest=_adapter_manifest_path(adapter_path),
        inference_config_path=str(inference_config_path),
        prompt_files=[str(p) for p in prompt_files],
        results_path=str(out_path),
        rows_written=rows_written,
    )
    write_manifest(manifest_path, manifest)
    return manifest_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=sorted(KNOWN_MODELS))
    parser.add_argument("--adapter", default=None, help="LoRA adapter path, required when --model manaca-instruct-pt")
    parser.add_argument("--prompts", nargs="+", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--prompt-format", choices=PROMPT_FORMATS, default="combined")
    parser.add_argument("--inference-config", type=Path, default=DEFAULT_INFERENCE_CONFIG_PATH)
    args = parser.parse_args(argv)

    if args.model == "manaca-instruct-pt" and not args.adapter:
        parser.error("--adapter is required when --model manaca-instruct-pt")

    results = run_evaluation(
        args.model, args.adapter, args.prompts, args.run_id, args.prompt_format, args.inference_config
    )
    write_results_jsonl(results, args.out)
    manifest_path = write_evaluation_manifest(
        args.out,
        model_key=args.model,
        adapter_path=args.adapter,
        prompt_files=args.prompts,
        run_id=args.run_id,
        prompt_format=args.prompt_format,
        inference_config_path=args.inference_config,
        rows_written=len(results),
    )
    print(f"Wrote {len(results)} results to {args.out} (manifest: {manifest_path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
