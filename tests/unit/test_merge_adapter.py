import json

import pytest

from src.merge_adapter import _base_model_name, merge_adapter


def test_merge_adapter_rejects_missing_adapter_path(tmp_path):
    missing = tmp_path / "does-not-exist"
    out_dir = tmp_path / "out"
    with pytest.raises(FileNotFoundError):
        merge_adapter(missing, out_dir)


def test_base_model_name_reads_adapter_config(tmp_path):
    adapter_dir = tmp_path / "adapter"
    adapter_dir.mkdir()
    (adapter_dir / "adapter_config.json").write_text(
        json.dumps({"base_model_name_or_path": "menezesbruno/manaca-1b-base", "r": 16}),
        encoding="utf-8",
    )
    assert _base_model_name(adapter_dir) == "menezesbruno/manaca-1b-base"


def test_base_model_name_rejects_adapter_without_config(tmp_path):
    adapter_dir = tmp_path / "adapter"
    adapter_dir.mkdir()
    with pytest.raises(FileNotFoundError, match="adapter_config.json"):
        _base_model_name(adapter_dir)


def test_base_model_name_rejects_config_without_base_model(tmp_path):
    adapter_dir = tmp_path / "adapter"
    adapter_dir.mkdir()
    (adapter_dir / "adapter_config.json").write_text(json.dumps({"r": 16}), encoding="utf-8")
    with pytest.raises(ValueError, match="base_model_name_or_path"):
        _base_model_name(adapter_dir)


def test_merge_adapter_orchestrates_load_and_merge_with_mocked_stack(tmp_path, monkeypatch):
    adapter_dir = tmp_path / "adapter"
    adapter_dir.mkdir()
    (adapter_dir / "adapter_config.json").write_text(
        json.dumps({"base_model_name_or_path": "menezesbruno/manaca-1b-base"}),
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    fake_model = object()
    monkeypatch.setattr("src.merge_adapter._load_base_and_adapter", lambda path: fake_model)
    saved_to = []
    monkeypatch.setattr(
        "src.merge_adapter._merge_and_save",
        lambda model, out: saved_to.append((model, out)),
    )

    result = merge_adapter(adapter_dir, out_dir)

    assert result == out_dir
    assert out_dir.is_dir()
    assert saved_to == [(fake_model, out_dir)]
