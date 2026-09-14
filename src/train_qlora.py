"""QLoRA fine-tuning entrypoint: menezesbruno/manaca-1b-base + configs/train.yaml
+ data/train.jsonl -> LoRA adapter checkpoint.

Usage (per specs/001-manaca-instruct-tuning/quickstart.md):

    python -m src.train_qlora --config configs/train.yaml --dataset data/train.jsonl --run-id qlora-v1

Implements FR-002 (QLoRA fine-tuning) using the starting configuration from
research.md §2 / configs/train.yaml. FR-005 budgets exactly one iteration
round (run-id qlora-v2) if the first run misses the FR-004 thresholds.

NOTE: `_build_model()`/`_run_training()` are documented seams, not wired to
real bitsandbytes/peft/trl calls — this file was authored during a
scaffolding-only pass with no GPU execution in scope (tasks.md Phase 4 scope
note). `load_config()` and `load_training_examples()` are the real,
unit-tested parts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from src.schema_validation import validate_instruction_example

REQUIRED_CONFIG_SECTIONS = {"base_model", "quantization", "lora", "training", "output"}


def load_config(config_path: Path) -> dict[str, Any]:
    with config_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    missing = REQUIRED_CONFIG_SECTIONS - config.keys()
    if missing:
        raise ValueError(f"{config_path}: missing required section(s): {sorted(missing)}")

    lora = config["lora"]
    if not (8 <= lora["r"] <= 16):
        raise ValueError(f"lora.r={lora['r']} outside research.md §2's validated range (8-16)")
    if not (16 <= lora["alpha"] <= 32):
        raise ValueError(f"lora.alpha={lora['alpha']} outside research.md §2's validated range (16-32)")

    training = config["training"]
    if not (1 <= training["batch_size"] <= 2):
        raise ValueError(f"training.batch_size={training['batch_size']} outside research.md §2's validated range (1-2)")
    if not (1e-4 <= training["learning_rate"] <= 2e-4):
        raise ValueError(
            f"training.learning_rate={training['learning_rate']} outside research.md §2's validated range (1e-4-2e-4)"
        )
    if not (1 <= training["num_epochs"] <= 3):
        raise ValueError(f"training.num_epochs={training['num_epochs']} outside research.md §2's validated range (1-3)")

    return config


def load_training_examples(dataset_path: Path) -> list[dict]:
    examples = []
    with dataset_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            validate_instruction_example(row)
            examples.append(row)
    return examples


def _format_prompt(example: dict) -> str:
    """### Instrução / ### Entrada / ### Resposta template, per manaca-local-projeto.md §14."""
    parts = [f"### Instrução:\n{example['instruction']}"]
    if example["input"]:
        parts.append(f"### Entrada:\n{example['input']}")
    parts.append(f"### Resposta:\n{example['output']}")
    return "\n\n".join(parts)


def _build_model(config: dict[str, Any]):
    """Seam for real transformers/peft/bitsandbytes model construction — not implemented in this pass."""
    raise NotImplementedError(
        "src/train_qlora.py's _build_model is a documented seam, not yet wired to "
        "transformers/peft/bitsandbytes — see this file's module docstring. "
        "Implement before running a real training pass (tasks.md T038)."
    )


def _run_training(model, tokenizer, examples: list[dict], config: dict[str, Any], output_dir: Path):
    """Seam for the real trl.SFTTrainer training loop — not implemented in this pass."""
    raise NotImplementedError("src/train_qlora.py's _run_training is a documented seam — see _build_model's docstring.")


def train(config_path: Path, dataset_path: Path, run_id: str) -> Path:
    config = load_config(config_path)
    examples = load_training_examples(dataset_path)
    formatted = [_format_prompt(ex) for ex in examples]  # noqa: F841 — consumed by _run_training once wired up

    model, tokenizer = _build_model(config)
    output_dir = Path("adapters") / run_id
    _run_training(model, tokenizer, examples, config, output_dir)
    return output_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)

    output_dir = train(args.config, args.dataset, args.run_id)
    print(f"Adapter written to {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
