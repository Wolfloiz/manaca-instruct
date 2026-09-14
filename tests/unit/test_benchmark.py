import pytest

from src.benchmark import run_benchmark


def test_run_benchmark_rejects_unknown_machine(tmp_path):
    model_path = tmp_path / "model-Q4_K_M.gguf"
    model_path.write_text("fake gguf content")
    with pytest.raises(ValueError, match="Unknown --machine"):
        run_benchmark(model_path, "some-other-laptop")


def test_run_benchmark_rejects_missing_model_file(tmp_path):
    missing = tmp_path / "does-not-exist.gguf"
    with pytest.raises(FileNotFoundError):
        run_benchmark(missing, "rtx-5050")


def test_run_benchmark_model_loading_is_a_documented_seam(tmp_path):
    model_path = tmp_path / "model-Q4_K_M.gguf"
    model_path.write_text("fake gguf content")
    # _load_gguf_model is not wired to real llama.cpp in this scaffolding-only pass
    with pytest.raises(NotImplementedError):
        run_benchmark(model_path, "rtx-5050")


def test_run_benchmark_accepts_dell_g3_as_a_valid_machine(tmp_path):
    model_path = tmp_path / "model-Q4_K_M.gguf"
    model_path.write_text("fake gguf content")
    # still hits the same documented seam, but proves "dell-g3" itself isn't rejected
    with pytest.raises(NotImplementedError):
        run_benchmark(model_path, "dell-g3")
