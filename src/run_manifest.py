"""Provenance manifests for training and evaluation runs
(specs/002-data-quality-iteration/contracts/run-manifest-schema.md).

A manifest is what lets a result be attributed to exactly one data fingerprint,
configuration and code version — feature 001's qlora-v2 changed data and epochs at
the same time and nothing in it could be attributed afterwards. `write_manifest`
is called by `src/train_qlora.py` and `src/evaluate.py`; the field lookups that
touch git, installed packages or the Hub live in small helpers so tests can
replace them.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

TRACKED_LIBRARIES = ("torch", "transformers", "peft", "trl", "bitsandbytes", "datasets")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_info() -> tuple[str | None, bool | None]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = bool(
            subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True).stdout.strip()
        )
        return commit, dirty
    except (subprocess.SubprocessError, FileNotFoundError):
        return None, None


def _library_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for name in TRACKED_LIBRARIES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def _base_model_revision(repo_id: str) -> tuple[str | None, str]:
    """(revision, source): Hub commit sha when reachable, else the locally cached ref, else nothing."""
    try:
        from huggingface_hub import model_info

        return model_info(repo_id).sha, "hub"
    except Exception:  # offline, no token, or huggingface_hub missing — never fail a run over provenance
        pass
    try:
        from huggingface_hub import constants

        ref = Path(constants.HF_HUB_CACHE) / f"models--{repo_id.replace('/', '--')}" / "refs" / "main"
        if ref.exists():
            return ref.read_text(encoding="utf-8").strip(), "local-cache"
    except Exception:
        pass
    return None, "unavailable"


def _dataset_entries(paths: list[Path]) -> list[dict]:
    entries = []
    for path in paths:
        path = Path(path)
        with path.open("rb") as f:
            rows = sum(1 for line in f if line.strip())
        entries.append({"path": str(path), "sha256": sha256_of(path), "rows": rows})
    return entries


def build_manifest(
    kind: str,
    run_id: str,
    *,
    base_model: str,
    datasets: list[Path],
    config: dict,
    prompt_format: str,
    status: str = "ok",
    error: str | None = None,
    **extra,
) -> dict:
    if kind not in ("training", "evaluation"):
        raise ValueError(f"kind must be 'training' or 'evaluation', got {kind!r}")
    commit, dirty = _git_info()
    revision, revision_source = _base_model_revision(base_model)
    manifest = {
        "kind": kind,
        "run_id": run_id,
        "status": status,
        "error": error,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "git_commit": commit,
        "git_dirty": dirty,
        "library_versions": _library_versions(),
        "base_model": {"repo_id": base_model, "revision": revision, "revision_source": revision_source},
        "datasets": _dataset_entries(datasets),
        "config": config,
        "prompt_format": prompt_format,
    }
    manifest.update(extra)
    return manifest


def write_manifest(path: Path, manifest: dict, copies: list[Path] = ()) -> dict:
    """Write `manifest` to `path` and byte-identical copies (e.g. the tracked runs/ mirror)."""
    payload = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    for target in (Path(path), *map(Path, copies)):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")
    return manifest
