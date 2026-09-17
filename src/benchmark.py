"""Measure generation throughput/resource usage of a quantized GGUF model on this machine.

Usage:

    python -m src.benchmark --model models/gguf/manaca-instruct-pt-Q4_K_M.gguf --machine rtx-5050 --out benchmarks/rtx-5050.jsonl
    python -m src.benchmark --model models/gguf/manaca-instruct-pt-Q4_K_M.gguf --machine dell-g3 --out benchmarks/dell-g3.jsonl

Implements FR-007/FR-008 and data-model.md's BenchmarkRecord: tokens_per_second,
load_time_s, vram_mb, ram_mb, stalled_or_crashed, written as one JSONL row per run.

The GGUF model is exercised through llama.cpp's `llama-cli` (must be built
locally, research.md §4): `_load_gguf_model()` runs a warm-up generation that
forces the model into memory (so `load_time_s` is real), and
`_run_generation_benchmark()` runs the timed generation and parses llama-cli's
`llama_print_timings` stderr line for honest tokens/sec. Both go through
`_run_and_measure()`, which runs llama-cli as a child process, polls
`nvidia-smi` for peak VRAM *while the process is alive* (a single post-hoc
read is too late for a short-lived one-shot process — by the time it
returns, llama-cli has already exited and freed its VRAM), and reads peak
child RSS via `resource.getrusage(RUSAGE_CHILDREN)` once it's done (accurate
without needing an external `time` binary).
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
# The training template, lowercased. Two llama.cpp facts found while benchmarking the adopted
# adapter (002 T056): (1) convert_hf_to_gguf.py drops the tokenizer's NFKC+Lowercase normalizer,
# so an uppercase "Resposta" tokenizes as ' ','R','esp','os','ta' instead of '▁resposta' and the
# model -- trained on lowercased text -- answers EOS; (2) the `llama-cli` of recent builds is a
# chat front-end that wraps the prompt in a (ChatML) chat template the model never saw. So the
# benchmark prompt is lowercased and templated, and `llama-completion` (raw completion) is
# preferred over `llama-cli`. qlora-v2's rows were measured through llama-cli with a raw
# uppercase prompt; it rambled anyway, so its throughput numbers stand, but the adopted model
# stops correctly and produced no tokens under that invocation (rows removed, see git history).
BENCHMARK_PROMPT = (
    "### instrução:\ncorrija gramaticalmente o texto: os documento foi enviado ontem\n\n### resposta:\n"
)
DEFAULT_MAX_NEW_TOKENS = 128

# llama-completion first: raw completion, no chat template. llama-cli is kept as the fallback
# for builds that predate the split (where it *was* the raw completion binary).
LLAMA_CLI_CANDIDATES = (
    "llama-completion", "llama.cpp/build/bin/llama-completion", "llama-cli", "llama.cpp/build/bin/llama-cli"
)

SUBPROCESS_TIMEOUT_S = 120  # llama-cli hanging (e.g. waiting on stdin it'll never get) should
# become a measured stalled_or_crashed: true, not an indefinitely frozen benchmark run

VRAM_POLL_INTERVAL_S = 0.1


def _find_llama_cli() -> str | None:
    for candidate in LLAMA_CLI_CANDIDATES:
        found = shutil.which(candidate) or (Path(candidate).resolve() if Path(candidate).exists() else None)
        if found:
            return str(found)
    return None


def _single_turn_flag(binary: str) -> list[str]:
    """--single-turn keeps llama-cli's chat front-end from waiting on stdin; llama-completion
    is non-interactive and exits after -n tokens on its own."""
    return [] if Path(binary).name.startswith("llama-completion") else ["--single-turn"]


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


def _read_vram_mb(nvidia_smi: str) -> int | None:
    """One instantaneous VRAM-used sample via nvidia-smi, or None if the read fails."""
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


def _peak_child_ram_mb() -> int | None:
    """Peak RSS of completed child processes (KB -> MB), via RUSAGE_CHILDREN.

    Accurate for a short-lived one-shot subprocess like a llama-cli run, and needs no
    external `time` binary — this machine has none installed (`shutil.which("time")`
    finds only the shell builtin), so the former `/usr/bin/time -v` branch always fell
    through to `RUSAGE_SELF`, which measures the *parent* Python process's own tiny RSS,
    not the llama-cli child's. RUSAGE_CHILDREN is cumulative across all children reaped
    so far in this process, which is fine here: each call site cares about "how much RAM
    did running llama-cli take", and later reads only ever report the same or a larger
    number as more of the run completes.
    """
    maxrss_kb = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return maxrss_kb // 1024 if maxrss_kb else None


def _run_and_measure(command: list[str]) -> tuple[subprocess.CompletedProcess, int | None, int | None]:
    """Run `command` to completion, returning (result, ram_mb, vram_mb).

    VRAM is polled from nvidia-smi while the process is alive rather than sampled once
    after it exits, because llama-cli's warm-up/generation runs are short-lived
    one-shot processes — by the time a post-hoc read would fire, the process has
    already exited and freed its VRAM. `vram_mb` is None when nvidia-smi isn't present
    (e.g. the CPU-only Dell G3). A run exceeding SUBPROCESS_TIMEOUT_S is killed and
    reported as a synthetic failed result instead of hanging the benchmark forever —
    found the hard way: llama-cli defaults to interactive/conversational mode when a
    GGUF's metadata includes a chat template, and silently waits on stdin forever
    without --single-turn (see _load_gguf_model/_run_generation_benchmark's commands).
    """
    nvidia_smi = shutil.which("nvidia-smi")
    try:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except OSError as exc:
        return subprocess.CompletedProcess(command, returncode=-1, stdout="", stderr=str(exc)), None, None

    start = time.monotonic()
    peak_vram: int | None = None
    timed_out = False
    while proc.poll() is None:
        if nvidia_smi:
            sample = _read_vram_mb(nvidia_smi)
            if sample is not None:
                peak_vram = sample if peak_vram is None else max(peak_vram, sample)
        if time.monotonic() - start > SUBPROCESS_TIMEOUT_S:
            timed_out = True
            proc.kill()
            break
        time.sleep(VRAM_POLL_INTERVAL_S)

    stdout, stderr = proc.communicate()
    ram_mb = _peak_child_ram_mb()

    if timed_out:
        return subprocess.CompletedProcess(command, returncode=-1, stdout=stdout, stderr="timed out"), ram_mb, peak_vram
    return subprocess.CompletedProcess(command, returncode=proc.returncode, stdout=stdout, stderr=stderr), ram_mb, peak_vram


def _load_gguf_model(model_path: Path):
    """Warm up llama.cpp so the model is actually in memory; returns a handle dict.

    The warm-up also captures the model's peak RAM/VRAM footprint, which is kept on
    the handle so the BenchmarkRecord reflects model load rather than only the
    benchmark subprocess's own transient allocations.
    """
    llama_cli = _find_llama_cli()
    if not llama_cli:
        raise FileNotFoundError(
            "llama-cli not found — build llama.cpp first (research.md §4) or put llama-cli on PATH"
        )
    if not _is_gguf(model_path):
        raise ValueError(f"not a GGUF file (missing GGUF magic bytes): {model_path}")
    result, ram_mb, vram_mb = _run_and_measure(
        [llama_cli, "-m", str(model_path), "-p", "oi", "-n", "1", *_single_turn_flag(llama_cli)]
    )
    if result.returncode != 0:
        raise RuntimeError(f"llama-cli warm-up failed (exit {result.returncode}):\n{result.stderr}")
    return {"path": str(model_path), "llama_cli": llama_cli, "ram_mb": ram_mb, "vram_mb": vram_mb}


def _run_generation_benchmark(model, prompt: str, max_new_tokens: int) -> dict:
    """Run a real generation through llama-cli and record throughput + resources."""
    start = time.monotonic()
    result, ram_mb, vram_mb = _run_and_measure(
        [
            model["llama_cli"],
            "-m", model["path"],
            "-p", prompt,
            "-n", str(max_new_tokens),
            "--no-display-prompt",
            *_single_turn_flag(model["llama_cli"]),
            "--temp", "0",
            "--repeat-penalty", "1.1",  # the adopted generation setting (configs/inference.yaml)
            "-c", "4096",
        ]
    )
    elapsed_s = time.monotonic() - start

    tokens_per_second = _parse_tokens_per_second(result.stderr)
    output_tokens = result.stdout
    stalled = result.returncode != 0 or not output_tokens.strip()

    if tokens_per_second is None and elapsed_s > 0 and output_tokens.strip():
        tokens_per_second = len(output_tokens.split()) / elapsed_s  # honest fallback, not silent default

    # peak-so-far across warm-up + this run; prefer this call's reading, it's the most complete
    ram_mb = ram_mb if ram_mb is not None else model.get("ram_mb")
    vram_mb = vram_mb if vram_mb is not None else model.get("vram_mb")

    return {
        "tokens_per_second": tokens_per_second if tokens_per_second is not None else 0.0,
        "vram_mb": vram_mb,
        "ram_mb": ram_mb,
        "stalled_or_crashed": stalled,
    }


def run_benchmark(
    model_path: Path, machine: str, max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS, source_run_id: str | None = None
) -> dict:
    """Note: pre-flight problems (bad --machine, missing/non-GGUF file, no llama-cli on
    PATH) raise — those are setup errors, not a benchmark result. A failure *during* the
    actual warm-up/generation (llama-cli exits non-zero, e.g. OOM) is caught here and
    recorded as `stalled_or_crashed: True` instead, per SC-004/data-model.md's
    BenchmarkRecord — a crash is itself a measured result, not something to hide behind
    an uncaught exception (spec.md's Edge Cases section).
    """
    if machine not in KNOWN_MACHINES:
        raise ValueError(f"Unknown --machine {machine!r}; must be one of {sorted(KNOWN_MACHINES)}")
    if not model_path.exists():
        raise FileNotFoundError(f"GGUF model file does not exist: {model_path}")

    quant_level = model_path.stem.rsplit("-", 1)[-1]
    # The GGUF file name is the same for every adapter that gets merged (manaca-instruct-pt-*),
    # so a benchmarks/*.jsonl that spans runs (v2 rows kept, v3b rows appended -- 002 T056)
    # needs the run recorded on the row itself; `source_run_id` mirrors QuantizedArtifact's.
    provenance = {"source_run_id": source_run_id} if source_run_id else {}
    start = time.monotonic()
    try:
        model = _load_gguf_model(model_path)
    except RuntimeError:
        return {
            "machine": machine,
            "quant_level": quant_level,
            "tokens_per_second": 0.0,
            "load_time_s": time.monotonic() - start,
            "vram_mb": None,
            "ram_mb": None,
            "stalled_or_crashed": True,
            **provenance,
        }
    load_time_s = time.monotonic() - start

    result = _run_generation_benchmark(model, BENCHMARK_PROMPT, max_new_tokens)

    return {
        "machine": machine,
        "quant_level": quant_level,
        "tokens_per_second": result["tokens_per_second"],
        "load_time_s": load_time_s,
        "vram_mb": result.get("vram_mb"),
        "ram_mb": result["ram_mb"],
        "stalled_or_crashed": result["stalled_or_crashed"],
        **provenance,
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
    parser.add_argument(
        "--source-run-id", default=None,
        help="training run the GGUF was merged from (e.g. qlora-v3b); recorded as source_run_id on the row",
    )
    args = parser.parse_args(argv)

    record = run_benchmark(args.model, args.machine, source_run_id=args.source_run_id)
    append_record(record, args.out)
    print(f"Recorded benchmark for {args.machine}: {record['tokens_per_second']:.1f} tok/s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
