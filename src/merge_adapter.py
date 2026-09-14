"""Merge a trained LoRA adapter into a standalone model, ready for quantization.

Usage:

    python src/merge_adapter.py --adapter adapters/qlora-v1 --out models/merged/manaca-instruct-pt

Implements the merge step of FR-006. NOTE: `_load_base_and_adapter()` and
`_merge_and_save()` are documented seams — see src/train_qlora.py's module
docstring for why (no GPU/model execution in this scaffolding-only pass).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _load_base_and_adapter(adapter_path: Path):
    """Seam for real peft.PeftModel.from_pretrained loading — not implemented in this pass."""
    raise NotImplementedError(
        "src/merge_adapter.py's _load_base_and_adapter is a documented seam, not yet wired to "
        "peft — implement before merging a real trained adapter (tasks.md T049)."
    )


def _merge_and_save(model, out_dir: Path) -> None:
    """Seam for real PeftModel.merge_and_unload() + save_pretrained() — not implemented in this pass."""
    raise NotImplementedError("src/merge_adapter.py's _merge_and_save is a documented seam — see the module docstring.")


def merge_adapter(adapter_path: Path, out_dir: Path) -> Path:
    if not adapter_path.exists():
        raise FileNotFoundError(f"adapter path does not exist: {adapter_path}")
    model = _load_base_and_adapter(adapter_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    _merge_and_save(model, out_dir)
    return out_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    out_dir = merge_adapter(args.adapter, args.out)
    print(f"Merged model written to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
