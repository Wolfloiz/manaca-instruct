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


def test_publish_reaches_the_documented_push_seam_once_card_is_valid(tmp_path):
    model_card_path = tmp_path / "MODEL_CARD.md"
    model_card_path.write_text(VALID_CARD, encoding="utf-8")
    with pytest.raises(NotImplementedError):
        publish(tmp_path / "model", tmp_path / "gguf", model_card_path, "someuser/manaca-instruct-pt")
