import json
from pathlib import Path

import pytest

from src.grading.report import FOOTNOTE, compare_runs, main, protocol_for, render_markdown, summarize_run


def _row(id_, run_id, category, score):
    return {"id": id_, "task_category": category, "model": "manaca-instruct-pt", "prompt": "p", "expected": None,
            "output": "o", "grading_method": "rule_based" if category == "classification" else "manual_review",
            "score": score, "run_id": run_id}


RUN_A = [
    _row("g1", "a", "grammar_correction", 1), _row("g2", "a", "grammar_correction", 0.5), _row("g3", "a", "grammar_correction", 0),
    _row("c1", "a", "classification", 1), _row("c2", "a", "classification", 0),
    _row("b1", "a", None, 1), _row("b2", "a", None, None),
]
RUN_B = [
    _row("g1", "b", "grammar_correction", 1), _row("g2", "b", "grammar_correction", 1), _row("g3", "b", "grammar_correction", 0),
    _row("c1", "b", "classification", 0), _row("c2", "b", "classification", 0),
    _row("b1", "b", None, 0.5), _row("b2", "b", None, 1),
]


def _write(path: Path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def test_summarize_run_matches_hand_computed_values():
    s = summarize_run(RUN_A)
    assert s["grammar_correction"] == {"n": 3, "mean": 0.5, "full_rate": pytest.approx(1 / 3), "n1": 1, "n05": 1, "n0": 1, "n_null": 0}
    assert s["classification"] == {"n": 2, "mean": 0.5, "full_rate": 0.5, "n1": 1, "n05": 0, "n0": 1, "n_null": 0}
    assert s["grupo_b"] == {"n": 2, "mean": 1.0, "full_rate": 1.0, "n1": 1, "n05": 0, "n0": 0, "n_null": 1}


def test_null_scores_are_visible_and_do_not_change_mean():
    s = summarize_run([_row("x", "a", "rewriting", 1), _row("y", "a", "rewriting", None)])
    assert s["rewriting"]["mean"] == 1.0 and s["rewriting"]["n_null"] == 1
    assert summarize_run([_row("y", "a", "rewriting", None)])["rewriting"]["mean"] is None


def test_compare_runs_counts_improved_worsened_tied_and_not_comparable():
    c = compare_runs(RUN_A, RUN_B)
    assert c["grammar_correction"] == {"improved": 1, "worsened": 0, "tied": 2, "not_comparable": 0}
    assert c["classification"] == {"improved": 0, "worsened": 1, "tied": 1, "not_comparable": 0}
    assert c["grupo_b"] == {"improved": 0, "worsened": 1, "tied": 0, "not_comparable": 1}


def test_protocol_detection():
    assert protocol_for(Path("eval/results/qlora-v2-blind.jsonl"), "qlora-v2") == "blind"
    assert protocol_for(Path("eval/results/qlora-v3a-split.jsonl"), "qlora-v3a-split") == "blind"
    assert protocol_for(Path("eval/results/baseline.jsonl"), "baseline") == "earlier (non-blind)"


def test_render_markdown_has_table_pairs_and_verbatim_footnote(tmp_path):
    a, b = tmp_path / "a-blind.jsonl", tmp_path / "b.jsonl"
    md = render_markdown([(a, "a", RUN_A), (b, "b", RUN_B)], [("a", "b")])
    assert "| a | blind | grammar_correction | 3 | 0.500 | 0.333 | 1 | 1 | 1 | 0 |" in md
    assert "| b | earlier (non-blind) | classification | 2 | 0.000 | 0.000 (0/2 correct) | 0 | 0 | 2 | 0 |" in md
    assert "### a → b" in md and "| grammar_correction | 1 | 0 | 2 | 0 |" in md
    assert FOOTNOTE in md
    assert str(a) in md and str(b) in md


def test_pair_with_unknown_run_raises():
    with pytest.raises(ValueError, match="--pair"):
        render_markdown([(Path("a.jsonl"), "a", RUN_A)], [("a", "zzz")])


def test_file_mixing_run_ids_is_rejected(tmp_path):
    mixed = _write(tmp_path / "mixed.jsonl", [RUN_A[0], RUN_B[0]])
    with pytest.raises(ValueError, match="exactly one run_id"):
        main([str(mixed)])


def test_main_writes_markdown_out(tmp_path, capsys):
    a = _write(tmp_path / "a-blind.jsonl", RUN_A)
    b = _write(tmp_path / "b-blind.jsonl", RUN_B)
    out = tmp_path / "report.md"
    assert main([str(a), str(b), "--pair", "a", "b", "--markdown-out", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == capsys.readouterr().out.rstrip("\n") + "\n"
    assert "### a → b" in out.read_text(encoding="utf-8")


def test_main_refuses_original_and_blind_copy_of_same_run(tmp_path):
    a = _write(tmp_path / "a.jsonl", RUN_A)
    a_blind = _write(tmp_path / "a-blind.jsonl", RUN_A)
    with pytest.raises(SystemExit, match="appears in both"):
        main([str(a), str(a_blind)])
