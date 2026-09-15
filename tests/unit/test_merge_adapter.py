import json

import pytest

from src.merge_adapter import _base_model_name, _copy_raw_tokenizer_files, merge_adapter


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


def test_copy_raw_tokenizer_files_fetches_and_copies(tmp_path, monkeypatch):
    # simulate a cached tokenizer.model but no special_tokens_map.json for this repo
    cached_file = tmp_path / "cache" / "tokenizer.model"
    cached_file.parent.mkdir(parents=True)
    cached_file.write_text("fake sentencepiece model", encoding="utf-8")

    from huggingface_hub.errors import EntryNotFoundError

    def fake_hf_hub_download(repo_id, filename):
        if filename == "tokenizer.model":
            return str(cached_file)
        raise EntryNotFoundError(f"no {filename} for {repo_id}")

    monkeypatch.setattr("huggingface_hub.hf_hub_download", fake_hf_hub_download)

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    _copy_raw_tokenizer_files("menezesbruno/manaca-1b-base", out_dir)

    assert (out_dir / "tokenizer.model").read_text(encoding="utf-8") == "fake sentencepiece model"
    assert not (out_dir / "special_tokens_map.json").exists()  # EntryNotFoundError -> skipped, not an error
