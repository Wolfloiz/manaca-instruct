"""Measure generation throughput/resource usage of a quantized GGUF model on this machine.

Usage:

    python src/benchmark.py --model models/gguf/manaca-instruct-pt-Q4_K_M.gguf --machine rtx-5050 --out benchmarks/rtx-5050.jsonl
    python src/benchmark.py --model models/gguf/manaca-instruct-pt-Q4_K_M.gguf --machine dell-g3 --out benchmarks/dell-g3.jsonl

Implements FR-007/FR-008 and data-model.md's BenchmarkRecord: tokens_per_second,
load_time_s, vram_mb, ram_mb, stalled_or_crashed, written as one JSONL row per run.

The GGUF model is exercised through llama.cpp's `llama-cli` (must be built
locally, research.md §4): `_load_gguf_model()` runs a warm-up generation that
forces the model into memory (so `load_time_s` is real), and
`_run_generation_benchmark()` runs the timed generation and parses llama-cli's
`llama_print_timings` stderr line for honest tokens/sec. Peak RAM is read from
`/usr/bin/time -v` when available; VRAM from `nvidia-smi` when present.
"""

from __future__ import annotations

import argparse
import json
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path

KNOWN_MACHINES = {"rtx-5050", "dell-g3"}
BENCHMARK_PROMPT = "Corrija gramaticalmente o texto: os documento foi enviado ontem"
DEFAULT_MAX_NEW_TOKENS = 128

LLAMA_CLI_CANDIDATES = ("llama-cli", "llama.cpp/build/bin/llama-cli")


def _find_llama_cli() -> str | None:
    for candidate in LLAMA_CLI_CANDIDATES:
        found = shutil.which(candidate) or (Path(candidate).resolve() if Path(candidate).exists() else None)
        if found:
            return str(found)
    return None


def _is_gguf(path: Path) -> bool:
    with path.open("rb") as f:
        return f.read(4) == b"GGUF"


def _parse_tokens_per_second(stderr: str) -> float | None:
    """Extract the `... eval time ... tokens per second` figure from llama-cli's stderr."""
    for line in reversed(stderr.splitlines()):
        if "tokens per second" in line:
            # e.g. "llama_print_timings:        eval time =  1234.56 ms /  100 tokens (  12.35 ms per token,   81.00 tokens per second)"
            try:
                return float(line.rsplit("tokens per second", 1)[0].split(",")[-1].strip())
            except (ValueError, IndexError):
                return None
    return None


def _read_vram_mb() -> int | None:
    """Peak VRAM via nvidia-smi when present, else None (e.g. CPU-only Dell G3)."""
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return None
    try:
        out = subprocess.run(
            [nvidia_smi, "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return int(out.stdout.strip().splitlines()[0].strip())
    except (subprocess.SubprocessError, ValueError, IndexError):
        return None


def _measure_peak_ram_mb(command: list[str]) -> tuple[int | None, subprocess.CompletedProcess]:
    """Run `command`; return (peak RAM MB, result). Uses /usr/bin/time -v when available."""
    time_bin = shutil.which("time") or shutil.which("/usr/bin/time")
    use_gnu_time = time_bin and subprocess.run([time_bin, "--version"], capture_output=True).returncode == 0
    if use_gnu_time:
        result = subprocess.run([time_bin, "-v", *command], capture_output=True, text=True)
        for line in reversed(result.stderr.splitlines()):
            if "Maximum resident set size" in line:
                try:
                    return int(line.split(":")[-1].strip()) // 1024, result  # KB -> MB
                except ValueError:
                    break
        return None, result
    result = subprocess.run(command, capture_output=True, text=True)
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024  # rough parent-process floor
    return peak, result


def _load_gguf_model(model_path: Path):
    """Warm up llama.cpp so the model is actually in memory; returns a handle dict.

    The warm-up also captures the model's peak RAM footprint, which is kept on
    the handle so the BenchmarkRecord's `ram_mb` reflects model load rather
    than the benchmark subprocess's own transient allocations.
    """
    llama_cli = _find_llama_cli()
    if not llama_cli:
        raise FileNotFoundError(
            "llama-cli not found — build llama.cpp first (research.md §4) or put llama-cli on PATH"
        )
    if not _is_gguf(model_path):
        raise ValueError(f"not a GGUF file (missing GGUF magic bytes): {model_path}")
    peak_ram, result = _measure_peak_ram_mb([llama_cli, "-m", str(model_path), "-p", "oi", "-n", "1"])
    if result.returncode != 0:
        raise RuntimeError(f"llama-cli warm-up failed (exit {result.returncode}):\n{result.stderr}")
    return {"path": str(model_path), "llama_cli": llama_cli, "ram_mb": peak_ram}


def _run_generation_benchmark(model, prompt: str, max_new_tokens: int) -> dict:
    """Run a real generation through llama-cli and record throughput + resources."""
    start = time.monotonic()
    _, result = _measure_peak_ram_mb(
        [
            model["llama_cli"],
            "-m", model["path"],
            "-p", prompt,
            "-n", str(max_new_tokens),
            "--no-display-prompt",
            "--temp", "0",
            "-c", "4096",
        ]
    )
    elapsed_s = time.monotonic() - start

    tokens_per_second = _parse_tokens_per_second(result.stderr)
    output_tokens = result.stdout
    stalled = result.returncode != 0 or not output_tokens.strip()

    if tokens_per_second is None and elapsed_s > 0 and output_tokens.strip():
        tokens_per_second = len(output_tokens.split()) / elapsed_s  # honest fallback, not silent default

    return {
        "tokens_per_second": tokens_per_second if tokens_per_second is not None else 0.0,
        "vram_mb": _read_vram_mb(),
        "ram_mb": model.get("ram_mb"),
        "stalled_or_crashed": stalled,
    }


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
