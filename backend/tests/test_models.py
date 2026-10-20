"""End-to-end checks with the real models on six Nigerian English recordings (tests/fixtures/slr70).

They download about 3 GB of models, so they run only when PG_MODEL_TESTS=1 (the CI "models" job, which guards
every library upgrade before it is deployed). expected.json holds what the tested environment heard on these
clips; a new environment must agree with it.

    PG_MODEL_TESTS=1 python -m pytest -q tests/test_models.py
    PG_MODEL_TESTS=1 PG_WRITE_EXPECTED=1 python -m pytest -q tests/test_models.py   # record a new reference
"""
import json
import os
from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.skipif(os.environ.get("PG_MODEL_TESTS") != "1", reason="set PG_MODEL_TESTS=1 to run")

FIXTURES = Path(__file__).parent / "fixtures" / "slr70"
EXPECTED = FIXTURES / "expected.json"
WORDS = ["think", "three", "north", "south", "something", "thousand"]


def _tsv(name):
    return dict(line.rstrip("\n").split("\t", 1) for line in (FIXTURES / name).read_text().splitlines(True))


@pytest.fixture(scope="module")
def clips():
    from pg.audio import load

    transcripts, speakers = _tsv("transcripts.tsv"), _tsv("speakers.tsv")
    return [(n, load(FIXTURES / n), transcripts[n], speakers[n]) for n in sorted(transcripts)]


@pytest.fixture(scope="module")
def conversation(clips):
    """The six clips joined into one recording, as in a short panel conversation."""
    gap = np.zeros(8000, dtype=np.float32)
    pieces, truth, t = [], [], 0.0
    for name, audio, _, speaker in clips:
        pieces += [audio, gap]
        truth.append((t, t + len(audio) / 16000, speaker))
        t += (len(audio) + len(gap)) / 16000
    return np.concatenate(pieces), truth


@pytest.fixture(scope="module")
def analyzer():
    from pg.pipeline import Analyzer

    return Analyzer()


def test_variants_and_preferred_form_match_the_reference(analyzer, clips):
    from pg.pipeline import Recording

    recs = [Recording(n, a, speaker=s, transcript=t) for n, a, t, s in clips]
    result = analyzer.analyse(recs, WORDS, "TH-voiceless")
    got = {f"{t.recording}:{t.word}": t.variant for t in result.tokens}
    if os.environ.get("PG_WRITE_EXPECTED") == "1":
        EXPECTED.write_text(json.dumps({"tokens": got, "preferred": result.preferred}, indent=1, ensure_ascii=False))
    expected = json.loads(EXPECTED.read_text())
    assert set(got) == set(expected["tokens"]), "the target words were not all found"
    same = sum(got[k] == v for k, v in expected["tokens"].items())
    assert same >= len(expected["tokens"]) - 1, f"variants changed: {got} vs {expected['tokens']}"
    assert result.preferred == expected["preferred"]


def test_speech_recognition_finds_the_target_words(analyzer, conversation):
    audio, _ = conversation
    heard = {w.word for w in analyzer.transcriber._transcribe(audio)}
    assert len(heard & set(WORDS)) >= 4, heard
    # and they survive the loop filter that every transcript goes through (whatever transformers' timestamps)
    from pg.asr import drop_loops

    kept = {w.word for w in drop_loops(analyzer.transcriber._transcribe(audio))}
    assert len(kept & set(WORDS)) >= 4, kept


def test_speaker_separation_finds_the_three_speakers(analyzer, conversation):
    audio, truth = conversation
    for dia in (analyzer.diarizer(audio), analyzer.diarizer(audio, num_speakers=3)):
        assert dia.speakers == 3
        # every clip is credited to one label, and different speakers to different labels
        label = {}
        for start, end, speaker in truth:
            label.setdefault(speaker, set()).add(dia.speaker_at(start, end))
        assert all(len(v) == 1 for v in label.values()), label
        assert len({next(iter(v)) for v in label.values()}) == 3, label
