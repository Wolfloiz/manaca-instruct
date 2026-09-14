import json

from src.grading.review_cli import review_file


def _write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def test_review_file_grades_pending_rows_and_persists(tmp_path):
    results_path = tmp_path / "run.jsonl"
    _write_jsonl(
        results_path,
        [
            {"id": "a", "grading_method": "manual_review", "score": None, "task_category": None,
             "model": "manaca-1b-base", "prompt": "p1", "expected": None, "output": "o1", "run_id": "r"},
            {"id": "b", "grading_method": "rule_based", "score": 1, "task_category": "classification",
             "model": "manaca-1b-base", "prompt": "p2", "expected": "x", "output": "x", "run_id": "r"},
        ],
    )

    answers = iter(["1"])  # grade row "a" as correct
    graded, still_pending = review_file(results_path, input_fn=lambda _: next(answers))

    assert graded == 1
    assert still_pending == 0
    saved = [json.loads(line) for line in results_path.read_text(encoding="utf-8").splitlines()]
    assert saved[0]["score"] == 1.0
    assert saved[1]["score"] == 1  # untouched rule_based row unaffected


def test_review_file_skip_leaves_row_pending(tmp_path):
    results_path = tmp_path / "run.jsonl"
    _write_jsonl(
        results_path,
        [
            {"id": "a", "grading_method": "manual_review", "score": None, "task_category": None,
             "model": "manaca-1b-base", "prompt": "p1", "expected": None, "output": "o1", "run_id": "r"},
        ],
    )

    answers = iter(["s"])
    graded, still_pending = review_file(results_path, input_fn=lambda _: next(answers))

    assert graded == 0
    assert still_pending == 1


def test_review_file_invalid_input_is_reprompted(tmp_path):
    results_path = tmp_path / "run.jsonl"
    _write_jsonl(
        results_path,
        [
            {"id": "a", "grading_method": "manual_review", "score": None, "task_category": None,
             "model": "manaca-1b-base", "prompt": "p1", "expected": None, "output": "o1", "run_id": "r"},
        ],
    )

    answers = iter(["banana", "0.5"])
    graded, still_pending = review_file(results_path, input_fn=lambda _: next(answers))

    assert graded == 1
    assert still_pending == 0
