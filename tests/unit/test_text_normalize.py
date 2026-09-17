from src.text_normalize import normalize


def test_lowercases_and_strips_accents():
    assert normalize("Reclamação") == "reclamacao"
    assert normalize("DÚVIDA") == "duvida"


def test_collapses_internal_whitespace_and_trims():
    assert normalize("  Resuma   o\ttexto \n a seguir  ") == "resuma o texto a seguir"


def test_strips_trailing_period_and_spaces_by_default():
    assert normalize("reclamação.") == "reclamacao"
    assert normalize("reclamação . ") == "reclamacao"
    assert normalize("fim. de. frase") == "fim. de. frase"  # only trailing punctuation is removed


def test_keeps_trailing_period_when_asked():
    assert normalize("reclamação.", strip_trailing_period=False) == "reclamacao."


def test_nfkd_folds_compatibility_forms():
    assert normalize("ﬁm") == "fim"  # U+FB01 ligature
    assert normalize("１２３") == "123"  # fullwidth digits


def test_empty_and_punctuation_only_inputs():
    assert normalize("") == ""
    assert normalize("...") == ""
    assert normalize("...", strip_trailing_period=False) == "..."
