from collections import Counter

import numpy as np

from pg.align import WordSpan
from pg.diarize import Diarization, Turn, cluster, speech_windows
from pg.pipeline import _spread


def _voices(order, dim=32, noise=0.15, seed=0):
    rng = np.random.default_rng(seed)
    centres = {s: rng.normal(size=dim) for s in set(order)}
    emb = np.stack([centres[s] + noise * rng.normal(size=dim) * np.linalg.norm(centres[s]) / np.sqrt(dim)
                    for s in order])
    return emb / np.linalg.norm(emb, axis=1, keepdims=True)


def test_cluster_finds_speakers_and_turns():
    order = ["a"] * 12 + ["b"] * 10 + ["a"] * 8 + ["c"] * 12
    windows = [(i * 0.75, i * 0.75 + 1.5) for i in range(len(order))]
    d = cluster(windows, _voices(order))
    assert d.speakers == 3
    assert [t.speaker for t in d.turns] == ["S1", "S2", "S1", "S3"]
    assert d.speaker_at(1.0, 1.5) == "S1" and d.speaker_at(31.0, 31.4) == "S3"


def test_known_speaker_count_and_small_clusters_folded():
    order = ["a"] * 20 + ["b"] * 20
    windows = [(i * 0.75, i * 0.75 + 1.5) for i in range(len(order))]
    emb = _voices(order)
    assert cluster(windows, emb, num_speakers=2).speakers == 2
    assert cluster(windows, emb, num_speakers=1).speakers == 1


def test_speaker_at_uses_nearest_turn_in_a_pause():
    d = Diarization([Turn(0, 2, "S1"), Turn(3, 5, "S2")], 2)
    assert d.speaker_at(2.2, 2.3) == "S1" and d.speaker_at(2.7, 2.8) == "S2"
    assert d.speaker_at(9, 9.5) is None


def test_speech_windows_follow_word_times():
    audio = np.zeros(16000 * 10, dtype=np.float32)
    wins = speech_windows(audio, [(1.0, 3.0), (6.0, 6.2)])
    assert wins and all(1.0 - 0.75 <= s and e <= 3.0 + 0.75 for s, e in wins)


def test_capped_words_are_sampled_through_the_whole_recording():
    spans = [WordSpan("think", float(i), i + 0.3, 1.0) for i in range(100)] + [WordSpan("three", 5.0, 5.3, 1.0)]
    kept = _spread(spans, 5, Counter())
    thinks = [s.start for s in kept if s.word == "think"]
    assert len(thinks) == 5 and thinks[0] == 0.0 and thinks[-1] == 99.0
    assert any(s.word == "three" for s in kept)
    assert not _spread(spans, 5, Counter({"think": 5, "three": 5}))
