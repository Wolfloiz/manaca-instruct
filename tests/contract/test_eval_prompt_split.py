"""Contract test for specs/002-data-quality-iteration/contracts/evaluation-presentation.md:
the authored instruction/input split must reconstruct every frozen grupo_a prompt exactly,
and grupo_b rows must not carry the split fields."""

import json
from pathlib import Path

from src.schema_validation import validate_evaluation_prompt

EVAL_DIR = Path("data/eval")


def _rows(name: str) -> list[dict]:
    with (EVAL_DIR / name).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_every_grupo_a_row_has_split_fields_that_reconstruct_prompt():
    rows = _rows("grupo_a_prompts.jsonl")
    assert len(rows) == 80
    for row in rows:
        assert "instruction" in row and "input" in row, row["id"]
        assert row["input"], f"{row['id']}: grupo_a rows always have a text to operate on"
        assert f"{row['instruction']}: {row['input']}" == row["prompt"], row["id"]
        validate_evaluation_prompt(row)


def test_grupo_b_rows_carry_no_split_fields():
    for row in _rows("grupo_b_prompts.jsonl"):
        assert "instruction" not in row and "input" not in row, row["id"]
        validate_evaluation_prompt(row)


def test_split_instruction_is_consistent_within_each_category():
    rows = _rows("grupo_a_prompts.jsonl")
    for category in ("grammar_correction", "classification", "rewriting"):
        instructions = {r["instruction"] for r in rows if r["task_category"] == category}
        assert len(instructions) == 1, (category, instructions)  # one wording per category, as authored in 001
