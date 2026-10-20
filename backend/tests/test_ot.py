import pytest

from pg.ot import Candidate, Violation, evaluate, parse_ranking


def think_candidates():
    # the operability table for <th> in 'think' from the PG slides (Ugorji)
    v = lambda: Violation(1)
    return [
        Candidate("tɪŋk", "t", violations={"DisaM": v()}),
        Candidate("sɪŋk", "s", violations={"I-Ac": v(), "FreQ": v(), "DisaM": v()}),
        Candidate("θɪŋk", "θ", violations={"Pho-S": v()}),
        Candidate("zɪŋk", "z", violations={"I-Ac": v(), "FreQ": v(), "DisaM": v()}),
    ]


def test_think_tableau_default_ranking():
    tab = evaluate(think_candidates(), unit="<th>")
    assert [c.form for c in tab.winners] == ["θɪŋk"]
    rows = {r["candidate"]: r for r in tab.to_rows()}
    assert rows["tɪŋk"]["DisaM"] == "*!"
    assert rows["sɪŋk"]["*No I-Ac"] == "*!"
    assert rows["zɪŋk"]["*No I-Ac"] == "*!"
    assert rows["θɪŋk"]["*Pho-S"] == "*"
    assert rows["sɪŋk"]["*No FreQ"] == "*"  # still printed, but shaded as irrelevant
    s = next(c for c in tab.candidates if c.form == "sɪŋk")
    assert tab.shaded(s, "FreQ") and not tab.shaded(s, "I-Ac")


def test_promoting_phonetic_simplicity_changes_the_winner():
    tab = evaluate(think_candidates(), "Pho-S >> I-Ac >> ContR >> FreQ >> DisaM >> Ped-C")
    assert [c.form for c in tab.winners] == ["tɪŋk"]


def test_deleting_tenets_can_produce_a_tie():
    tab = evaluate(think_candidates(), "I-Ac >> ContR >> FreQ")
    assert sorted(c.form for c in tab.winners) == ["tɪŋk", "θɪŋk"]
    assert tab.tie


def test_stratum_pools_marks():
    cands = [
        Candidate("a", violations={"I-Ac": Violation(1)}),
        Candidate("b", violations={"FreQ": Violation(1), "DisaM": Violation(1)}),
    ]
    tab = evaluate(cands, [["I-Ac", "FreQ", "DisaM"]])
    assert [c.form for c in tab.winners] == ["a"]
    row_b = next(r for r in tab.to_rows() if r["candidate"] == "b")
    assert row_b["*No FreQ"] == "*" and row_b["DisaM"] == "*!"


def test_multiple_marks_fatal_position():
    cands = [Candidate("a", violations={"FreQ": Violation(1)}), Candidate("b", violations={"FreQ": Violation(3)})]
    tab = evaluate(cands, "FreQ")
    assert next(r for r in tab.to_rows() if r["candidate"] == "b")["*No FreQ"] == "**!*"


def test_parse_ranking_variants():
    assert parse_ranking("I-Ac >> ContR") == [["I-Ac"], ["ContR"]]
    assert parse_ranking(["Frequency", "phonetic simplicity"]) == [["FreQ"], ["Pho-S"]]
    assert parse_ranking("*No I-Ac >> DisaM, Ped-C") == [["I-Ac"], ["DisaM", "Ped-C"]]
    with pytest.raises(ValueError):
        parse_ranking("I-Ac >> I-Ac")
    with pytest.raises(ValueError):
        parse_ranking("Loudness")
