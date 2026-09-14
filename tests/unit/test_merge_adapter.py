import pytest

from src.merge_adapter import merge_adapter


def test_merge_adapter_rejects_missing_adapter_path(tmp_path):
    missing = tmp_path / "does-not-exist"
    out_dir = tmp_path / "out"
    with pytest.raises(FileNotFoundError):
        merge_adapter(missing, out_dir)


def test_merge_adapter_model_loading_is_a_documented_seam(tmp_path):
    adapter_dir = tmp_path / "adapter"
    adapter_dir.mkdir()
    out_dir = tmp_path / "out"
    # _load_base_and_adapter is not wired to real weights in this scaffolding-only pass
    with pytest.raises(NotImplementedError):
        merge_adapter(adapter_dir, out_dir)
