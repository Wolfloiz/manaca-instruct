import pytest

from src.quantize import _run_conversion, _run_quantize, quantize


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


def test_quantize_returns_one_output_path_per_level(tmp_path, monkeypatch):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    out_dir = tmp_path / "out"
    calls = []

    def fake_conversion(merged, f16, script):
        f16.parent.mkdir(parents=True, exist_ok=True)
        f16.write_text("f16")
        calls.append(("conversion", str(f16)))

    def fake_quantize(f16, level, out, bin):
        out.write_text(level)
        calls.append(("quantize", level, str(out)))

    monkeypatch.setattr("src.quantize._run_conversion", fake_conversion)
    monkeypatch.setattr("src.quantize._run_quantize", fake_quantize)

    outputs = quantize(model_dir, ["Q4_K_M", "Q5_K_M"], out_dir)

    assert [p.name for p in outputs] == ["model-Q4_K_M.gguf", "model-Q5_K_M.gguf"]
    assert all(p.exists() for p in outputs)
    assert calls[0][0] == "conversion"
    assert [c[1] for c in calls if c[0] == "quantize"] == ["Q4_K_M", "Q5_K_M"]


def test_run_conversion_missing_script_raises(tmp_path):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    f16 = tmp_path / "model-f16.gguf"
    with pytest.raises(FileNotFoundError, match="convert_hf_to_gguf.py"):
        _run_conversion(model_dir, f16, tmp_path / "no-such-convert.py")


def test_run_quantize_missing_binary_raises(tmp_path):
    f16 = tmp_path / "model-f16.gguf"
    with pytest.raises(FileNotFoundError, match="llama-quantize"):
        _run_quantize(f16, "Q4_K_M", tmp_path / "out.gguf", tmp_path / "no-such-llama-quantize")


def test_run_conversion_and_quantize_use_real_subprocess(tmp_path, monkeypatch):
    """End-to-end over stub binaries proving the subprocess contract (no llama.cpp needed)."""
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    convert_script = tmp_path / "convert_hf_to_gguf.py"
    convert_script.write_text(
        "import pathlib, sys\n"
        "out = pathlib.Path(sys.argv[sys.argv.index('--outfile') + 1])\n"
        "out.write_text('stub f16 gguf')\n",
        encoding="utf-8",
    )
    # _run_quantize invokes this path directly (real llama-quantize is a compiled
    # binary, not "python llama-quantize"), so the stub needs a shebang + exec bit —
    # a plain script file isn't spawnable on its own (PermissionError otherwise).
    quantize_bin = tmp_path / "llama-quantize"
    quantize_bin.write_text(
        "#!/usr/bin/env python3\n"
        "import pathlib, sys\n"
        "pathlib.Path(sys.argv[2]).write_text('stub quantized')\n",
        encoding="utf-8",
    )
    quantize_bin.chmod(0o755)

    f16 = tmp_path / "model-f16.gguf"
    _run_conversion(model_dir, f16, convert_script)
    assert f16.read_text() == "stub f16 gguf"

    out = tmp_path / "model-Q4_K_M.gguf"
    _run_quantize(f16, "Q4_K_M", out, quantize_bin)
    assert out.read_text() == "stub quantized"
