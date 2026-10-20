from pathlib import Path

import pytest

from pg import lexicon

RESOURCES = Path(__file__).resolve().parents[1] / "data" / "resources"


def test_segments_keeps_multi_character_phones_together():
    assert lexicon.segments("ˈθɪŋk") == ["θ", "ɪ", "ŋ", "k"]
    assert lexicon.segments("tʃɜːtʃ") == ["tʃ", "ɜː", "tʃ"]
    assert lexicon.segments("/ɡəʊt/") == ["ɡ", "əʊ", "t"]
    assert lexicon.segments("t̪ɪŋk") == ["t̪", "ɪ", "ŋ", "k"]
    assert lexicon.segments("gʊd") == ["ɡ", "ʊ", "d"]  # ASCII g is normalised to IPA ɡ


def test_arpabet_conversion_handles_stress():
    assert lexicon.arpabet_to_ipa(["TH", "IH1", "NG", "K"]) == ["θ", "ɪ", "ŋ", "k"]
    assert lexicon.arpabet_to_ipa(["AH0", "B", "AH1", "V"]) == ["ə", "b", "ʌ", "v"]
    assert lexicon.arpabet_to_ipa(["B", "ER1", "D"]) == ["b", "ɝ", "d"]


def test_merger_pairs_and_homophones_in_memory():
    lex = lexicon.Lexicon("tiny")
    for w, p in [("three", "θɹi"), ("tree", "tɹi"), ("thin", "θɪn"), ("tin", "tɪn"), ("think", "θɪŋk"), ("sink", "sɪŋk")]:
        lex.add(w, lexicon.segments(p))
    assert lex.merger_pairs("θ", "t") == [("thin", "tin"), ("three", "tree")]
    assert lex.merger_pairs("θ", "θ") == []
    assert lex.homophones(["s", "ɪ", "ŋ", "k"], exclude="think") == {"sink"}


@pytest.mark.skipif(not (RESOURCES / "lexicons").exists(), reason="lexicons not downloaded")
def test_real_lexicons_reproduce_think_homophones():
    lexs = lexicon.load_default(RESOURCES)
    cmu = lexs["cmudict"]
    assert cmu.pronunciations("think") == [("θ", "ɪ", "ŋ", "k")]
    assert "sink" in cmu.homophones(("s", "ɪ", "ŋ", "k"))
    assert "zinc" in cmu.homophones(("z", "ɪ", "ŋ", "k"))
    assert not cmu.homophones(("t", "ɪ", "ŋ", "k"))
    assert ("three", "tree") in cmu.merger_pairs("θ", "t")
