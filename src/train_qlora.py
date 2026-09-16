"""QLoRA fine-tuning entrypoint: menezesbruno/manaca-1b-base + configs/train.yaml
+ data/train.jsonl -> LoRA adapter checkpoint.

Usage (per specs/001-manaca-instruct-tuning/quickstart.md):

    python -m src.train_qlora --config configs/train.yaml --dataset data/train.jsonl \
        --validation data/validation.jsonl --run-id qlora-v3a

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
import math
import sys
from pathlib import Path
from typing import Any

import yaml

from src.prompt_format import format_prompt
from src.run_manifest import build_manifest, write_manifest
from src.schema_validation import validate_instruction_example
from src.text_normalize import normalize

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
    # Feature 001 configs did not contain this switch.  Keep their objective
    # byte-for-byte compatible unless a v3 run opts in explicitly.
    training.setdefault("completion_only_loss", False)
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
    """The shared training/evaluation template, including the target response."""
    return format_prompt(example["instruction"], example["input"], example["output"])


def _assert_no_overlap(train_examples: list[dict], validation_examples: list[dict]) -> None:
    """Reject a held-out set that leaks a normalized instruction/input pair."""
    train_pairs = {(normalize(row["instruction"]), normalize(row["input"])) for row in train_examples}
    overlap = train_pairs & {
        (normalize(row["instruction"]), normalize(row["input"])) for row in validation_examples
    }
    if overlap:
        raise ValueError("training and validation datasets share normalized (instruction, input) example(s)")


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


def _run_training(
    model, tokenizer, examples: list[dict], validation_examples: list[dict], config: dict[str, Any], output_dir: Path
) -> dict[str, Any]:
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
    sft_config_kwargs = dict(
        output_dir=str(output_dir),
        per_device_train_batch_size=train["batch_size"],
        gradient_accumulation_steps=train["gradient_accumulation_steps"],
        learning_rate=train["learning_rate"],
        num_train_epochs=train["num_epochs"],
        optim=train["optimizer"],
        eval_strategy="epoch",
        per_device_eval_batch_size=train["batch_size"],
        save_strategy="epoch",
        logging_steps=10,
        report_to=[],  # no external experiment trackers
        bf16=True,  # matches configs/train.yaml's bnb_4bit_compute_dtype (bfloat16) — fp16 here would
        # fight the bf16-loaded model's dtype (mismatched autocast/GradScaler assumptions)
        seed=42,
        max_length=train["max_seq_length"],
    )
    if not train["completion_only_loss"]:
        sft_config_kwargs["dataset_text_field"] = "text"
    training_args = SFTConfig(**sft_config_kwargs)

    if train["completion_only_loss"]:
        dataset = Dataset.from_list(
            [{"prompt": format_prompt(ex["instruction"], ex["input"]), "completion": ex["output"]} for ex in examples]
        )
        validation_dataset = Dataset.from_list(
            [{"prompt": format_prompt(ex["instruction"], ex["input"]), "completion": ex["output"]} for ex in validation_examples]
        )
    else:
        # dataset_text_field is deliberately supplied only in the legacy
        # full-sequence path.  TRL uses prompt/completion's response-only
        # loss behaviour automatically in the branch above.
        dataset = Dataset.from_list([{"text": _format_prompt(ex)} for ex in examples])
        validation_dataset = Dataset.from_list([{"text": _format_prompt(ex)} for ex in validation_examples])

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        args=training_args,
        train_dataset=dataset,
        eval_dataset=validation_dataset,
    )
    trainer.train()
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    return _training_summary(output_dir, train["num_epochs"])


def _checkpoint_step(checkpoint_dir: Path) -> int:
    """`checkpoint-124` -> 124. Plain `sorted()` is lexicographic, so a smoke run's
    checkpoint-7/14/21 (or a batch_size=1 run's 495/990/1485) would come out misordered."""
    return int(checkpoint_dir.name.rsplit("-", 1)[1])


def _checkpoint_dirs(output_dir: Path) -> list[Path]:
    return sorted(output_dir.glob("checkpoint-*"), key=_checkpoint_step)


def _training_summary(output_dir: Path, num_epochs: int) -> dict[str, Any]:
    """Extract epoch losses and retained checkpoints from TRL's state file."""
    # The Trainer only writes trainer_state.json inside checkpoint-<step>/; with
    # save_strategy="epoch" the highest step is the end of the last epoch.
    state_path = output_dir / "trainer_state.json"
    if not state_path.exists():
        candidates = [c / "trainer_state.json" for c in _checkpoint_dirs(output_dir)]
        candidates = [c for c in candidates if c.exists()]
        if candidates:
            state_path = candidates[-1]
    log_history = []
    if state_path.exists():
        log_history = json.loads(state_path.read_text(encoding="utf-8")).get("log_history", [])

    eval_losses: dict[str, float] = {}
    train_losses: dict[str, float] = {}
    for entry in log_history:
        epoch = entry.get("epoch")
        if epoch is None:
            continue
        # Training losses are logged every `logging_steps` with fractional epochs
        # (0.08, 0.16, ...); ceil files them under the epoch they were logged in,
        # so each key keeps the last loss of that epoch. End-of-epoch eval entries
        # land on exact integers (1.0, 2.0, ...) and map to themselves.
        epoch_key = str(math.ceil(float(epoch) - 1e-6))
        if "eval_loss" in entry:
            eval_losses[epoch_key] = entry["eval_loss"]
        if "loss" in entry:
            train_losses[epoch_key] = entry["loss"]

    checkpoints = []
    for index, checkpoint in enumerate(_checkpoint_dirs(output_dir), start=1):
        checkpoint_epoch = index
        checkpoint_state = checkpoint / "trainer_state.json"
        if checkpoint_state.exists():
            state = json.loads(checkpoint_state.read_text(encoding="utf-8"))
            if state.get("epoch") is not None:
                checkpoint_epoch = int(round(float(state["epoch"])))
        checkpoints.append({"epoch": checkpoint_epoch, "path": str(checkpoint)})
    best_epoch = min(eval_losses, key=eval_losses.get) if eval_losses else None
    return {
        "eval_loss_by_epoch": eval_losses,
        "train_loss_by_epoch": train_losses,
        "best_epoch": int(best_epoch) if best_epoch is not None else None,
        "checkpoints": checkpoints,
        "adapter_epoch": num_epochs,
    }


def train(config_path: Path, dataset_path: Path, validation_path: Path, run_id: str) -> Path:
    output_dir = Path("adapters") / run_id
    mirror_path = Path("runs") / f"{run_id}.manifest.json"
    # Checked before any manifest is written: stale checkpoint-*/ from an earlier
    # attempt would be folded into this run's summary, and overwriting the earlier
    # run's manifest with a "failed" one would destroy its provenance.
    if _checkpoint_dirs(output_dir) or (output_dir / "adapter_config.json").exists():
        raise FileExistsError(
            f"{output_dir} already holds a previous run's checkpoints/adapter; "
            "pick a new --run-id or remove the directory first"
        )
    config: dict[str, Any] = {}
    summary: dict[str, Any] = {
        "eval_loss_by_epoch": {}, "train_loss_by_epoch": {}, "best_epoch": None,
        "checkpoints": [], "adapter_epoch": None,
    }
    manifest: dict[str, Any] | None = None
    try:
        config = load_config(config_path)
        examples = load_training_examples(dataset_path)
        validation_examples = load_training_examples(validation_path)
        _assert_no_overlap(examples, validation_examples)
        manifest = build_manifest(
            "training", run_id, base_model=config["base_model"], datasets=[dataset_path, validation_path], config=config,
            prompt_format="train-template", validation_path=str(validation_path),
            completion_only_loss=config["training"]["completion_only_loss"], adapter_path=str(output_dir), **summary,
        )
        if manifest["git_dirty"]:
            print("Warning: training run started with a dirty git worktree.", file=sys.stderr)
        model, tokenizer = _build_model(config)
        summary = _run_training(model, tokenizer, examples, validation_examples, config, output_dir)
        manifest.update(summary)
        write_manifest(output_dir / "run_manifest.json", manifest, copies=[mirror_path])
        return output_dir
    except BaseException as exc:
        # BaseException, not Exception: Ctrl-C mid-training is the usual way a
        # local run ends early and it must still leave a failed manifest.
        # A failed run remains reproducible/auditable.  Building a manifest can
        # itself fail only for a missing input file, in which case preserve the
        # original training exception rather than masking it.
        try:
            if manifest is None:
                manifest = build_manifest(
                    "training", run_id, base_model=config.get("base_model", "unknown"), datasets=[dataset_path, validation_path], config=config,
                    prompt_format="train-template", status="failed", error=str(exc), validation_path=str(validation_path),
                    completion_only_loss=config.get("training", {}).get("completion_only_loss", False),
                    adapter_path=str(output_dir), **summary,
                )
            else:
                manifest.update(status="failed", error=str(exc), **summary)
            write_manifest(output_dir / "run_manifest.json", manifest, copies=[mirror_path])
        except Exception:
            # Do not obscure the original training/configuration error if an
            # input is so broken that even its provenance cannot be collected.
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--validation", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)

    output_dir = train(args.config, args.dataset, args.validation, args.run_id)
    print(f"Adapter written to {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
