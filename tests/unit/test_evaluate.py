import json

import pytest

from src.evaluate import _format_inference_prompt, _read_prompts, run_evaluation, write_results_jsonl


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


def test_run_evaluation_manaca_instruct_pt_requires_adapter(tmp_path):
    # _load_model raises before any network/GPU work if --adapter is missing for this model
    with pytest.raises(ValueError, match="requires --adapter"):
        run_evaluation("manaca-instruct-pt", None, [], "run1")


def test_format_inference_prompt_matches_training_template():
    formatted = _format_inference_prompt("Corrija gramaticalmente o texto: ele viajo ontem")
    assert formatted == "### Instrução:\nCorrija gramaticalmente o texto: ele viajo ontem\n\n### Resposta:\n"


# NOTE: _load_model/_generate now do real transformers/peft loading and GPU
# inference (see evaluate.py's docstring) — exercising them for real belongs
# to specs/001-manaca-instruct-tuning/quickstart.md's manual validation path,
# not this fast unit suite, since it needs real model weights, a GPU, and
# real wall-clock time to download/run.


# --- feature 002 (T016): --prompt-format, --inference-config, evaluation manifest
from src import evaluate as evaluate_module
from src import run_manifest
from src.evaluate import write_evaluation_manifest

GRUPO_A_SPLIT = {
    "id": "grupo_a-grammar-001", "group": "grupo_a", "task_category": "grammar_correction",
    "prompt": "Corrija gramaticalmente o texto: os menino foi", "expected": "Os meninos foram",
    "grading_method": "manual_review", "instruction": "Corrija gramaticalmente o texto", "input": "os menino foi",
}
GRUPO_A_NO_SPLIT = {k: v for k, v in GRUPO_A_SPLIT.items() if k not in ("instruction", "input")}
GRUPO_B = {
    "id": "grupo_b-001", "group": "grupo_b", "task_category": None,
    "prompt": "Qual é a capital do Brasil?", "expected": None, "grading_method": "manual_review",
}


def _prompt_file(tmp_path, rows):
    path = tmp_path / "prompts.jsonl"
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return path


def _mock_stack(monkeypatch, seen_prompts):
    monkeypatch.setattr(evaluate_module, "_load_model", lambda *a, **k: (object(), object(), {}))

    def fake_generate(model, tokenizer, prompt, cfg):
        seen_prompts.append(prompt)
        return "resposta", 1.0

    monkeypatch.setattr(evaluate_module, "_generate", fake_generate)


def test_split_format_renders_entrada_block_and_grupo_b_falls_back(tmp_path, monkeypatch):
    seen = []
    _mock_stack(monkeypatch, seen)
    results = run_evaluation("manaca-1b-base", None, [_prompt_file(tmp_path, [GRUPO_A_SPLIT, GRUPO_B])], "r-split", "split")
    assert len(results) == 2
    assert seen[0] == "### Instrução:\nCorrija gramaticalmente o texto\n\n### Entrada:\nos menino foi\n\n### Resposta:\n"
    assert seen[1] == "### Instrução:\nQual é a capital do Brasil?\n\n### Resposta:\n"
    assert results[0]["prompt"] == GRUPO_A_SPLIT["prompt"]  # the recorded prompt stays the frozen text


def test_combined_format_never_renders_entrada_block(tmp_path, monkeypatch):
    seen = []
    _mock_stack(monkeypatch, seen)
    run_evaluation("manaca-1b-base", None, [_prompt_file(tmp_path, [GRUPO_A_SPLIT])], "r")
    assert seen == ["### Instrução:\nCorrija gramaticalmente o texto: os menino foi\n\n### Resposta:\n"]


def test_split_format_fails_fast_on_grupo_a_row_without_fields(tmp_path, monkeypatch):
    _mock_stack(monkeypatch, [])
    with pytest.raises(ValueError, match="requires instruction/input"):
        run_evaluation("manaca-1b-base", None, [_prompt_file(tmp_path, [GRUPO_A_NO_SPLIT])], "r-split", "split")


def test_unknown_prompt_format_rejected(tmp_path, monkeypatch):
    _mock_stack(monkeypatch, [])
    with pytest.raises(ValueError, match="prompt-format"):
        run_evaluation("manaca-1b-base", None, [], "r", "sideways")


def test_evaluation_manifest_written_with_evaluation_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(run_manifest, "_git_info", lambda: ("c" * 40, False))
    monkeypatch.setattr(run_manifest, "_base_model_revision", lambda repo_id: ("rev", "hub"))
    prompts = _prompt_file(tmp_path, [GRUPO_A_SPLIT, GRUPO_B])
    cfg = tmp_path / "inference.yaml"
    cfg.write_text("max_new_tokens: 8\nrepetition_penalty: 1.3\n", encoding="utf-8")
    adapter = tmp_path / "adapters" / "qlora-v3b" / "checkpoint-124"
    adapter.mkdir(parents=True)
    (adapter.parent / "run_manifest.json").write_text("{}", encoding="utf-8")
    out = tmp_path / "eval" / "results" / "qlora-v3b-best-split.jsonl"
    out.parent.mkdir(parents=True)
    out.write_text("{}\n{}\n", encoding="utf-8")

    manifest_path = write_evaluation_manifest(
        out, model_key="manaca-instruct-pt", adapter_path=str(adapter), prompt_files=[prompts],
        run_id="qlora-v3b-best-split", prompt_format="split", inference_config_path=cfg, rows_written=2,
    )

    assert manifest_path == out.with_suffix(".manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["kind"] == "evaluation" and manifest["run_id"] == "qlora-v3b-best-split"
    assert manifest["model"] == "manaca-instruct-pt"
    assert manifest["base_model"]["repo_id"] == "menezesbruno/manaca-1b-base"
    assert manifest["checkpoint"] == str(adapter)
    assert manifest["adapter_manifest"] == str(adapter.parent / "run_manifest.json")
    assert manifest["prompt_format"] == "split"
    assert manifest["config"] == {"max_new_tokens": 8, "repetition_penalty": 1.3}
    assert manifest["datasets"][0]["rows"] == 2
    assert manifest["rows_written"] == 2 == len(out.read_text().splitlines())
    assert manifest["results_path"] == str(out)


def test_official_model_manifest_has_no_adapter(tmp_path, monkeypatch):
    monkeypatch.setattr(run_manifest, "_git_info", lambda: ("c" * 40, False))
    monkeypatch.setattr(run_manifest, "_base_model_revision", lambda repo_id: ("rev", "hub"))
    out = tmp_path / "official-instruct-split.jsonl"
    out.write_text("", encoding="utf-8")
    manifest_path = write_evaluation_manifest(
        out, model_key="manaca-1b-instruct", adapter_path=None, prompt_files=[], run_id="official-instruct-split",
        prompt_format="split", inference_config_path=tmp_path / "missing.yaml", rows_written=0,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["base_model"]["repo_id"] == "menezesbruno/manaca-1b-instruct"
    assert manifest["adapter_path"] is None and manifest["checkpoint"] is None and manifest["adapter_manifest"] is None
