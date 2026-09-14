import json

import pytest

from src.evaluate import _read_prompts, run_evaluation, write_results_jsonl


def test_read_prompts_validates_and_yields_rows(tmp_path):
    prompt_file = tmp_path / "prompts.jsonl"
    prompt_file.write_text(
        json.dumps(
            {
                "id": "p1",
                "group": "grupo_a",
                "task_category": "classification",
                "prompt": "Classifique: oi",
                "expected": "dúvida",
                "grading_method": "rule_based",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    rows = list(_read_prompts([prompt_file]))
    assert len(rows) == 1
    assert rows[0]["id"] == "p1"


def test_write_results_jsonl_roundtrips(tmp_path):
    results = [{"id": "a", "score": 1}, {"id": "b", "score": 0}]
    out_path = tmp_path / "eval" / "results" / "run.jsonl"
    write_results_jsonl(results, out_path)
    lines = out_path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line) for line in lines] == results


def test_run_evaluation_rejects_unknown_model(tmp_path):
    with pytest.raises(ValueError, match="Unknown --model"):
        run_evaluation("not-a-real-model", None, [], "run1")


def test_run_evaluation_model_loading_is_a_documented_seam(tmp_path):
    prompt_file = tmp_path / "prompts.jsonl"
    prompt_file.write_text(
        json.dumps(
            {
                "id": "p1",
                "group": "grupo_a",
                "task_category": "classification",
                "prompt": "Classifique: oi",
                "expected": "dúvida",
                "grading_method": "rule_based",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    # _load_model is not wired to real weights in this scaffolding-only pass (see evaluate.py's docstring)
    with pytest.raises(NotImplementedError):
        run_evaluation("manaca-1b-base", None, [prompt_file], "run1")
