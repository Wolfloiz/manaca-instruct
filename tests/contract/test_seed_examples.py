"""Contract tests for data/seed/ (specs/002 contracts/dataset-preparation.md, FR-011).

Skip until data/seed/ exists (tasks.md T036 — the author generates and reviews the rows).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pytest

from src.dataset_filters.quality import is_degenerate_output
from src.prepare_dataset import _load_eval_prompt_keys
from src.schema_validation import validate_instruction_example
from src.text_normalize import normalize

SEED_DIR = Path("data/seed")
SEED_FILE = SEED_DIR / "classification_4class.jsonl"
README = SEED_DIR / "README.md"

LABELS = {"reclamação", "dúvida", "elogio", "solicitação"}
INSTRUCTION = "Classifique a mensagem como reclamação, dúvida, elogio ou solicitação"
MIN_PER_LABEL = 30
MAX_LABEL_SHARE = 0.40
_ID = re.compile(r"^seed-llm-\d{6}$")
_PROVENANCE_PHRASE = re.compile(r"modelo gerador|generating model", re.IGNORECASE)


@pytest.fixture(scope="module")
def seed_rows():
    if not SEED_DIR.exists():
        pytest.skip("data/seed/ absent — seed examples not yet authored (T036)")
    assert SEED_FILE.exists(), f"{SEED_FILE} missing"
    rows = [json.loads(line) for line in SEED_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in rows:
        validate_instruction_example(row)
    return rows


def test_rows_have_the_seed_shape(seed_rows):
    for row in seed_rows:
        assert _ID.match(row["id"]), row["id"]
        assert row["source"] == "seed-llm"
        assert row["task_category"] == "classification"
        assert row["instruction"] == INSTRUCTION
        assert row["input"].strip()
        assert row["output"] in LABELS, row["id"]
        assert not is_degenerate_output(row["output"])


def test_ids_are_unique(seed_rows):
    ids = [r["id"] for r in seed_rows]
    assert len(ids) == len(set(ids))


def test_at_least_thirty_rows_per_label_and_no_label_dominates(seed_rows):
    counts = Counter(r["output"] for r in seed_rows)
    for label in LABELS:
        assert counts[label] >= MIN_PER_LABEL, f"{label}: {counts[label]} < {MIN_PER_LABEL}"
    assert max(counts.values()) / len(seed_rows) <= MAX_LABEL_SHARE, dict(counts)


def test_no_row_reuses_an_evaluation_prompt(seed_rows):
    keys = _load_eval_prompt_keys(Path("data/eval"))
    for row in seed_rows:
        assert (normalize(row["instruction"]), normalize(row["input"])) not in keys.pairs, row["id"]
        assert normalize(f"{row['instruction']}: {row['input']}") not in keys.prompts, row["id"]


def test_readme_records_the_generating_model(seed_rows):
    assert README.exists(), "data/seed/README.md is required (generating model, terms, counts, confirmation)"
    text = README.read_text(encoding="utf-8")
    assert _PROVENANCE_PHRASE.search(text), "README must name the generating model ('modelo gerador' / 'generating model')"
    assert "<FILL" not in text and "TODO" not in text
