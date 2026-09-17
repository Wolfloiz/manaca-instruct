import json
import sys
from types import ModuleType

import pytest
import yaml

from src.train_qlora import (
    _assert_no_overlap,
    _format_prompt,
    _oversample,
    _run_training,
    _training_summary,
    load_config,
    load_training_examples,
    train,
)

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
    assert config["training"]["completion_only_loss"] is False


def test_load_config_defaults_oversample_and_validates_it(tmp_path):
    config = load_config(_write_yaml(tmp_path, VALID_CONFIG))
    assert config["training"]["oversample"] == {}
    bad = json.loads(json.dumps(VALID_CONFIG))
    bad["training"]["oversample"] = {"grammar": 2}  # not a task_category
    with pytest.raises(ValueError, match="unknown task_category"):
        load_config(_write_yaml(tmp_path, bad))
    bad["training"]["oversample"] = {"grammar_correction": 1.5}
    with pytest.raises(ValueError, match="integer >= 1"):
        load_config(_write_yaml(tmp_path, bad))


def test_oversample_repeats_only_the_named_category_in_order():
    rows = [
        {"id": "g1", "task_category": "grammar_correction"},
        {"id": "c1", "task_category": "classification"},
        {"id": "g2", "task_category": "grammar_correction"},
    ]
    assert [r["id"] for r in _oversample(rows, {"grammar_correction": 2})] == ["g1", "g1", "c1", "g2", "g2"]
    assert _oversample(rows, {}) == rows


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
    monkeypatch.chdir(tmp_path)
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
    validation_path = tmp_path / "validation.jsonl"
    validation_path.write_text(
        json.dumps(
            {
                "id": "x-2", "source": "alpaca-pt-br", "task_category": "grammar_correction",
                "instruction": "Corrija outra frase.", "input": "ela viajo", "output": "Ela viajou.",
            }
        ) + "\n", encoding="utf-8",
    )

    built = object()
    monkeypatch.setattr("src.train_qlora._build_model", lambda config: (built, None))
    saved_examples = []
    saved_dir = None

    def fake_run_training(model, tokenizer, examples, validation_examples, config, output_dir):
        assert model is built
        saved_examples.extend(examples)
        nonlocal saved_dir
        saved_dir = output_dir
        assert [ex["id"] for ex in validation_examples] == ["x-2"]
        return {"eval_loss_by_epoch": {"1": 1.0}, "train_loss_by_epoch": {}, "best_epoch": 1,
                "checkpoints": [], "adapter_epoch": 2}

    monkeypatch.setattr("src.train_qlora._run_training", fake_run_training)

    monkeypatch.setattr(
        "src.train_qlora.build_manifest",
        lambda *args, **kwargs: {"status": kwargs.get("status", "ok"), "run_id": args[1], "git_dirty": False},
    )
    output_dir = train(config_path, dataset_path, validation_path, "qlora-test")

    assert output_dir.name == "qlora-test"
    assert str(output_dir) == "adapters/qlora-test"
    assert saved_dir == output_dir
    assert [ex["id"] for ex in saved_examples] == ["x-1"]


def test_overlap_check_normalizes_instruction_and_input():
    train_rows = [{"instruction": "Corrija.", "input": "Texto  aqui"}]
    validation_rows = [{"instruction": "corrija", "input": "texto aqui."}]
    with pytest.raises(ValueError, match="share normalized"):
        _assert_no_overlap(train_rows, validation_rows)


@pytest.mark.parametrize("completion_only_loss", [False, True])
def test_run_training_uses_expected_dataset_shape_and_eval_config(tmp_path, monkeypatch, completion_only_loss):
    captured = {}

    class FakeDataset:
        @classmethod
        def from_list(cls, rows):
            return rows

    class FakeSFTConfig:
        def __init__(self, **kwargs):
            captured["config"] = kwargs

    class FakeTrainer:
        def __init__(self, **kwargs):
            captured["trainer"] = kwargs

        def train(self):
            # Like transformers' Trainer: state lives only inside checkpoint-<step>/
            checkpoint = tmp_path / "adapter" / "checkpoint-7"
            checkpoint.mkdir(parents=True, exist_ok=True)
            (checkpoint / "trainer_state.json").write_text(
                json.dumps({"epoch": 1.0, "log_history": [{"epoch": 0.7, "loss": 2.0}, {"epoch": 1.0, "eval_loss": 1.5}]}),
                encoding="utf-8",
            )

    datasets = ModuleType("datasets")
    datasets.Dataset = FakeDataset
    trl = ModuleType("trl")
    trl.SFTConfig = FakeSFTConfig
    trl.SFTTrainer = FakeTrainer
    monkeypatch.setitem(sys.modules, "datasets", datasets)
    monkeypatch.setitem(sys.modules, "trl", trl)

    class Saveable:
        def save_pretrained(self, path):
            pass

    config = json.loads(json.dumps(VALID_CONFIG))
    config["training"]["completion_only_loss"] = completion_only_loss
    config["training"]["oversample"] = {"grammar_correction": 3}
    rows = [{"instruction": "Instrua", "input": "contexto", "output": "resposta", "task_category": "grammar_correction"}]
    summary = _run_training(Saveable(), Saveable(), rows, rows, config, tmp_path / "adapter")

    assert len(captured["trainer"]["train_dataset"]) == 3  # oversampled
    assert len(captured["trainer"]["eval_dataset"]) == 1  # validation never repeated

    assert captured["config"]["eval_strategy"] == "epoch"
    assert captured["config"]["per_device_eval_batch_size"] == 2
    assert captured["config"]["save_strategy"] == "epoch"
    # contract: every epoch checkpoint is kept and the adapter is always the last epoch
    assert "save_total_limit" not in captured["config"]
    assert "load_best_model_at_end" not in captured["config"]
    assert captured["trainer"]["eval_dataset"]
    train_row = captured["trainer"]["train_dataset"][0]
    if completion_only_loss:
        assert train_row == {"prompt": "### Instrução:\nInstrua\n\n### Entrada:\ncontexto\n\n### Resposta:\n", "completion": "resposta"}
        assert "dataset_text_field" not in captured["config"]
    else:
        assert "text" in train_row
        assert captured["config"]["dataset_text_field"] == "text"
    assert summary["eval_loss_by_epoch"] == {"1": 1.5}
    assert summary["train_loss_by_epoch"] == {"1": 2.0}
    assert summary["checkpoints"] == [{"epoch": 1, "path": str(tmp_path / "adapter" / "checkpoint-7")}]


def _write_checkpoint(output_dir, step, epoch, log_history):
    checkpoint = output_dir / f"checkpoint-{step}"
    checkpoint.mkdir(parents=True)
    (checkpoint / "trainer_state.json").write_text(
        json.dumps({"epoch": epoch, "global_step": step, "log_history": log_history}), encoding="utf-8"
    )
    return checkpoint


def test_training_summary_orders_checkpoints_numerically_and_buckets_fractional_epochs(tmp_path):
    # A 200-row smoke run (7 optimizer steps/epoch): lexicographic order would be 14, 21, 7.
    # log_history mirrors the real shape: `loss` every logging_steps with fractional epochs,
    # `eval_loss` exactly on the epoch boundary; each checkpoint holds the history so far.
    history = [
        {"epoch": 0.43, "loss": 4.0, "step": 3},
        {"epoch": 0.86, "loss": 3.0, "step": 6},
        {"epoch": 1.0, "eval_loss": 2.5, "step": 7},
        {"epoch": 1.29, "loss": 2.9, "step": 9},
        {"epoch": 1.71, "loss": 2.2, "step": 12},
        {"epoch": 2.0, "eval_loss": 1.9, "step": 14},
        {"epoch": 2.14, "loss": 2.1, "step": 15},
        {"epoch": 2.57, "loss": 2.0, "step": 18},
        {"epoch": 3.0, "eval_loss": 2.1, "step": 21},
        {"epoch": 3.0, "train_loss": 2.6, "train_runtime": 10.0, "step": 21},
    ]
    _write_checkpoint(tmp_path, 7, 1.0, history[:3])
    _write_checkpoint(tmp_path, 14, 2.0, history[:6])
    _write_checkpoint(tmp_path, 21, 3.0, history)

    summary = _training_summary(tmp_path, 3)

    assert summary["eval_loss_by_epoch"] == {"1": 2.5, "2": 1.9, "3": 2.1}
    # last loss logged *within* each epoch; no spurious "0" bucket
    assert summary["train_loss_by_epoch"] == {"1": 3.0, "2": 2.2, "3": 2.0}
    assert summary["best_epoch"] == 2
    assert summary["adapter_epoch"] == 3
    assert [c["epoch"] for c in summary["checkpoints"]] == [1, 2, 3]
    assert [c["path"] for c in summary["checkpoints"]] == [str(tmp_path / f"checkpoint-{n}") for n in (7, 14, 21)]


def test_train_refuses_run_id_with_previous_checkpoints(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = _write_yaml(tmp_path, VALID_CONFIG)
    output_dir = tmp_path / "adapters" / "reused"
    _write_checkpoint(output_dir, 124, 1.0, [])
    previous_manifest = output_dir / "run_manifest.json"
    previous_manifest.write_text('{"status": "ok"}', encoding="utf-8")
    monkeypatch.setattr("src.train_qlora._build_model", lambda config: pytest.fail("must not load the model"))

    with pytest.raises(FileExistsError, match="reused"):
        train(config_path, tmp_path / "train.jsonl", tmp_path / "validation.jsonl", "reused")
    # the earlier run's provenance is left untouched
    assert previous_manifest.read_text(encoding="utf-8") == '{"status": "ok"}'
    assert not (tmp_path / "runs" / "reused.manifest.json").exists()


def test_training_failure_writes_both_failed_manifests(tmp_path, monkeypatch):
    config_path = _write_yaml(tmp_path, VALID_CONFIG)
    row = {"id": "x", "source": "seed", "task_category": "classification", "instruction": "Classifique", "input": "a", "output": "a"}
    dataset_path = tmp_path / "train.jsonl"
    validation_path = tmp_path / "validation.jsonl"
    dataset_path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    row["id"] = "y"
    row["instruction"] = "Classifique outra"
    validation_path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("src.train_qlora._build_model", lambda config: (object(), object()))
    monkeypatch.setattr("src.train_qlora._run_training", lambda *args: (_ for _ in ()).throw(RuntimeError("trainer failed")))
    monkeypatch.setattr("src.train_qlora.build_manifest", lambda *args, **kwargs: {"status": kwargs.get("status", "ok"), "error": kwargs.get("error"), "git_dirty": False})

    with pytest.raises(RuntimeError, match="trainer failed"):
        train(config_path, dataset_path, validation_path, "failed")
    primary = tmp_path / "adapters" / "failed" / "run_manifest.json"
    mirror = tmp_path / "runs" / "failed.manifest.json"
    assert json.loads(primary.read_text())["status"] == "failed"
    assert primary.read_bytes() == mirror.read_bytes()


TRAINING_ONLY_FIELDS = {
    "validation_path", "completion_only_loss", "eval_loss_by_epoch", "train_loss_by_epoch",
    "best_epoch", "checkpoints", "adapter_path", "adapter_epoch",
}


def _capture_manifest_kwargs(monkeypatch, captured):
    def fake_build_manifest(*args, **kwargs):
        captured.append(kwargs)
        # only the JSON-serialisable training-only fields; `datasets`/`config` carry Path objects here
        extra = {k: v for k, v in kwargs.items() if k in TRAINING_ONLY_FIELDS}
        return {"status": kwargs.get("status", "ok"), "error": kwargs.get("error"), "git_dirty": False, **extra}

    monkeypatch.setattr("src.train_qlora.build_manifest", fake_build_manifest)


def test_keyboard_interrupt_during_training_still_writes_failed_manifest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = _write_yaml(tmp_path, VALID_CONFIG)
    row = {"id": "x", "source": "seed", "task_category": "classification", "instruction": "Classifique", "input": "a", "output": "a"}
    (tmp_path / "train.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    (tmp_path / "validation.jsonl").write_text(json.dumps({**row, "id": "y", "instruction": "Outra"}) + "\n", encoding="utf-8")
    monkeypatch.setattr("src.train_qlora._build_model", lambda config: (object(), object()))
    monkeypatch.setattr("src.train_qlora._run_training", lambda *args: (_ for _ in ()).throw(KeyboardInterrupt()))
    _capture_manifest_kwargs(monkeypatch, [])

    with pytest.raises(KeyboardInterrupt):
        train(config_path, tmp_path / "train.jsonl", tmp_path / "validation.jsonl", "interrupted")
    manifest = json.loads((tmp_path / "runs" / "interrupted.manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert TRAINING_ONLY_FIELDS <= manifest.keys()


def test_failed_manifest_records_checkpoints_already_on_disk(tmp_path, monkeypatch):
    """Ctrl-C in epoch 3: the two finished epochs' checkpoints and eval losses must be in the failed manifest."""
    monkeypatch.chdir(tmp_path)
    config_path = _write_yaml(tmp_path, VALID_CONFIG)
    row = {"id": "x", "source": "seed", "task_category": "classification", "instruction": "Classifique", "input": "a", "output": "a"}
    (tmp_path / "train.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    (tmp_path / "validation.jsonl").write_text(json.dumps({**row, "id": "y", "instruction": "Outra"}) + "\n", encoding="utf-8")
    monkeypatch.setattr("src.train_qlora._build_model", lambda config: (object(), object()))

    def interrupted_training(model, tokenizer, examples, validation_examples, config, output_dir):
        _write_checkpoint(output_dir, 7, 1.0, [{"epoch": 1.0, "eval_loss": 2.5}])
        _write_checkpoint(output_dir, 14, 2.0, [{"epoch": 1.0, "eval_loss": 2.5}, {"epoch": 2.0, "eval_loss": 1.9}])
        raise KeyboardInterrupt()

    monkeypatch.setattr("src.train_qlora._run_training", interrupted_training)
    _capture_manifest_kwargs(monkeypatch, [])

    with pytest.raises(KeyboardInterrupt):
        train(config_path, tmp_path / "train.jsonl", tmp_path / "validation.jsonl", "interrupted")
    manifest = json.loads((tmp_path / "runs" / "interrupted.manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert manifest["eval_loss_by_epoch"] == {"1": 2.5, "2": 1.9}
    assert [c["epoch"] for c in manifest["checkpoints"]] == [1, 2]
    assert manifest["best_epoch"] == 2 and manifest["adapter_epoch"] is None


def test_early_failure_manifest_has_same_training_fields_as_late_failure(tmp_path, monkeypatch):
    """A failure before build_manifest (here: train/validation overlap) must not produce a thinner manifest."""
    monkeypatch.chdir(tmp_path)
    config_path = _write_yaml(tmp_path, VALID_CONFIG)
    row = {"id": "x", "source": "seed", "task_category": "classification", "instruction": "Classifique", "input": "a", "output": "a"}
    (tmp_path / "train.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    (tmp_path / "validation.jsonl").write_text(json.dumps({**row, "id": "y"}) + "\n", encoding="utf-8")
    monkeypatch.setattr("src.train_qlora._build_model", lambda config: pytest.fail("must not load the model"))
    captured = []
    _capture_manifest_kwargs(monkeypatch, captured)

    with pytest.raises(ValueError, match="share normalized"):
        train(config_path, tmp_path / "train.jsonl", tmp_path / "validation.jsonl", "early")
    assert len(captured) == 1
    assert captured[0]["status"] == "failed"
    assert TRAINING_ONLY_FIELDS <= captured[0].keys()
    assert captured[0]["adapter_path"] == "adapters/early"
    manifest = json.loads((tmp_path / "adapters" / "early" / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert (tmp_path / "runs" / "early.manifest.json").read_bytes() == (tmp_path / "adapters" / "early" / "run_manifest.json").read_bytes()
