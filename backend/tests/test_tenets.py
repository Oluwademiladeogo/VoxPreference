from pathlib import Path

import pytest

from pg import lexicon
from pg.ot import Candidate, evaluate
from pg.tenets import Settings, assess, load_typology, load_units, reference_phoneme, tiers

RESOURCES = Path(__file__).resolve().parents[1] / "data" / "resources"
needs_lexicons = pytest.mark.skipif(not (RESOURCES / "lexicons").exists(), reason="lexicons not downloaded")


@pytest.fixture(scope="module")
def lexicons():
    return list(lexicon.load_default(RESOURCES, names=("cmudict", "britfone")).values())


def marks(cands):
    return {c.segment: {t for t, v in c.violations.items() if v.count} for c in cands}


@needs_lexicons
def test_reproduces_ugorji_think_tableau(lexicons):
    # Ugorji 2010: 58; shares of word-initial /θ/ in ICE-Nigeria (Oyebola, Ho & Li 2019)
    unit = load_units()["TH-voiceless"]
    shares = {"t": 0.488, "θ": 0.472, "s": 0.04, "z": 0.0}
    cands = [Candidate(f"{s}ɪŋk", s, tokens=round(p * 729), share=p) for s, p in shares.items()]
    assess(cands, unit, "think", lexicons, load_typology(), Settings())
    assert marks(cands) == {
        "t": {"DisaM"},
        "s": {"I-Ac", "FreQ", "DisaM"},
        "θ": {"Pho-S"},
        "z": {"I-Ac", "FreQ", "DisaM"},
    }
    tab = evaluate(cands, unit="<th>")
    assert [c.form for c in tab.winners] == ["θɪŋk"]
    assert "sink" in cands[2].violations["DisaM"].reason
    assert tiers(tab) == {"t": "allophone (formal inventory)", "s": "outer (informal) norm",
                          "θ": "preferred (formal standard)", "z": "outer (informal) norm"}


@needs_lexicons
def test_reproduces_ugorji_goat_evaluation(lexicons):
    # Ugorji 2010 as reported by Jowitt 2015: 8; Ugorji's /ɒ/ is phonetically [ɔ]
    unit = load_units()["GOAT"]
    shares = {"o": 0.60, "ɔ": 0.16, "əʊ": 0.05}
    cands = [Candidate(f"ɡ{s}t", s, tokens=round(p * 100), share=p) for s, p in shares.items()]
    assess(cands, unit, "goat", lexicons, load_typology(), Settings())
    assert marks(cands) == {
        "o": set(),
        "əʊ": {"FreQ", "Pho-S", "Ped-C"},
        "ɔ": {"I-Ac", "ContR", "FreQ", "DisaM"},
    }
    assert [c.segment for c in evaluate(cands).winners] == ["o"]


@needs_lexicons
def test_think_flips_when_theta_is_rare(lexicons):
    # with less-educated speakers θ is rare (Akande 2005: 16%), so FreQ removes it before DisaM can act
    unit = load_units()["TH-voiceless"]
    cands = [Candidate("tɪŋk", "t", 84, 0.84), Candidate("θɪŋk", "θ", 16, 0.16)]
    assess(cands, unit, "think", lexicons, load_typology(), Settings())
    assert [c.segment for c in evaluate(cands).winners] == ["t"]
    assert cands[1].violations["Ped-C"].count == 1  # absent from the L1s and rarely used


@needs_lexicons
def test_expert_override_and_contrastiveness_for_core_consonants(lexicons):
    unit = load_units()["TH-voiceless"]
    cands = [Candidate("tɪŋk", "t", 60, 0.6), Candidate("θɪŋk", "θ", 40, 0.4)]
    assess(cands, unit, "think", lexicons, load_typology(), Settings(overrides={"t|DisaM": 0}))
    assert [c.form for c in evaluate(cands).winners] == ["tɪŋk"]


def test_reference_phoneme_mapping():
    typ = load_typology()
    assert reference_phoneme("t̪", typ) == "t"
    assert reference_phoneme("ɔ", typ) == "ɒ"  # Ugorji's /ɒ/
    assert reference_phoneme("o", typ) is None and reference_phoneme("e", typ) is None
    assert reference_phoneme("ʌ", typ) == "ɐ"


@needs_lexicons
def test_frequency_first_picks_the_commonest_form_in_most_frequent_mode(lexicons):
    # the user's reading of PG: rank Frequency first and the most frequent pronunciation is preferred
    unit = load_units()["TH-voiceless"]
    shares = {"t": 0.488, "θ": 0.472, "s": 0.04}
    ranking = "FreQ >> I-Ac >> ContR >> DisaM >> Pho-S >> Ped-C"
    for mode, winner in (("most_frequent", "t"), ("threshold", "θ")):
        cands = [Candidate(f"{s}ɪŋk", s, tokens=round(p * 729), share=p) for s, p in shares.items()]
        assess(cands, unit, "think", lexicons, load_typology(), Settings(freq_mode=mode))
        assert [c.segment for c in evaluate(cands, ranking).winners] == [winner]
