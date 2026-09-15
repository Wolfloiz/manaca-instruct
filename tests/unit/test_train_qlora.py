import json

import pytest
import yaml

from src.train_qlora import _format_prompt, load_config, load_training_examples, train

VALID_CONFIG = {
    "base_model": "menezesbruno/manaca-1b-base",
    "quantization": {"load_in_4bit": True, "bnb_4bit_quant_type": "nf4", "bnb_4bit_compute_dtype": "bfloat16"},
    "lora": {"r": 16, "alpha": 32, "dropout": 0.05, "target_modules": ["q_proj"]},
    "training": {
        "batch_size": 2,
        "gradient_accumulation_steps": 16,
        "learning_rate": 1.5e-4,
        "num_epochs": 2,
        "max_seq_length": 2048,
        "optimizer": "paged_adamw_8bit",
    },
    "output": {"adapter_dir": "adapters/qlora-v1"},
}


def _write_yaml(tmp_path, data):
    path = tmp_path / "train.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_load_config_accepts_valid_config(tmp_path):
    path = _write_yaml(tmp_path, VALID_CONFIG)
    config = load_config(path)
    assert config["lora"]["r"] == 16


def test_load_config_rejects_missing_section(tmp_path):
    bad = dict(VALID_CONFIG)
    del bad["lora"]
    path = _write_yaml(tmp_path, bad)
    with pytest.raises(ValueError, match="missing required section"):
        load_config(path)


def test_load_config_rejects_lora_rank_outside_research_range(tmp_path):
    bad = json.loads(json.dumps(VALID_CONFIG))  # deep copy
    bad["lora"]["r"] = 64  # research.md §2's validated range is 8-16
    path = _write_yaml(tmp_path, bad)
    with pytest.raises(ValueError, match="lora.r"):
        load_config(path)


def test_load_config_rejects_learning_rate_outside_research_range(tmp_path):
    bad = json.loads(json.dumps(VALID_CONFIG))
    bad["training"]["learning_rate"] = 0.01  # research.md §2's validated range is 1e-4-2e-4
    path = _write_yaml(tmp_path, bad)
    with pytest.raises(ValueError, match="learning_rate"):
        load_config(path)


def test_load_training_examples_validates_schema(tmp_path):
    dataset_path = tmp_path / "train.jsonl"
    dataset_path.write_text(
        json.dumps(
            {
                "id": "x-1",
                "source": "alpaca-pt-br",
                "task_category": "grammar_correction",
                "instruction": "Corrija.",
                "input": "ele viajo",
                "output": "Ele viajou.",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    examples = load_training_examples(dataset_path)
    assert len(examples) == 1


def test_format_prompt_matches_manaca_template():
    example = {"instruction": "Corrija o texto.", "input": "ele viajo", "output": "Ele viajou."}
    formatted = _format_prompt(example)
    assert "### Instrução:\nCorrija o texto." in formatted
    assert "### Entrada:\nele viajo" in formatted
    assert "### Resposta:\nEle viajou." in formatted


def test_format_prompt_omits_empty_input_section():
    example = {"instruction": "Explique X.", "input": "", "output": "resposta"}
    formatted = _format_prompt(example)
    assert "### Entrada:" not in formatted


def test_train_orchestrates_build_and_run_with_mocked_ml_stack(tmp_path, monkeypatch):
    config_path = _write_yaml(tmp_path, VALID_CONFIG)
    dataset_path = tmp_path / "train.jsonl"
    dataset_path.write_text(
        json.dumps(
            {
                "id": "x-1",
                "source": "alpaca-pt-br",
                "task_category": "grammar_correction",
                "instruction": "Corrija.",
                "input": "ele viajo",
                "output": "Ele viajou.",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    built = object()
    monkeypatch.setattr("src.train_qlora._build_model", lambda config: (built, None))
    saved_examples = []
    saved_dir = None

    def fake_run_training(model, tokenizer, examples, config, output_dir):
        assert model is built
        saved_examples.extend(examples)
        nonlocal saved_dir
        saved_dir = output_dir

    monkeypatch.setattr("src.train_qlora._run_training", fake_run_training)

    output_dir = train(config_path, dataset_path, "qlora-test")

    assert output_dir.name == "qlora-test"
    assert str(output_dir) == "adapters/qlora-test"
    assert saved_dir == output_dir
    assert [ex["id"] for ex in saved_examples] == ["x-1"]
