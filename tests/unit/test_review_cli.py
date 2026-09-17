import json
import pytest

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


# --- feature 002 (T017): blind / interleaved mode writing -blind siblings
import hashlib

from src.grading.review_cli import _prompt_for_score, blind_output_path, main, review_blind


def _row(id_, run_id, score=None, method="manual_review", category="rewriting"):
    return {"id": id_, "grading_method": method, "score": score, "task_category": category,
            "model": "manaca-instruct-pt", "prompt": f"p-{id_}", "expected": None, "output": f"o-{id_}", "run_id": run_id}


def test_blind_prompt_hides_model_and_run_id(capsys):
    row = _row("grupo_a-rewriting-001", "qlora-v2")
    _prompt_for_score(row, 3, 10, input_fn=lambda _: "1", blind=True)
    shown = capsys.readouterr().out
    assert "model=" not in shown and "run_id" not in shown and "qlora-v2" not in shown and "id=" not in shown
    assert "[3/10]" in shown and "task_category=rewriting" in shown and "p-grupo_a-rewriting-001" in shown


def test_blind_output_path_and_rejection_of_blind_input(tmp_path):
    assert blind_output_path(tmp_path / "qlora-v2.jsonl") == tmp_path / "qlora-v2-blind.jsonl"
    with pytest.raises(ValueError):
        blind_output_path(tmp_path / "qlora-v2-blind.jsonl")


def test_interleaved_session_routes_grades_and_never_touches_inputs(tmp_path):
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    _write_jsonl(a, [_row("x", "a", score=1.0), _row("y", "a", score=1, method="rule_based", category="classification")])
    _write_jsonl(b, [_row("x", "b", score=0.0), _row("z", "b")])
    a_before, b_before = hashlib.sha256(a.read_bytes()).hexdigest(), hashlib.sha256(b.read_bytes()).hexdigest()

    answers = iter(["0.5", "1", "0"])
    summary = review_blind([a, b], input_fn=lambda _: next(answers), shuffle_seed=3)

    assert hashlib.sha256(a.read_bytes()).hexdigest() == a_before
    assert hashlib.sha256(b.read_bytes()).hexdigest() == b_before
    a_blind = {r["id"]: r for r in (json.loads(l) for l in (tmp_path / "a-blind.jsonl").read_text().splitlines())}
    b_blind = {r["id"]: r for r in (json.loads(l) for l in (tmp_path / "b-blind.jsonl").read_text().splitlines())}
    # original manual grades were reset and then re-graded blind; rule_based kept; run_id preserved
    assert a_blind["x"]["score"] in (0.5, 1.0, 0.0) and a_blind["x"]["run_id"] == "a"
    assert a_blind["y"]["score"] == 1
    assert {a_blind["x"]["score"], b_blind["x"]["score"], b_blind["z"]["score"]} == {0.5, 1.0, 0.0}
    assert summary == {tmp_path / "a-blind.jsonl": (1, 0), tmp_path / "b-blind.jsonl": (2, 0)}


def test_blind_session_is_resumable_and_only_fills_nulls(tmp_path):
    a = tmp_path / "a.jsonl"
    _write_jsonl(a, [_row("x", "a"), _row("y", "a")])
    # first session: grade x, quit before y
    answers = iter(["1", "q"])
    review_blind([a], input_fn=lambda _: next(answers), shuffle_seed=0)
    blind = tmp_path / "a-blind.jsonl"
    first = [json.loads(l) for l in blind.read_text().splitlines()]
    assert [r["score"] for r in first] == [1.0, None] or [r["score"] for r in first] == [None, 1.0]
    # second session: only the null one is asked, the existing grade is untouched
    asked = []
    review_blind([a], input_fn=lambda _: asked.append("0.5") or "0.5", shuffle_seed=0)
    second = [json.loads(l) for l in blind.read_text().splitlines()]
    assert len(asked) == 1
    assert sorted(r["score"] for r in second) == [0.5, 1.0]


def test_shuffle_seed_is_deterministic(tmp_path):
    rows = [_row(f"r{i}", "a") for i in range(6)]
    orders = []
    for _ in range(2):
        a = tmp_path / f"run{_}.jsonl"
        _write_jsonl(a, rows)
        seen = []
        review_blind([a], input_fn=lambda t: seen.append(t) or "s", shuffle_seed=42)
        # capture presentation order via the prompt text printed… simpler: reconstruct from skip order
        orders.append(seen)
    assert orders[0] == orders[1]


def test_main_requires_interleave_for_several_files_and_seed_with_interleave(tmp_path):
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    _write_jsonl(a, [_row("x", "a")]); _write_jsonl(b, [_row("x", "b")])
    with pytest.raises(SystemExit):
        main([str(a), str(b)])
    with pytest.raises(SystemExit):
        main([str(a), str(b), "--interleave"])


def test_legacy_in_place_mode_still_supports_quit(tmp_path):
    a = tmp_path / "a.jsonl"
    _write_jsonl(a, [_row("x", "a"), _row("y", "a")])
    answers = iter(["1", "q"])
    graded, pending = review_file(a, input_fn=lambda _: next(answers))
    assert (graded, pending) == (1, 1)
