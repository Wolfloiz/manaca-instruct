"""QLoRA fine-tuning entrypoint: menezesbruno/manaca-1b-base + configs/train.yaml
+ data/train.jsonl -> LoRA adapter checkpoint.

Usage (per specs/001-manaca-instruct-tuning/quickstart.md):

    python -m src.train_qlora --config configs/train.yaml --dataset data/train.jsonl --run-id qlora-v1

Implements FR-002 (QLoRA fine-tuning) using the starting configuration from
research.md §2 / configs/train.yaml. FR-005 budgets exactly one iteration
round (run-id qlora-v2) if the first run misses the FR-004 thresholds.

Heavy ML dependencies (torch/transformers/peft/bitsandbytes/trl/datasets) are
imported lazily inside the seam functions so this module stays importable in
test environments without the CUDA stack; install requirements.txt before a
real training run (tasks.md T038).
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
    """Load the 4-bit quantized base model + tokenizer and wrap it with LoRA (research.md §2).

    Returns a `peft.PeftModel` (via `get_peft_model`). Requires the CUDA torch
    build + bitsandbytes/peft/transformers from requirements.txt; imports are
    deferred so tests without the ML stack don't need them.
    """
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    quant = config["quantization"]
    compute_dtype = getattr(torch, quant.get("bnb_4bit_compute_dtype", "bfloat16"))
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=quant.get("load_in_4bit", True),
        bnb_4bit_quant_type=quant.get("bnb_4bit_quant_type", "nf4"),
        bnb_4bit_compute_dtype=compute_dtype,
    )

    model = AutoModelForCausalLM.from_pretrained(
        config["base_model"],
        quantization_config=bnb_config,
        device_map="auto",
        dtype=compute_dtype,
        # no trust_remote_code: menezesbruno/manaca-1b-base is a standard LlamaForCausalLM
        # (confirmed via its config.json — no auto_map/custom modeling code), so there's
        # no reason to grant arbitrary code execution from the repo.
    )
    model.config.use_cache = False

    tokenizer = AutoTokenizer.from_pretrained(config["base_model"])
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    lora = config["lora"]
    lora_config = LoraConfig(
        r=lora["r"],
        lora_alpha=lora["alpha"],
        lora_dropout=lora["dropout"],
        target_modules=lora["target_modules"],
        task_type="CAUSAL_LM",
    )
    return get_peft_model(model, lora_config), tokenizer


def _run_training(model, tokenizer, examples: list[dict], config: dict[str, Any], output_dir: Path):
    """Run the SFT training loop and save the adapter + tokenizer to output_dir.

    Uses `trl.SFTTrainer` with the `### Instrução/### Entrada/### Resposta`
    prompt template from `_format_prompt`, a configuration validated against
    research.md §2's ranges by `load_config`. The 4-bit-loaded base model is
    kept frozen by the PeftModel wrapper — only the LoRA adapters train.
    """
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer

    train = config["training"]

    # trl >=1.0's SFTTrainer moved dataset_text_field/max_length (renamed from
    # max_seq_length) onto SFTConfig, and renamed the tokenizer kwarg to
    # processing_class — this is the current API, not trl 0.9.x's (verified
    # against the actually-installed trl 1.13.0; requirements.txt's pin was
    # updated to match, see its comment).
    training_args = SFTConfig(
        output_dir=str(output_dir),
        per_device_train_batch_size=train["batch_size"],
        gradient_accumulation_steps=train["gradient_accumulation_steps"],
        learning_rate=train["learning_rate"],
        num_train_epochs=train["num_epochs"],
        optim=train["optimizer"],
        save_strategy="epoch",
        logging_steps=10,
        report_to=[],  # no external experiment trackers
        bf16=True,  # matches configs/train.yaml's bnb_4bit_compute_dtype (bfloat16) — fp16 here would
        # fight the bf16-loaded model's dtype (mismatched autocast/GradScaler assumptions)
        seed=42,
        max_length=train["max_seq_length"],
        dataset_text_field="text",
    )

    dataset = Dataset.from_list([{"text": _format_prompt(ex)} for ex in examples])

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        args=training_args,
        train_dataset=dataset,
    )
    trainer.train()
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)


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
