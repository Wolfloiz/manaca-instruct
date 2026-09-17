"""Feature 002 FR-022: the recorded result files of feature 001 and the frozen evaluation
prompt texts must never change. Every new result goes to a new file; every blind grade goes
to a `-blind` sibling. If this test fails, a frozen artifact was edited — revert it.

Hashes recorded 2026-09-15 at the start of feature 002 (tasks.md T005/T018).
"""

import hashlib
import json
from pathlib import Path

import pytest

FROZEN_RESULT_FILES = {
    "eval/results/baseline.jsonl": "8e07ebfcf120bfccbabe96d55abede25f796c36ae9c11e00d7d5d96edee58304",
    "eval/results/qlora-v1.jsonl": "2bf1c50437ed5bff9a75a7154cc71daaf130ab35bc1ab434e716e73cd2750ac4",
    "eval/results/qlora-v2.jsonl": "286abe87045f69c1d3302fca9985bf34ee1f9c945e3386d1e6e04af5af8c620d",
    "eval/results/official-instruct.jsonl": "aec234196ea5c7c16aab658dd2a28c77a4f3a963f6d55d880b7ff6fb214df9e3",
}

# SHA256 of the "\n"-joined `prompt` strings, in file order — the split annotation (002 T015)
# may add fields to grupo_a rows, but the prompt text itself is frozen.
FROZEN_PROMPT_TEXTS = {
    "data/eval/grupo_a_prompts.jsonl": (80, "d8ab99f037e6ae828dba6a6fcb8fe63fed03a9a1c8d9fd57c895317320475f61"),
    "data/eval/grupo_b_prompts.jsonl": (24, "460889aba9bc6e4a8995944fbea1fc0efb1270fe6fc66ee32a6e90ffffb7b455"),
}


@pytest.mark.parametrize("path,expected", sorted(FROZEN_RESULT_FILES.items()))
def test_feature_001_result_file_is_unchanged(path, expected):
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected, f"{path} was modified (FR-022)"


@pytest.mark.parametrize("path,expected", sorted(FROZEN_PROMPT_TEXTS.items()))
def test_evaluation_prompt_texts_are_unchanged(path, expected):
    count, digest = expected
    with Path(path).open(encoding="utf-8") as f:
        prompts = [json.loads(line)["prompt"] for line in f if line.strip()]
    assert len(prompts) == count
    assert hashlib.sha256("\n".join(prompts).encode("utf-8")).hexdigest() == digest, f"{path}: a prompt text changed (FR-022)"
