import json
from collections import Counter

from src.prepare_dataset import (
    EvalKeys,
    _load_eval_prompt_keys,
    build_dataset,
    build_dev_prompts,
    build_report,
    render_report_markdown,
    split_train_validation,
)
from src.schema_validation import validate_evaluation_prompt
from src.text_normalize import normalize

RAW_ALPACA = [
    {"instruction": "Corrija o texto a seguir.", "input": "os menino foi na escola", "output": "Os meninos foram à escola."},
    {"instruction": "Reescreva de maneira profissional.", "input": "fala pro cliente que vai atrasar", "output": "Informe ao cliente que haverá um atraso."},
    {"instruction": "Corrija a ortografia.", "input": "ele viajo ontem", "output": "Ele viajou ontem."},
]

RAW_CANARIM = [
    {"instruction": "Simplifique o texto a seguir.", "context": "A implementação supracitada deverá ser realizada posteriormente.", "output": "A implementação mencionada deverá ser feita depois."},
    {"instruction": "Resuma o texto abaixo.", "context": "texto longo...", "output": "resumo curto"},
    {"instruction": "Classifique a mensagem como reclamação, dúvida, elogio ou solicitação.", "context": "Meu pedido ainda não chegou.", "output": "reclamação"},
]


def _seed(i, instruction="Corrija a frase", input_text="texto", output="Texto.", category="grammar_correction"):
    return {
        "id": f"seed-llm-{i:06d}",
        "source": "seed-llm",
        "task_category": category,
        "instruction": instruction,
        "input": input_text,
        "output": output,
    }


def test_build_dataset_combines_both_sources():
    examples = build_dataset(RAW_ALPACA, RAW_CANARIM, eval_keys=EvalKeys())
    sources = {ex["source"] for ex in examples}
    assert sources == {"alpaca-pt-br", "canarim"}
    categories = {ex["task_category"] for ex in examples}
    assert categories == {"grammar_correction", "rewriting", "simplification", "summarization", "classification"}


def test_build_dataset_excludes_rows_matching_eval_prompts_by_combined_text():
    # eval prompts are "instruction: text"; the row's (instruction, input) renders to exactly that
    eval_keys = EvalKeys(prompts={normalize("Corrija o texto a seguir.: os menino foi na escola")})
    stats = Counter()
    examples = build_dataset(RAW_ALPACA, RAW_CANARIM, eval_keys=eval_keys, stats=stats)
    assert all(ex["input"] != "os menino foi na escola" for ex in examples)
    assert len(examples) == 5
    assert stats["overlap_with_eval"] == 1


def test_build_dataset_excludes_rows_matching_eval_split_pair_accent_insensitively():
    eval_keys = EvalKeys(pairs={(normalize("Corrija a ORTOGRAFIA"), normalize("ele viajo ontem"))})
    examples = build_dataset(RAW_ALPACA, RAW_CANARIM, eval_keys=eval_keys)
    assert all(ex["input"] != "ele viajo ontem" for ex in examples)


def test_load_eval_prompt_keys_uses_split_fields_or_splits_at_first_colon(tmp_path):
    eval_dir = tmp_path / "eval"
    eval_dir.mkdir()
    rows = [
        {"id": "grupo_a-grammar-001", "group": "grupo_a", "task_category": "grammar_correction",
         "prompt": "Corrija: os menino foi", "expected": None, "grading_method": "manual_review"},
        {"id": "grupo_a-grammar-002", "group": "grupo_a", "task_category": "grammar_correction",
         "prompt": "Corrija: a casa é bonita", "instruction": "Corrija", "input": "a casa é bonita",
         "expected": None, "grading_method": "manual_review"},
    ]
    (eval_dir / "grupo_a_prompts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    keys = _load_eval_prompt_keys(eval_dir)
    assert normalize("Corrija: os menino foi") in keys.prompts
    assert (normalize("Corrija"), normalize("os menino foi")) in keys.pairs
    assert (normalize("Corrija"), normalize("a casa é bonita")) in keys.pairs


def test_build_dataset_drops_degenerate_outputs():
    rows = RAW_ALPACA + [{"instruction": "Corrija a frase.", "input": "x", "output": "ssrsrsrsrsrsrsrsrsrsrs"}]
    stats = Counter()
    examples = build_dataset(rows, RAW_CANARIM, eval_keys=EvalKeys(), stats=stats)
    assert stats["degenerate_output"] == 1
    assert all("ssrsrs" not in ex["output"] for ex in examples)


def test_dedupe_collapses_identical_triples_and_pairs_before_split():
    triple = {"instruction": "Corrija a frase.", "input": "ele viajo", "output": "Ele viajou."}
    same_pair_other_output = {"instruction": "corrija a frase.", "input": "Ele viajo", "output": "Ele viajou ontem."}
    rows = [triple, dict(triple), dict(triple), same_pair_other_output]
    stats = Counter()
    examples = build_dataset(rows, [], eval_keys=EvalKeys(), stats=stats)
    assert len(examples) == 1
    assert stats["duplicate_triple"] == 2
    assert stats["duplicate_pair"] == 1


def test_seed_rows_pass_through_the_same_stages():
    seeds = [
        _seed(1, category="classification", instruction="Classifique a mensagem", input_text="Meu pedido atrasou", output="reclamação"),
        _seed(2, category="classification", instruction="Classifique a mensagem", input_text="Meu pedido atrasou", output="reclamação"),  # duplicate
        _seed(3, category="classification", instruction="Classifique a mensagem", input_text="Ótimo!", output="elogio . . . . . . . . ."),  # degenerate
    ]
    stats = Counter()
    stage_counts = {}
    examples = build_dataset(RAW_ALPACA, RAW_CANARIM, eval_keys=EvalKeys(), seed_rows=seeds, stats=stats, stage_counts=stage_counts)
    kept_seed = [ex for ex in examples if ex["source"] == "seed-llm"]
    assert [ex["id"] for ex in kept_seed] == ["seed-llm-000001"]
    assert stats["duplicate_triple"] == 1 and stats["degenerate_output"] == 1
    assert stage_counts["raw"]["classification"] == 1  # public rows only
    assert stage_counts["after_filter"]["classification"] == 4  # + 3 seed rows


def test_cap_counts_over_cap_rows():
    rows = [{"instruction": f"Corrija a frase {i}.", "input": f"texto {i}", "output": f"Texto {i}."} for i in range(7)]
    stats = Counter()
    examples = build_dataset(rows, [], eval_keys=EvalKeys(), target_total=25, stats=stats)  # cap = 5 per category
    assert len(examples) == 5
    assert stats["over_cap"] == 2


def test_cap_keeps_seed_rows_ahead_of_public_rows():
    public = [
        {"instruction": f"Classifique a frase {i} como positiva ou negativa.", "input": f"texto {i}", "output": "positiva"}
        for i in range(20)
    ]
    seeds = [
        _seed(i, category="classification", instruction="Classifique a mensagem", input_text=f"mensagem {i}", output="elogio")
        for i in range(1, 4)
    ]
    examples = build_dataset([], public, eval_keys=EvalKeys(), seed_rows=seeds, target_total=25)  # canarim filter -> classification; cap = 5
    assert len(examples) == 5
    assert sorted(ex["id"] for ex in examples if ex["source"] == "seed-llm") == [f"seed-llm-{i:06d}" for i in range(1, 4)]


def test_cap_emits_categories_in_sorted_order_regardless_of_input_order():
    """Set iteration order varies with PYTHONHASHSEED; the cap must not let it leak into the file order."""
    from src.prepare_dataset import _cap_per_category

    rows = [
        {"source": "canarim", "task_category": c, "instruction": f"i{c}{i}", "input": "", "output": "o"}
        for c in ("summarization", "classification", "rewriting", "grammar_correction", "simplification")
        for i in range(2)
    ]
    order = [r["task_category"] for r in _cap_per_category(rows, target_total=50)]
    assert order == sorted(order)
    assert order == [r["task_category"] for r in _cap_per_category(list(reversed(rows)), target_total=50)]


def test_build_dataset_produces_no_duplicate_ids():
    examples = build_dataset(RAW_ALPACA, RAW_CANARIM, eval_keys=EvalKeys())
    ids = [ex["id"] for ex in examples]
    assert len(ids) == len(set(ids))


def test_split_train_validation_respects_fraction():
    examples = [{"id": f"x-{i}"} for i in range(100)]
    train, validation = split_train_validation(examples, validation_fraction=0.1)
    assert len(validation) == 10
    assert len(train) == 90
    assert set(ex["id"] for ex in train).isdisjoint(ex["id"] for ex in validation)


def test_split_train_validation_handles_empty_input():
    train, validation = split_train_validation([])
    assert train == []
    assert validation == []


def test_dev_prompts_come_only_from_validation_rows_and_validate():
    validation = [
        {"id": f"canarim-{i:06d}", "source": "canarim", "task_category": "summarization",
         "instruction": "Resuma o texto", "input": f"texto {i}", "output": f"resumo {i}"}
        for i in range(12)
    ] + [
        {"id": "canarim-900000", "source": "canarim", "task_category": "classification",
         "instruction": "Classifique como positivo ou negativo", "input": "", "output": "Positivo"},
    ]
    dev = build_dev_prompts(validation, per_category=10, seed=1)
    assert len([d for d in dev if d["task_category"] == "summarization"]) == 10
    assert len([d for d in dev if d["task_category"] == "classification"]) == 1
    assert {d["source_id"] for d in dev} <= {v["id"] for v in validation}
    for d in dev:
        validate_evaluation_prompt(d)
    cls = next(d for d in dev if d["task_category"] == "classification")
    assert cls["grading_method"] == "rule_based" and cls["expected"] == "Positivo"
    assert cls["prompt"] == "Classifique como positivo ou negativo"  # empty input → instruction alone
    summ = next(d for d in dev if d["task_category"] == "summarization")
    assert summ["grading_method"] == "manual_review" and summ["prompt"] == f"Resuma o texto: {summ['input']}"


def test_report_has_contract_fields_and_warns_below_minimum():
    train = [
        {"id": f"a-{i}", "source": "alpaca-pt-br", "task_category": "grammar_correction",
         "instruction": "x", "input": "y", "output": "z"}
        for i in range(3)
    ]
    validation = [dict(train[0], id="a-v")]
    stats = Counter({"duplicate_triple": 2, "degenerate_output": 1})
    stage_counts = {"raw": Counter({"grammar_correction": 6}), "after_filter": Counter({"grammar_correction": 6})}
    report = build_report(
        seed=42,
        source_rows_in={"alpaca-pt-br": 100, "seed-llm": 5},
        train=train,
        validation=validation,
        stats=stats,
        stage_counts=stage_counts,
        fingerprints={"data/train.jsonl": "abc", "data/validation.jsonl": "def"},
    )
    assert set(report) == {"generated_at", "seed", "sources", "by_category", "dropped_by_reason", "fingerprints", "warnings"}
    assert report["sources"]["alpaca-pt-br"] == {"license": "CC BY-NC-4.0", "rows_in": 100, "rows_kept": 4}
    assert report["sources"]["seed-llm"]["rows_kept"] == 0
    assert set(report["dropped_by_reason"]) == {
        "no_output", "exclude_regex", "label_not_in_instruction", "missing_input", "degenerate_output",
        "overlap_with_eval", "duplicate_triple", "duplicate_pair", "over_cap",
    }
    entry = report["by_category"]["grammar_correction"]
    assert set(entry) == {"raw", "after_filter", "after_quality", "after_eval_dedupe", "after_dedupe", "after_cap", "train", "validation"}
    assert entry["train"] == 3 and entry["validation"] == 1 and entry["raw"] == 6
    assert len(report["warnings"]) == 5  # every category is below 350 in this tiny fixture
    assert any(w.startswith("grammar_correction: 4 < 350") for w in report["warnings"])
    markdown = render_report_markdown(report)
    assert "| grammar_correction | 6 | 6 |" in markdown and "duplicate_triple | 2" in markdown
