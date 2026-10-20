import math

import numpy as np

from pg.phones import Evidence, PhoneModel, classify_slot


def tiny_model():
    """A PhoneModel with a hand-made vocabulary and no network; scoring runs on given log posteriors."""
    m = PhoneModel.__new__(PhoneModel)
    m.model_id = "tiny"
    m.tok2id = {"<pad>": 0, "θ": 1, "t": 2, "ɪ": 3, "ŋ": 4, "k": 5, "s": 6, "x": 7, "i5": 8}
    m.id2tok = {i: t for t, i in m.tok2id.items()}
    m.blank = 0
    m.special = {0}
    return m


def evidence(frames: list[str], sure: float = 0.9) -> Evidence:
    m = tiny_model()
    logp = np.full((len(frames), len(m.tok2id)), math.log((1 - sure) / (len(m.tok2id) - 1)))
    for i, tok in enumerate(frames):
        logp[i, m.tok2id[tok]] = math.log(sure)
    return Evidence(logp, None)


WORD = ["θ", "ɪ", "ŋ", "k"]


def test_forced_choice_picks_the_variant_in_the_audio():
    m = tiny_model()
    ev = evidence(["θ", "θ", "<pad>", "ɪ", "ŋ", "k", "<pad>"])
    assert classify_slot(m, ev, WORD, 0, ["θ", "t", "s"])[0].label == "θ"
    ev = evidence(["t", "t", "<pad>", "ɪ", "ŋ", "k", "<pad>"])
    best = classify_slot(m, ev, WORD, 0, ["θ", "t", "s"])[0]
    assert best.label == "t" and best.posterior > 0.9


def test_calibration_offsets_shift_close_calls():
    m = tiny_model()
    ev = evidence(["θ", "<pad>", "ɪ", "ŋ", "k"], sure=0.5)
    assert classify_slot(m, ev, WORD, 0, ["θ", "t"])[0].label == "θ"
    assert classify_slot(m, ev, WORD, 0, ["θ", "t"], offsets={"t": 10.0})[0].label == "t"


def test_clip_shorter_than_the_word_cannot_be_scored():
    m = tiny_model()
    scores = classify_slot(m, evidence(["θ", "ɪ"]), WORD, 0, ["θ", "t"])
    assert all(not math.isfinite(s.nll) and s.posterior == 0 for s in scores)


def test_open_set_is_off_by_default_and_needs_a_margin():
    m = tiny_model()
    ev = evidence(["x", "x", "<pad>", "ɪ", "ŋ", "k"])
    assert {s.label for s in classify_slot(m, ev, WORD, 0, ["θ", "t"])} == {"θ", "t"}
    assert classify_slot(m, ev, WORD, 0, ["θ", "t"], open_set=3)[0].label == "x"
    # a token outside the curated IPA inventory (e.g. a tone-numbered vowel) is never proposed, even when heard
    ev = evidence(["i5", "i5", "<pad>", "ɪ", "ŋ", "k"])
    assert "i5" not in {s.label for s in classify_slot(m, ev, WORD, 0, ["θ", "t"], open_set=8)}
