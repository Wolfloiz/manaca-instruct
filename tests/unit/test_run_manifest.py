import hashlib
import json

import pytest

from src import run_manifest
from src.run_manifest import build_manifest, sha256_of, write_manifest

COMMON_FIELDS = {
    "kind", "run_id", "status", "error", "created_at", "git_commit", "git_dirty",
    "library_versions", "base_model", "datasets", "config", "prompt_format",
}


@pytest.fixture
def fake_environment(monkeypatch):
    monkeypatch.setattr(run_manifest, "_git_info", lambda: ("abc123" * 6 + "abcd", False))
    monkeypatch.setattr(run_manifest, "_base_model_revision", lambda repo_id: ("deadbeef", "hub"))
    monkeypatch.setattr(run_manifest, "_library_versions", lambda: {name: "1.0" for name in run_manifest.TRACKED_LIBRARIES})


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def test_sha256_of_matches_hashlib(tmp_path):
    f = tmp_path / "data.jsonl"
    f.write_bytes(b'{"a": 1}\n{"a": 2}\n')
    assert sha256_of(f) == hashlib.sha256(f.read_bytes()).hexdigest()


def test_build_manifest_has_all_common_fields_and_dataset_entries(tmp_path, fake_environment):
    train = _write_jsonl(tmp_path / "train.jsonl", [{"x": 1}, {"x": 2}, {"x": 3}])
    manifest = build_manifest(
        "training",
        "qlora-v3a",
        base_model="menezesbruno/manaca-1b-base",
        datasets=[train],
        config={"lora": {"r": 16}},
        prompt_format="train-template",
        best_epoch=2,
    )
    assert COMMON_FIELDS <= manifest.keys()
    assert manifest["status"] == "ok" and manifest["error"] is None
    assert manifest["git_dirty"] is False
    assert manifest["base_model"] == {"repo_id": "menezesbruno/manaca-1b-base", "revision": "deadbeef", "revision_source": "hub"}
    assert manifest["datasets"] == [{"path": str(train), "sha256": sha256_of(train), "rows": 3}]
    assert manifest["library_versions"]["trl"] == "1.0"
    assert manifest["best_epoch"] == 2  # extra fields pass through
    assert manifest["created_at"].endswith("Z")


def test_dataset_row_count_ignores_blank_lines(tmp_path, fake_environment):
    f = tmp_path / "val.jsonl"
    f.write_text('{"a": 1}\n\n{"a": 2}\n\n', encoding="utf-8")
    manifest = build_manifest("evaluation", "r", base_model="m", datasets=[f], config={}, prompt_format="combined")
    assert manifest["datasets"][0]["rows"] == 2


def test_failed_status_is_recorded(tmp_path, fake_environment):
    manifest = build_manifest(
        "training", "r", base_model="m", datasets=[], config={}, prompt_format="train-template",
        status="failed", error="CUDA out of memory",
    )
    assert manifest["status"] == "failed"
    assert manifest["error"] == "CUDA out of memory"


def test_rejects_unknown_kind(fake_environment):
    with pytest.raises(ValueError, match="kind"):
        build_manifest("benchmark", "r", base_model="m", datasets=[], config={}, prompt_format="combined")


def test_write_manifest_writes_byte_identical_copies(tmp_path, fake_environment):
    manifest = build_manifest("training", "r", base_model="m", datasets=[], config={"k": "v"}, prompt_format="x")
    primary = tmp_path / "adapters" / "r" / "run_manifest.json"
    mirror = tmp_path / "runs" / "r.manifest.json"
    write_manifest(primary, manifest, copies=[mirror])
    assert primary.read_bytes() == mirror.read_bytes()
    assert json.loads(primary.read_text(encoding="utf-8"))["config"] == {"k": "v"}


def test_base_model_revision_falls_back_to_local_cache(tmp_path, monkeypatch):
    import types

    fake_hub = types.SimpleNamespace(
        model_info=lambda repo_id: (_ for _ in ()).throw(OSError("offline")),
        constants=types.SimpleNamespace(HF_HUB_CACHE=str(tmp_path)),
    )
    monkeypatch.setitem(__import__("sys").modules, "huggingface_hub", fake_hub)
    ref = tmp_path / "models--menezesbruno--manaca-1b-base" / "refs" / "main"
    ref.parent.mkdir(parents=True)
    ref.write_text("cafe0123\n", encoding="utf-8")
    assert run_manifest._base_model_revision("menezesbruno/manaca-1b-base") == ("cafe0123", "local-cache")


def test_base_model_revision_unavailable_without_hub_or_cache(tmp_path, monkeypatch):
    import types

    fake_hub = types.SimpleNamespace(
        model_info=lambda repo_id: (_ for _ in ()).throw(OSError("offline")),
        constants=types.SimpleNamespace(HF_HUB_CACHE=str(tmp_path)),
    )
    monkeypatch.setitem(__import__("sys").modules, "huggingface_hub", fake_hub)
    assert run_manifest._base_model_revision("org/none") == (None, "unavailable")
