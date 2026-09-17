"""Publish the merged model + GGUF artifacts + model card to Hugging Face Hub.

Usage:

    python -m src.publish --model models/merged/manaca-instruct-pt --gguf-dir models/gguf/ \\
        --eval-results eval/results/qlora-v1.jsonl eval/results/baseline.jsonl eval/results/official-instruct.jsonl \\
        --repo-id <hf-username>/manaca-instruct-pt

Implements FR-009/FR-010 and contracts/model-usage-contract.md's pre-publish
gate: refuses to push if the model card is missing its license front matter,
either usage snippet, or a populated evaluation section.

The push itself (`_push_to_hub`) wraps huggingface_hub.create_repo +
upload_folder, authenticated via the HUGGING_FACE_HUB_TOKEN env var (or a
prior `huggingface-cli login`) — never a token committed to the repo. Per
tasks.md this remains the author's own final sign-off (T058); the gate
(`validate_model_card`) is the part safe to run anywhere and is fully tested.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

REQUIRED_FRONT_MATTER_FIELDS = {"license", "language", "base_model"}
REQUIRED_BODY_MARKERS = [
    r"transformers",  # from_pretrained usage snippet (contracts/model-usage-contract.md #3)
    r"llama",  # llama.cpp / GGUF usage snippet
    r"##\s*Evalua",  # an "Evaluation results" section header (PT or EN)
]


class ModelCardError(ValueError):
    """Raised when the model card fails contracts/model-usage-contract.md's pre-publish gate."""


def _parse_front_matter(model_card_text: str) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n", model_card_text, re.DOTALL)
    if not match:
        raise ModelCardError("model card is missing YAML front matter (--- ... --- block)")
    front_matter = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            front_matter[key.strip()] = value.strip()
    return front_matter


def validate_model_card(model_card_text: str) -> None:
    """contracts/model-usage-contract.md's pre-publish gate. Raises ModelCardError on any violation."""
    front_matter = _parse_front_matter(model_card_text)

    missing_fields = REQUIRED_FRONT_MATTER_FIELDS - front_matter.keys()
    if missing_fields:
        raise ModelCardError(f"model card front matter missing required field(s): {sorted(missing_fields)}")

    if front_matter.get("license") != "cc-by-nc-4.0":
        raise ModelCardError(
            f"model card license is {front_matter.get('license')!r}, expected 'cc-by-nc-4.0' "
            "per research.md §1's dataset-license precedent"
        )

    for pattern in REQUIRED_BODY_MARKERS:
        if not re.search(pattern, model_card_text, re.IGNORECASE):
            raise ModelCardError(f"model card body is missing required content matching {pattern!r}")


def _push_to_hub(model_dir: Path, gguf_dir: Path, model_card_text: str, repo_id: str) -> str:
    """Create the HF repo and upload the merged model, GGUF files, and model card.

    Requires a HUGGING_FACE_HUB_TOKEN env var (or `huggingface-cli login`).
    GGUF files go under a `gguf/` subfolder in the repo so the model card's
    llama-cli snippet (which references `manaca-instruct-pt-Q4_K_M.gguf`) maps
    to a stable path. Returns the model page URL.
    """
    from huggingface_hub import HfApi, create_repo

    if (
        not os.environ.get("HF_TOKEN")
        and not os.environ.get("HUGGING_FACE_HUB_TOKEN")
        and not Path.home().joinpath(".cache/huggingface/token").exists()
    ):
        raise RuntimeError(
            "no Hugging Face token found — set HF_TOKEN or run `hf auth login` "
            "(tasks.md T058; the token is never committed to this repo)"
        )

    api = HfApi()
    create_repo(repo_id=repo_id, repo_type="model", exist_ok=True)
    api.upload_folder(repo_id=repo_id, folder_path=str(model_dir), commit_message="Publish merged model")
    # Only this model's quantized files: models/gguf/ also holds the 3.4 GB f16 intermediate and
    # whatever other GGUFs were downloaded locally (the Qwen2.5 seed generator, for one), and
    # upload_folder would otherwise push the whole directory.
    gguf_patterns = [f"{model_dir.name}-*.gguf"]
    if gguf_dir.is_dir() and any(p for pat in gguf_patterns for p in gguf_dir.glob(pat) if not p.name.endswith("-f16.gguf")):
        api.upload_folder(
            repo_id=repo_id, folder_path=str(gguf_dir), path_in_repo="gguf", commit_message="Publish GGUF artifacts",
            allow_patterns=gguf_patterns, ignore_patterns=["*-f16.gguf"],
        )
    api.upload_file(
        repo_id=repo_id,
        path_in_repo="README.md",
        path_or_fileobj=model_card_text.encode("utf-8"),
        commit_message="Publish model card",
    )
    return f"https://huggingface.co/{repo_id}"


def publish(model_dir: Path, gguf_dir: Path, model_card_path: Path, repo_id: str) -> str:
    model_card_text = model_card_path.read_text(encoding="utf-8")
    validate_model_card(model_card_text)  # raises ModelCardError before any network call
    return _push_to_hub(model_dir, gguf_dir, model_card_text, repo_id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--gguf-dir", required=True, type=Path)
    parser.add_argument("--eval-results", nargs="+", type=Path, required=True)
    parser.add_argument("--model-card", type=Path, default=Path("MODEL_CARD.md"))
    parser.add_argument("--repo-id", required=True)
    args = parser.parse_args(argv)

    url = publish(args.model, args.gguf_dir, args.model_card, args.repo_id)
    print(f"Published to {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
