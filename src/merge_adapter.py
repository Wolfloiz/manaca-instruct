"""Merge a trained LoRA adapter into a standalone model, ready for quantization.

Usage:

    python -m src.merge_adapter --adapter adapters/qlora-v1 --out models/merged/manaca-instruct-pt

Implements the merge step of FR-006. The adapter's `adapter_config.json`
records `base_model_name_or_path`, so the base model is re-derived from the
adapter itself — no separate --base-model flag needed. ML imports are lazy
(see src/train_qlora.py's module docstring for why).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _base_model_name(adapter_path: Path) -> str:
    config_path = adapter_path / "adapter_config.json"
    if not config_path.exists():
        raise FileNotFoundError(
            f"adapter path has no adapter_config.json — not a PeftModel adapter: {adapter_path}"
        )
    with config_path.open(encoding="utf-8") as f:
        config = json.load(f)
    base = config.get("base_model_name_or_path")
    if not base:
        raise ValueError(f"adapter_config.json is missing base_model_name_or_path: {config_path}")
    return base


def _load_base_and_adapter(adapter_path: Path):
    """Load the base model from the adapter's adapter_config.json and attach the LoRA adapter."""
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    base_model_name = _base_model_name(adapter_path)
    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        dtype=torch.bfloat16,
        device_map="auto",
        # no trust_remote_code — see src/train_qlora.py's _build_model for why
    )
    model = PeftModel.from_pretrained(model, adapter_path)
    model.tokenizer = AutoTokenizer.from_pretrained(base_model_name)
    model.base_model_name = base_model_name  # kept for _merge_and_save's raw-file copy
    return model


_RAW_TOKENIZER_FILES = ("tokenizer.model", "special_tokens_map.json")


def _copy_raw_tokenizer_files(base_model_name: str, out_dir: Path) -> None:
    """AutoTokenizer.save_pretrained() can silently drop files a fast tokenizer doesn't
    round-trip (e.g. the raw SentencePiece tokenizer.model) — found the hard way when
    llama.cpp's convert_hf_to_gguf.py couldn't build a vocab from our merged output even
    though the original base model repo ships tokenizer.model. Fetch those specific files
    straight from the base repo instead of trusting the round-trip.
    """
    from huggingface_hub import hf_hub_download
    from huggingface_hub.errors import EntryNotFoundError

    for filename in _RAW_TOKENIZER_FILES:
        try:
            cached_path = hf_hub_download(repo_id=base_model_name, filename=filename)
        except EntryNotFoundError:
            continue  # not every model ships every one of these (e.g. pure-BPE tokenizers)
        import shutil

        shutil.copy(cached_path, out_dir / filename)


def _merge_and_save(model, out_dir: Path) -> None:
    """Merge LoRA weights into the base weights and save a standalone model + tokenizer."""
    merged = model.merge_and_unload()
    merged.save_pretrained(out_dir, safe_serialization=True)
    tokenizer = getattr(model, "tokenizer", None)
    if tokenizer is not None:
        tokenizer.save_pretrained(out_dir)
    base_model_name = getattr(model, "base_model_name", None)
    if base_model_name is not None:
        _copy_raw_tokenizer_files(base_model_name, out_dir)


GENERATION_KEYS = ("max_new_tokens", "do_sample", "temperature", "top_p", "repetition_penalty", "no_repeat_ngram_size")


def write_generation_defaults(out_dir: Path, inference_config_path: Path) -> dict:
    """Fold configs/inference.yaml into the merged model's generation_config.json.

    What gets published is what was evaluated (002 adoption-decision.md): a downloader calling
    `model.generate(**inputs)` with no arguments then gets the evaluated settings
    (repetition_penalty 1.1, greedy) instead of transformers' defaults.
    """
    import json

    import yaml

    inference = yaml.safe_load(inference_config_path.read_text(encoding="utf-8"))
    path = out_dir / "generation_config.json"
    generation = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    generation.update({k: inference[k] for k in GENERATION_KEYS if k in inference})
    path.write_text(json.dumps(generation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return generation


def merge_adapter(adapter_path: Path, out_dir: Path, inference_config_path: Path | None = None) -> Path:
    if not adapter_path.exists():
        raise FileNotFoundError(f"adapter path does not exist: {adapter_path}")
    model = _load_base_and_adapter(adapter_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    _merge_and_save(model, out_dir)
    if inference_config_path is not None:
        write_generation_defaults(out_dir, inference_config_path)
    return out_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--generation-config", type=Path, default=Path("configs/inference.yaml"),
        help="inference YAML whose generation settings become the merged model's generation_config.json defaults",
    )
    args = parser.parse_args(argv)

    out_dir = merge_adapter(args.adapter, args.out, args.generation_config)
    print(f"Merged model written to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
