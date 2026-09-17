"""Validation for the JSONL record shapes defined in specs/001-manaca-instruct-tuning/contracts/.

Shared by src/prepare_dataset.py, src/train_qlora.py, and src/evaluate.py so that
three independently-reviewed PRs (Agent 1, Agent 2, Agent 3) produce and consume
files that actually interoperate, per contracts/dataset-schema.md and
contracts/evaluation-results-schema.md.
"""

from __future__ import annotations

TASK_CATEGORIES = {
    "grammar_correction",
    "rewriting",
    "summarization",
    "simplification",
    "classification",
}

RULE_BASED_CATEGORIES = {"classification"}
# grammar_correction moved to manual_review (2026-09-15): edit-distance-to-a-single-reference
# couldn't distinguish a genuinely good correction (different valid phrasing) from an off-topic
# failure -- both landed at low similarity. Reading qlora-v1's real outputs found ~31% genuine
# grammar fixes that the scorer reported as 0%. See research.md §3's update.

GRADING_METHODS = {"rule_based", "manual_review"}

EVAL_GROUPS = {"grupo_a", "grupo_b", "dev"}
# "dev" (added for feature 002): data/dev/dev_prompts.jsonl, sampled from validation data for
# tuning decisions so the frozen grupo_a/grupo_b set is never reused for them (002 FR-005).

CATEGORY_SCOPED_GROUPS = {"grupo_a", "dev"}

EVAL_MODELS = {"manaca-1b-base", "manaca-instruct-pt", "manaca-1b-instruct"}


class SchemaError(ValueError):
    """Raised when a JSONL record violates its contract."""


def _require_keys(record: dict, required: set[str], record_kind: str) -> None:
    missing = required - record.keys()
    if missing:
        raise SchemaError(f"{record_kind} missing required key(s): {sorted(missing)}")


def validate_instruction_example(record: dict) -> None:
    """contracts/dataset-schema.md — train.jsonl / validation.jsonl rows."""
    _require_keys(
        record,
        {"id", "source", "task_category", "instruction", "input", "output"},
        "InstructionExample",
    )
    if record["task_category"] not in TASK_CATEGORIES:
        raise SchemaError(
            f"InstructionExample {record.get('id')!r}: task_category "
            f"{record['task_category']!r} not in {sorted(TASK_CATEGORIES)}"
        )
    if not record["id"]:
        raise SchemaError("InstructionExample: id must be non-empty")


def validate_evaluation_prompt(record: dict) -> None:
    """contracts/dataset-schema.md — grupo_a/grupo_b prompt rows."""
    _require_keys(
        record,
        {"id", "group", "task_category", "prompt", "expected", "grading_method"},
        "EvaluationPrompt",
    )
    if record["group"] not in EVAL_GROUPS:
        raise SchemaError(f"EvaluationPrompt {record.get('id')!r}: group must be one of {sorted(EVAL_GROUPS)}")
    if record["grading_method"] not in GRADING_METHODS:
        raise SchemaError(
            f"EvaluationPrompt {record.get('id')!r}: grading_method must be one of {sorted(GRADING_METHODS)}"
        )
    if record["group"] == "grupo_b" and record["task_category"] is not None:
        raise SchemaError(f"EvaluationPrompt {record.get('id')!r}: grupo_b rows must have task_category: null")
    if record["group"] in CATEGORY_SCOPED_GROUPS and record["task_category"] not in TASK_CATEGORIES:
        raise SchemaError(
            f"EvaluationPrompt {record.get('id')!r}: {record['group']} task_category must be one of "
            f"{sorted(TASK_CATEGORIES)}"
        )
    if record["grading_method"] == "rule_based" and not record["expected"]:
        raise SchemaError(
            f"EvaluationPrompt {record.get('id')!r}: rule_based prompts require a non-null expected value"
        )
    _validate_split_fields(record)


def _validate_split_fields(record: dict) -> None:
    """Optional `instruction`/`input` annotation of a frozen `prompt` (002 contracts/evaluation-presentation.md).

    The split exists so the evaluator can present a prompt in the training structure
    (`### Instrução` / `### Entrada`) without changing the frozen text, so the two fields
    must reconstruct `prompt` exactly — anything else would be a silent edit of the
    evaluation set (002 FR-022).
    """
    has_instruction = "instruction" in record
    has_input = "input" in record
    if has_instruction != has_input:
        raise SchemaError(
            f"EvaluationPrompt {record.get('id')!r}: instruction and input must be present together or not at all"
        )
    if not has_instruction:
        return
    if record["group"] == "grupo_b":
        raise SchemaError(f"EvaluationPrompt {record.get('id')!r}: grupo_b rows must not carry instruction/input")
    reconstructed = f"{record['instruction']}: {record['input']}" if record["input"] else record["instruction"]
    if reconstructed != record["prompt"]:
        raise SchemaError(
            f"EvaluationPrompt {record.get('id')!r}: instruction/input do not reconstruct prompt exactly "
            f"({reconstructed!r} != {record['prompt']!r})"
        )


def validate_evaluation_result(record: dict) -> None:
    """contracts/evaluation-results-schema.md — eval/results/*.jsonl rows."""
    _require_keys(
        record,
        {"id", "task_category", "model", "prompt", "expected", "output", "grading_method", "score", "run_id"},
        "EvaluationResult",
    )
    if record["model"] not in EVAL_MODELS:
        raise SchemaError(f"EvaluationResult {record.get('id')!r}: model must be one of {sorted(EVAL_MODELS)}")
    if record["grading_method"] not in GRADING_METHODS:
        raise SchemaError(
            f"EvaluationResult {record.get('id')!r}: grading_method must be one of {sorted(GRADING_METHODS)}"
        )
    score = record["score"]
    if score is not None and score not in (0, 0.5, 1):
        raise SchemaError(f"EvaluationResult {record.get('id')!r}: score must be null, 0, 0.5, or 1 — got {score!r}")
    if record["grading_method"] == "rule_based" and score is None:
        raise SchemaError(
            f"EvaluationResult {record.get('id')!r}: rule_based rows must not have a null score "
            "(per contracts/evaluation-results-schema.md's producer rules)"
        )
