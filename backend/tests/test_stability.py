from pg.ot import Candidate, Violation
from pg.pipeline import Token, preferred_stability, variant_shares
from pg.tenets import Settings, load_typology, load_units


def tok(speaker, variant):
    return Token("r.wav", speaker, "think", 0, 1, variant, 1.0, {}, "", "")


def think_attested():
    one = lambda: Violation(1)  # noqa: E731
    return [Candidate("tɪŋk", "t", violations={"DisaM": one()}),
            Candidate("θɪŋk", "θ", violations={"Pho-S": one()}),
            Candidate("sɪŋk", "s", violations={"I-Ac": one(), "DisaM": one()})]


def test_speaker_weighting_stops_one_speaker_dominating():
    tokens = [tok("a", "t")] * 9 + [tok("b", "θ"), tok("c", "θ")]
    _, by_token = variant_shares(tokens, "tokens")
    _, by_speaker = variant_shares(tokens, "speakers")
    assert round(by_token["t"], 2) == 0.82 and round(by_speaker["t"], 2) == 0.33


def test_stability_is_high_when_theta_is_clearly_frequent():
    tokens = [tok(f"s{i}", "θ" if i % 2 else "t") for i in range(20)]
    res = preferred_stability(tokens, think_attested(), load_units()["TH-voiceless"], load_typology(), "I-Ac >> ContR >> FreQ >> DisaM >> Pho-S >> Ped-C", Settings(), n=300)
    assert res["preferred_rate"]["θ"] > 0.95


def test_stability_reveals_a_knife_edge_near_the_frequency_threshold():
    # θ used by about 20% of speakers: whether it passes FreQ depends on who is sampled
    tokens = [tok(f"s{i}", "θ" if i < 4 else "t") for i in range(20)]
    res = preferred_stability(tokens, think_attested(), load_units()["TH-voiceless"], load_typology(), "I-Ac >> ContR >> FreQ >> DisaM >> Pho-S >> Ped-C", Settings(), n=300)
    assert 0.2 < res["preferred_rate"].get("θ", 0) < 0.8
