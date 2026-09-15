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

    def fake_measure(command):
        class Result:
            returncode = 0
            stdout = "alguma resposta gerada pelo modelo"
            stderr = (
                "llama_print_timings:        eval time =  1000.00 ms /  200 tokens "
                "(    5.00 ms per token,  200.00 tokens per second)\n"
            )

        return (512, Result())

    monkeypatch.setattr("src.benchmark._measure_peak_ram_mb", fake_measure)
    monkeypatch.setattr("src.benchmark._read_vram_mb", lambda: 4096)

    record = run_benchmark(model_path, "rtx-5050")

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

    def fake_measure(command):
        class Result:
            returncode = 1
            stdout = ""
            stderr = "error: out of memory\n"

        return (None, Result())

    monkeypatch.setattr("src.benchmark._measure_peak_ram_mb", fake_measure)
    monkeypatch.setattr("src.benchmark._read_vram_mb", lambda: None)

    record = run_benchmark(model_path, "dell-g3")

    assert record["machine"] == "dell-g3"
    assert record["stalled_or_crashed"] is True
    assert record["tokens_per_second"] == 0.0
    assert record["ram_mb"] is None
    assert record["vram_mb"] is None
