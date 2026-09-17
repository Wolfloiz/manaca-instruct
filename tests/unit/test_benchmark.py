import subprocess

import pytest

from src.benchmark import _is_gguf, _parse_tokens_per_second, run_benchmark


def test_run_benchmark_rejects_unknown_machine(tmp_path):
    model_path = tmp_path / "model-Q4_K_M.gguf"
    model_path.write_bytes(b"GGUF" + b"\x00" * 16)
    with pytest.raises(ValueError, match="Unknown --machine"):
        run_benchmark(model_path, "some-other-laptop")


def test_run_benchmark_rejects_missing_model_file(tmp_path):
    missing = tmp_path / "does-not-exist.gguf"
    with pytest.raises(FileNotFoundError):
        run_benchmark(missing, "rtx-5050")


def test_run_benchmark_rejects_non_gguf_file(tmp_path, monkeypatch):
    model_path = tmp_path / "model-Q4_K_M.gguf"
    model_path.write_text("not really a gguf")
    monkeypatch.setattr("src.benchmark._find_llama_cli", lambda: "/usr/bin/llama-cli")
    with pytest.raises(ValueError, match="GGUF"):
        run_benchmark(model_path, "rtx-5050")


def test_is_gguf_checks_magic_bytes(tmp_path):
    good = tmp_path / "good.gguf"
    good.write_bytes(b"GGUF\x01\x02\x03\x04")
    bad = tmp_path / "bad.gguf"
    bad.write_text("plain text")
    assert _is_gguf(good) is True
    assert _is_gguf(bad) is False


def test_parse_tokens_per_second_extracts_eval_figure():
    stderr = (
        "llama_print_timings:        load time =   120.00 ms\n"
        "llama_print_timings:        eval time =  1234.56 ms /  100 tokens "
        "(   12.35 ms per token,   81.00 tokens per second)\n"
    )
    assert _parse_tokens_per_second(stderr) == 81.0


def test_parse_tokens_per_second_returns_none_when_missing():
    assert _parse_tokens_per_second("no timing info here") is None


def test_run_benchmark_builds_valid_record_with_mocked_llama_cli(tmp_path, monkeypatch):
    model_path = tmp_path / "model-Q4_K_M.gguf"
    model_path.write_bytes(b"GGUF" + b"\x00" * 16)
    monkeypatch.setattr("src.benchmark._find_llama_cli", lambda: "/usr/bin/llama-cli")

    def fake_run_and_measure(command):
        result = subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout="alguma resposta gerada pelo modelo",
            stderr=(
                "llama_print_timings:        eval time =  1000.00 ms /  200 tokens "
                "(    5.00 ms per token,  200.00 tokens per second)\n"
            ),
        )
        return result, 512, 4096

    monkeypatch.setattr("src.benchmark._run_and_measure", fake_run_and_measure)

    record = run_benchmark(model_path, "rtx-5050")
    assert "source_run_id" not in record  # optional: absent when not given, so older rows stay valid

    record = run_benchmark(model_path, "rtx-5050", source_run_id="qlora-v3b")
    assert record["source_run_id"] == "qlora-v3b"
    assert record["machine"] == "rtx-5050"
    assert record["quant_level"] == "Q4_K_M"
    assert record["tokens_per_second"] == 200.0
    assert record["ram_mb"] == 512
    assert record["vram_mb"] == 4096
    assert record["stalled_or_crashed"] is False
    assert isinstance(record["load_time_s"], float)


def test_run_benchmark_accepts_dell_g3_and_marks_stall_on_failure(tmp_path, monkeypatch):
    model_path = tmp_path / "model-Q4_K_M.gguf"
    model_path.write_bytes(b"GGUF" + b"\x00" * 16)
    monkeypatch.setattr("src.benchmark._find_llama_cli", lambda: "/usr/bin/llama-cli")

    def fake_run_and_measure(command):
        result = subprocess.CompletedProcess(command, returncode=1, stdout="", stderr="error: out of memory\n")
        return result, None, None

    monkeypatch.setattr("src.benchmark._run_and_measure", fake_run_and_measure)

    record = run_benchmark(model_path, "dell-g3")

    assert record["machine"] == "dell-g3"
    assert record["stalled_or_crashed"] is True
    assert record["tokens_per_second"] == 0.0
    assert record["ram_mb"] is None
    assert record["vram_mb"] is None


def test_peak_child_ram_mb_reads_rusage_children(monkeypatch):
    from src import benchmark

    class FakeUsage:
        ru_maxrss = 2048  # KB

    monkeypatch.setattr(benchmark.resource, "getrusage", lambda who: FakeUsage())
    assert benchmark._peak_child_ram_mb() == 2  # 2048 KB -> 2 MB


def test_peak_child_ram_mb_returns_none_when_zero(monkeypatch):
    from src import benchmark

    class FakeUsage:
        ru_maxrss = 0

    monkeypatch.setattr(benchmark.resource, "getrusage", lambda who: FakeUsage())
    assert benchmark._peak_child_ram_mb() is None


def test_run_and_measure_polls_vram_while_process_alive(monkeypatch):
    from src import benchmark

    class FakeProc:
        def __init__(self):
            self._polls = 0
            self.returncode = 0

        def poll(self):
            self._polls += 1
            return None if self._polls <= 2 else 0

        def communicate(self):
            return "output", ""

    fake_proc = FakeProc()
    monkeypatch.setattr(benchmark.subprocess, "Popen", lambda *a, **k: fake_proc)
    monkeypatch.setattr(benchmark.shutil, "which", lambda name: "/usr/bin/nvidia-smi" if name == "nvidia-smi" else None)
    monkeypatch.setattr(benchmark.time, "sleep", lambda s: None)
    samples = iter([1000, 3000, 2000])
    monkeypatch.setattr(benchmark, "_read_vram_mb", lambda path: next(samples))
    monkeypatch.setattr(benchmark, "_peak_child_ram_mb", lambda: 777)

    result, ram_mb, vram_mb = benchmark._run_and_measure(["llama-cli"])

    assert result.returncode == 0
    assert result.stdout == "output"
    assert ram_mb == 777
    assert vram_mb == 3000  # peak of the sampled readings


def test_run_and_measure_returns_none_vram_without_nvidia_smi(monkeypatch):
    from src import benchmark

    class FakeProc:
        returncode = 0

        def poll(self):
            return 0

        def communicate(self):
            return "output", ""

    monkeypatch.setattr(benchmark.subprocess, "Popen", lambda *a, **k: FakeProc())
    monkeypatch.setattr(benchmark.shutil, "which", lambda name: None)
    monkeypatch.setattr(benchmark, "_peak_child_ram_mb", lambda: 512)

    result, ram_mb, vram_mb = benchmark._run_and_measure(["llama-cli"])

    assert ram_mb == 512
    assert vram_mb is None


def test_single_turn_flag_only_for_llama_cli():
    from src.benchmark import BENCHMARK_PROMPT, _single_turn_flag

    assert _single_turn_flag("/x/llama-completion") == []
    assert _single_turn_flag("/x/llama-cli") == ["--single-turn"]
    # the GGUF tokenizer has no lowercase normalizer, and the prompt must carry the training template
    assert BENCHMARK_PROMPT == BENCHMARK_PROMPT.lower()
    assert BENCHMARK_PROMPT.startswith("### instrução:\n") and BENCHMARK_PROMPT.endswith("### resposta:\n")
