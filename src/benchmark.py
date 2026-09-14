"""Measure generation throughput/resource usage of a quantized GGUF model on this machine.

Usage:

    python -m src.benchmark --model models/gguf/manaca-instruct-pt-Q4_K_M.gguf --machine rtx-5050 --out benchmarks/rtx-5050.jsonl
    python -m src.benchmark --model models/gguf/manaca-instruct-pt-Q4_K_M.gguf --machine dell-g3 --out benchmarks/dell-g3.jsonl

Implements FR-007/FR-008 and data-model.md's BenchmarkRecord: tokens_per_second,
load_time_s, vram_mb, ram_mb, stalled_or_crashed, written as one JSONL row per run.

NOTE: `_load_gguf_model()`/`_run_generation_benchmark()` shell out to (or bind)
llama.cpp and are documented seams — not invoked in this pass, since it would
require a real quantized GGUF file and, for the Dell G3 leg, physical access
to that machine (tasks.md Phase 5 scope note: You runs this, not an agent).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

KNOWN_MACHINES = {"rtx-5050", "dell-g3"}


def _load_gguf_model(model_path: Path):
    """Seam wrapping llama.cpp model loading — not invoked in this pass."""
    raise NotImplementedError(
        "src/benchmark.py's _load_gguf_model is a documented seam wrapping llama.cpp — "
        "see the module docstring. Implement/invoke before benchmarking a real GGUF file "
        "(tasks.md T050/T051)."
    )


def _run_generation_benchmark(model, prompt: str, max_new_tokens: int) -> dict:
    """Seam returning {'tokens_per_second', 'vram_mb', 'ram_mb', 'stalled_or_crashed'} — not invoked in this pass."""
    raise NotImplementedError("src/benchmark.py's _run_generation_benchmark is a documented seam — see the module docstring.")


BENCHMARK_PROMPT = "Corrija gramaticalmente o texto: os documento foi enviado ontem"
DEFAULT_MAX_NEW_TOKENS = 128


def run_benchmark(model_path: Path, machine: str, max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS) -> dict:
    if machine not in KNOWN_MACHINES:
        raise ValueError(f"Unknown --machine {machine!r}; must be one of {sorted(KNOWN_MACHINES)}")
    if not model_path.exists():
        raise FileNotFoundError(f"GGUF model file does not exist: {model_path}")

    start = time.monotonic()
    model = _load_gguf_model(model_path)
    load_time_s = time.monotonic() - start

    result = _run_generation_benchmark(model, BENCHMARK_PROMPT, max_new_tokens)

    return {
        "machine": machine,
        "quant_level": model_path.stem.rsplit("-", 1)[-1],
        "tokens_per_second": result["tokens_per_second"],
        "load_time_s": load_time_s,
        "vram_mb": result.get("vram_mb"),
        "ram_mb": result["ram_mb"],
        "stalled_or_crashed": result["stalled_or_crashed"],
    }


def append_record(record: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--machine", required=True, choices=sorted(KNOWN_MACHINES))
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    record = run_benchmark(args.model, args.machine)
    append_record(record, args.out)
    print(f"Recorded benchmark for {args.machine}: {record['tokens_per_second']:.1f} tok/s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
