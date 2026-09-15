from src.dataset_filters.quality import is_degenerate_output


def test_repeated_token_run_is_degenerate():
    assert is_degenerate_output("rochedo . . . . . . . . . . . . . . . .") is True


def test_repeated_character_run_is_degenerate():
    assert is_degenerate_output("E-mail : ssrsrsrsrsrsrsrsrsrsrsrsrsrs") is True
    assert is_degenerate_output("########") is True


def test_low_character_variety_is_degenerate():
    assert is_degenerate_output("ab ab ab ab ab ab ab ab ab ab ab ab ab ab ab") is True


def test_normal_answer_is_not_degenerate():
    text = (
        "O time de suporte recebeu mais chamados após o lançamento. "
        "A empresa contratou novos atendentes. O tempo de resposta caiu."
    )
    assert is_degenerate_output(text) is False


def test_short_label_is_not_degenerate():
    assert is_degenerate_output("reclamação") is False
    assert is_degenerate_output("Não tóxico") is False


def test_short_text_with_few_distinct_characters_is_not_flagged_by_variety_rule():
    assert is_degenerate_output("aaa bbb") is False  # under the 30-char threshold, no 6-run
