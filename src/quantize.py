"""Convert a merged model to GGUF and quantize it to two comparison levels.

Usage:

    python src/quantize.py --model models/merged/manaca-instruct-pt --levels Q4_K_M Q5_K_M --out-dir models/gguf/

Implements FR-006 via the standard llama.cpp workflow from research.md §4:
merged model -> F16 GGUF (`convert_hf_to_gguf.py`) -> quantize (`llama-quantize`).

NOTE: research.md §4 flags a real risk — GGUF quantization below a certain
aggressiveness has produced degraded results specifically for QLoRA-derived
(vs. fully-fine-tuned) models. `_run_conversion()`/`_run_quantize()` shell out
to llama.cpp binaries that must be built locally first. Paths to those
binaries default to a `llama.cpp/` checkout beside the repo; override with
--convert-script/--quantize-bin.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SUPPORTED_LEVELS = {"Q4_K_M", "Q5_K_M", "Q6_K", "Q8_0"}
MINIMUM_LEVELS_REQUIRED = 2  # FR-006: at least Q4_K_M plus one comparison level


def _run_conversion(merged_model_dir: Path, f16_out: Path, convert_script: Path) -> None:
    """Run `python convert_hf_to_gguf.py <model> --outfile <out> --outtype f16`."""
    if not convert_script.exists():
        raise FileNotFoundError(
            f"convert_hf_to_gguf.py not found at {convert_script} — build llama.cpp first (research.md §4)"
        )
    result = subprocess.run(
        [
            sys.executable,
            str(convert_script),
            str(merged_model_dir),
            "--outfile",
            str(f16_out),
            "--outtype",
            "f16",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not f16_out.exists():
        raise RuntimeError(
            f"convert_hf_to_gguf.py failed (exit {result.returncode}):\n{result.stderr}"
        )


def _run_quantize(f16_path: Path, level: str, out_path: Path, quantize_bin: Path) -> None:
    """Run `llama-quantize <f16> <out> <level>`."""
    if not quantize_bin.exists():
        raise FileNotFoundError(
            f"llama-quantize not found at {quantize_bin} — build llama.cpp first (research.md §4)"
        )
    result = subprocess.run(
        [str(quantize_bin), str(f16_path), str(out_path), level],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not out_path.exists():
        raise RuntimeError(
            f"llama-quantize {level} failed (exit {result.returncode}):\n{result.stderr}"
        )


def quantize(
    merged_model_dir: Path,
    levels: list[str],
    out_dir: Path,
    convert_script: Path = Path("llama.cpp/convert_hf_to_gguf.py"),
    quantize_bin: Path = Path("llama.cpp/build/bin/llama-quantize"),
) -> list[Path]:
    if not merged_model_dir.exists():
        raise FileNotFoundError(f"merged model directory does not exist: {merged_model_dir}")

    unsupported = set(levels) - SUPPORTED_LEVELS
    if unsupported:
        raise ValueError(f"Unsupported quantization level(s): {sorted(unsupported)} — must be in {sorted(SUPPORTED_LEVELS)}")
    if len(levels) < MINIMUM_LEVELS_REQUIRED:
        raise ValueError(f"FR-006 requires at least {MINIMUM_LEVELS_REQUIRED} quantization levels, got {len(levels)}")

    out_dir.mkdir(parents=True, exist_ok=True)
    f16_path = out_dir / f"{merged_model_dir.name}-f16.gguf"
    _run_conversion(merged_model_dir, f16_path, convert_script)

    outputs = []
    for level in levels:
        out_path = out_dir / f"{merged_model_dir.name}-{level}.gguf"
        _run_quantize(f16_path, level, out_path, quantize_bin)
        outputs.append(out_path)
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--levels", nargs="+", default=["Q4_K_M", "Q5_K_M"])
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument(
        "--convert-script",
        type=Path,
        default=Path("llama.cpp/convert_hf_to_gguf.py"),
        help="Path to llama.cpp's convert_hf_to_gguf.py",
    )
    parser.add_argument(
        "--quantize-bin",
        type=Path,
        default=Path("llama.cpp/build/bin/llama-quantize"),
        help="Path to the llama-quantize binary",
    )
    args = parser.parse_args(argv)

    outputs = quantize(args.model, args.levels, args.out_dir, args.convert_script, args.quantize_bin)
    for path in outputs:
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
