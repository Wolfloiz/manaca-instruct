import pytest

from src.quantize import quantize


def test_quantize_rejects_missing_model_dir(tmp_path):
    missing = tmp_path / "does-not-exist"
    with pytest.raises(FileNotFoundError):
        quantize(missing, ["Q4_K_M", "Q5_K_M"], tmp_path / "out")


def test_quantize_rejects_unsupported_level(tmp_path):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    with pytest.raises(ValueError, match="Unsupported quantization level"):
        quantize(model_dir, ["Q4_K_M", "NOT_A_LEVEL"], tmp_path / "out")


def test_quantize_requires_at_least_two_levels_per_fr006(tmp_path):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    with pytest.raises(ValueError, match="at least 2"):
        quantize(model_dir, ["Q4_K_M"], tmp_path / "out")


def test_quantize_conversion_is_a_documented_seam(tmp_path):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    # _run_conversion is not wired to real llama.cpp binaries in this scaffolding-only pass
    with pytest.raises(NotImplementedError):
        quantize(model_dir, ["Q4_K_M", "Q5_K_M"], tmp_path / "out")
