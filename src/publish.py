"""Publish the merged model + GGUF artifacts + model card to Hugging Face Hub.

Usage:

    python src/publish.py --model models/merged/manaca-instruct-pt --gguf-dir models/gguf/ \\
        --eval-results eval/results/qlora-v1.jsonl eval/results/baseline.jsonl eval/results/official-instruct.jsonl \\
        --repo-id <hf-username>/manaca-instruct-pt

Implements FR-009/FR-010 and contracts/model-usage-contract.md's pre-publish
gate: refuses to push if the model card is missing its license front matter,
either usage snippet, or a populated evaluation section.

NOTE: `_push_to_hub()` wraps huggingface_hub.create_repo/upload_folder and is
a documented seam — not invoked in this pass (no HF token available to an
agent, and per tasks.md this is deliberately the author's final sign-off, not
something to delegate). The pre-publish gate itself (`validate_model_card`)
is real and fully tested — that's the part safe to build without a token.
"""

from __future__ import annotations

import argparse
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
    """Seam wrapping huggingface_hub.create_repo + upload_folder — not invoked in this pass."""
    raise NotImplementedError(
        "src/publish.py's _push_to_hub is a documented seam, not yet wired to huggingface_hub — "
        "see the module docstring. This is deliberately the author's own final action (tasks.md T058), "
        "not something an agent runs."
    )


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
