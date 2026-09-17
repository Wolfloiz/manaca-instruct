import json
from pathlib import Path

from src.grading import category_session, review_cli


def _row(i, category, score=None, method="manual_review"):
    return {
        "id": f"grupo_a-{category}-{i:03d}", "task_category": category, "model": "m", "prompt": f"p{i}",
        "expected": None, "output": f"o{i}", "grading_method": method, "run_id": "r", "latency_ms": 1.0, "score": score,
    }


def _write(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_category_session_regrades_only_the_category_and_merges_into_real_blind_file(tmp_path):
    original = tmp_path / "qlora-x.jsonl"
    _write(original, [_row(1, "grammar_correction"), _row(2, "grammar_correction"), _row(3, "rewriting"),
                      _row(4, "classification", score=1.0, method="rule_based")])
    real_blind = tmp_path / "qlora-x-blind.jsonl"
    _write(real_blind, [_row(1, "grammar_correction", 1.0), _row(2, "grammar_correction", 1.0), _row(3, "rewriting", 0.5),
                        _row(4, "classification", score=1.0, method="rule_based")])
    before = review_cli._sha256(original)
    answers = iter(["0", "0.5"])

    category_session.main(
        ["--category", "grammar_correction", "--shuffle-seed", "1", "--workdir", str(tmp_path / "wd"), str(original)],
        input_fn=lambda prompt="": next(answers),
    )

    rows = {r["id"]: r for r in review_cli._load_rows(real_blind)}
    assert {rows["grupo_a-grammar_correction-001"]["score"], rows["grupo_a-grammar_correction-002"]["score"]} == {0.0, 0.5}
    assert rows["grupo_a-rewriting-003"]["score"] == 0.5  # untouched
    assert rows["grupo_a-classification-004"]["score"] == 1.0
    assert review_cli._sha256(original) == before
    # session files hold only the category and are resumable (nothing pending now)
    session_rows = review_cli._load_rows(tmp_path / "wd" / "qlora-x.jsonl")
    assert [r["task_category"] for r in session_rows] == ["grammar_correction", "grammar_correction"]


def test_exclude_mode_creates_the_real_blind_file_when_missing(tmp_path):
    original = tmp_path / "qlora-y.jsonl"
    _write(original, [_row(1, "grammar_correction"), _row(2, "rewriting"), _row(3, "classification", score=0.0, method="rule_based")])
    category_session.main(
        ["--exclude", "grammar_correction", "--shuffle-seed", "1", "--workdir", str(tmp_path / "wd"), str(original)],
        input_fn=lambda prompt="": "1",
    )

    rows = {r["id"]: r for r in review_cli._load_rows(tmp_path / "qlora-y-blind.jsonl")}
    assert rows["grupo_a-rewriting-002"]["score"] == 1.0
    assert rows["grupo_a-grammar_correction-001"]["score"] is None  # left for the category session
    assert rows["grupo_a-classification-003"]["score"] == 0.0
