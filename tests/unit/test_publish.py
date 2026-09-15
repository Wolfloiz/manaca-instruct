import pytest

from src.publish import ModelCardError, publish, validate_model_card

VALID_CARD = """---
license: cc-by-nc-4.0
language: [pt]
base_model: menezesbruno/manaca-1b-base
tags: [instruction-tuning, portuguese, gguf, qlora, personal-project]
---

# Manaca-Instruct-PT

## What this is

A personal/learning project fine-tuning menezesbruno/manaca-1b-base.

## How to use it

### transformers

```python
from transformers import AutoModelForCausalLM
```

### llama.cpp

```bash
llama-cli -m manaca-instruct-pt-Q4_K_M.gguf -p "..."
```

## Evaluation results

| Category | Base | Instruct | Official |
|---|---|---|---|
| grammar_correction | 10% | 80% | 60% |
"""


def test_valid_model_card_passes():
    validate_model_card(VALID_CARD)  # no raise


def test_missing_front_matter_rejected():
    with pytest.raises(ModelCardError, match="front matter"):
        validate_model_card("# just a heading, no front matter\n")


def test_missing_required_field_rejected():
    bad = VALID_CARD.replace("base_model: menezesbruno/manaca-1b-base\n", "")
    with pytest.raises(ModelCardError, match="missing required field"):
        validate_model_card(bad)


def test_wrong_license_rejected():
    bad = VALID_CARD.replace("license: cc-by-nc-4.0", "license: mit")
    with pytest.raises(ModelCardError, match="cc-by-nc-4.0"):
        validate_model_card(bad)


def test_missing_llama_cpp_snippet_rejected():
    bad = VALID_CARD.replace("### llama.cpp\n\n```bash\nllama-cli -m manaca-instruct-pt-Q4_K_M.gguf -p \"...\"\n```\n\n", "")
    with pytest.raises(ModelCardError, match="missing required content"):
        validate_model_card(bad)


def test_missing_evaluation_section_rejected():
    bad = VALID_CARD.split("## Evaluation results")[0]
    with pytest.raises(ModelCardError, match="missing required content"):
        validate_model_card(bad)


def test_publish_refuses_before_touching_the_network(tmp_path):
    model_card_path = tmp_path / "MODEL_CARD.md"
    model_card_path.write_text("# no front matter", encoding="utf-8")
    with pytest.raises(ModelCardError):
        publish(tmp_path / "model", tmp_path / "gguf", model_card_path, "someuser/manaca-instruct-pt")


def test_publish_returns_repo_url_after_gate_passes(tmp_path, monkeypatch):
    model_card_path = tmp_path / "MODEL_CARD.md"
    model_card_path.write_text(VALID_CARD, encoding="utf-8")
    monkeypatch.setattr("src.publish._push_to_hub", lambda m, g, t, r: f"https://huggingface.co/{r}")
    url = publish(tmp_path / "model", tmp_path / "gguf", model_card_path, "someuser/manaca-instruct-pt")
    assert url == "https://huggingface.co/someuser/manaca-instruct-pt"


def test_push_to_hub_uploads_model_gguf_and_card(tmp_path, monkeypatch):
    import src.publish as publish_mod

    model_dir = tmp_path / "model"
    model_dir.mkdir()
    (model_dir / "model.safetensors").write_text("weights")
    gguf_dir = tmp_path / "gguf"
    gguf_dir.mkdir()
    (gguf_dir / "manaca-instruct-pt-Q4_K_M.gguf").write_text("gguf")

    class FakeApi:
        def __init__(self):
            self.calls = []

        def upload_folder(self, **kwargs):
            self.calls.append(("folder", kwargs))

        def upload_file(self, **kwargs):
            self.calls.append(("file", kwargs))

    fake_api = FakeApi()
    monkeypatch.setattr(publish_mod, "HfApi", lambda: fake_api)
    monkeypatch.setattr(publish_mod, "create_repo", lambda **kw: None)
    monkeypatch.setenv("HUGGING_FACE_HUB_TOKEN", "hf_fake")

    url = publish_mod._push_to_hub(model_dir, gguf_dir, VALID_CARD, "someuser/manaca-instruct-pt")

    assert url == "https://huggingface.co/someuser/manaca-instruct-pt"
    folder_kwargs = [c[1] for c in fake_api.calls if c[0] == "folder"]
    file_kwargs = [c[1] for c in fake_api.calls if c[0] == "file"]
    assert any(kw["repo_id"] == "someuser/manaca-instruct-pt" for kw in folder_kwargs)
    assert any(kw.get("path_in_repo") == "gguf" for kw in folder_kwargs)
    assert file_kwargs[0]["path_in_repo"] == "README.md"


def test_push_to_hub_requires_a_token(tmp_path, monkeypatch):
    import src.publish as publish_mod

    monkeypatch.delenv("HUGGING_FACE_HUB_TOKEN", raising=False)
    monkeypatch.setattr(publish_mod.Path.home, lambda: tmp_path)  # no cached HF token either
    with pytest.raises(RuntimeError, match="token"):
        publish_mod._push_to_hub(tmp_path / "model", tmp_path / "gguf", VALID_CARD, "someuser/manaca-instruct-pt")
