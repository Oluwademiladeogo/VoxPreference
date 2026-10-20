"""Speaker separation (diarization) for recordings with several speakers, such as podcasts and interviews.

Every target word must be credited to the person who said it, or "every speaker counts equally", the
minimum-speaker rule and the speaker resampling in the stability check all treat a whole panel as one person.
Short overlapping windows of speech are turned into speaker embeddings (SpeechBrain's ECAPA-TDNN model trained
for speaker verification on VoxCeleb), averaged with their neighbours, grouped by agglomerative clustering on
cosine distance, refined and smoothed over time, and each word is given the label of the windows it falls in.
On made-up conversations of 2-5 SLR70 Nigerian speakers this credited every sampled word to the right speaker
(eval/diarize_eval.py); WavLM (microsoft/wavlm-base-plus-sv) managed 71-100% and is kept as an option. The speaker labels are anonymous (S1, S2, ... in order of first
speaking); they say who spoke together, not who the person is.
"""
from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

SPEAKER_MODEL = "speechbrain/spkrec-ecapa-voxceleb"
WAVLM_MODEL = "microsoft/wavlm-base-plus-sv"
# cosine distance at which clusters stop merging, tuned per model on eval/diarize_eval.py conversations
THRESHOLDS = {SPEAKER_MODEL: 0.9, WAVLM_MODEL: 0.7}
CACHE_DIR = Path(os.environ.get("PG_CACHE", Path(__file__).resolve().parents[1] / "data" / "cache" / "diarize"))
SR = 16000


@dataclass
class Turn:
    start: float
    end: float
    speaker: str


@dataclass
class Diarization:
    turns: list[Turn]
    speakers: int

    def speaker_at(self, start: float, end: float, reach: float = 2.0) -> str | None:
        """The speaker who talks most during [start, end]; else the nearest turn within reach seconds."""
        overlap = Counter()
        for t in self.turns:
            o = min(end, t.end) - max(start, t.start)
            if o > 0:
                overlap[t.speaker] += o
        if overlap:
            return overlap.most_common(1)[0][0]
        mid = (start + end) / 2
        near = min(self.turns, key=lambda t: min(abs(mid - t.start), abs(mid - t.end)), default=None)
        if near is not None and min(abs(mid - near.start), abs(mid - near.end)) <= reach:
            return near.speaker
        return None


def speech_windows(audio: np.ndarray, speech: list[tuple[float, float]] | None = None, win_s: float = 1.5,
                   hop_s: float = 0.75, min_cover: float = 0.5) -> list[tuple[float, float]]:
    """Windows that are mostly speech. Speech regions come from word times when known, else from frame energy."""
    total = len(audio) / SR
    step = 0.01
    voiced = np.zeros(int(total / step) + 1, dtype=bool)
    if speech:
        for s, e in speech:
            voiced[int(max(0.0, s) / step):int(min(total, e) / step) + 1] = True
    else:
        hop = int(step * SR)
        frames = audio[: len(audio) // hop * hop].reshape(-1, hop)
        db = 20 * np.log10(np.sqrt((frames ** 2).mean(1) + 1e-12))
        voiced[: len(db)] = db > np.percentile(db, 30) + 6  # well above the noise floor
    out, t = [], 0.0
    while t + win_s <= total + 1e-6:
        a, b = int(t / step), int((t + win_s) / step)
        if voiced[a:b].mean() >= min_cover:
            out.append((round(t, 3), round(t + win_s, 3)))
        t += hop_s
    return out


class Diarizer:
    def __init__(self, model_id: str = SPEAKER_MODEL):
        import torch

        self.torch = torch
        self.model_id = model_id
        if model_id.startswith("speechbrain/"):
            from speechbrain.inference.speaker import EncoderClassifier

            self.model = EncoderClassifier.from_hparams(source=model_id, run_opts={"device": "cpu"},
                                                        savedir=str(CACHE_DIR.parent / "speechbrain" / model_id.split("/")[1]))
            self.extractor = None
        else:
            from transformers import AutoFeatureExtractor, WavLMForXVector

            self.extractor = AutoFeatureExtractor.from_pretrained(model_id)
            self.model = WavLMForXVector.from_pretrained(model_id).eval()

    def embed(self, audio: np.ndarray, windows: list[tuple[float, float]], batch: int = 16) -> np.ndarray:
        out = []
        with self.torch.inference_mode():
            for i in range(0, len(windows), batch):
                clips = [audio[int(s * SR):int(e * SR)] for s, e in windows[i:i + batch]]
                if self.extractor is None:
                    n = min(len(c) for c in clips)
                    wavs = self.torch.from_numpy(np.stack([c[:n] for c in clips]))
                    out.append(self.model.encode_batch(wavs).squeeze(1).numpy())
                else:
                    inputs = self.extractor(clips, sampling_rate=SR, return_tensors="pt", padding=True)
                    out.append(self.model(**inputs).embeddings.numpy())
        emb = np.concatenate(out) if out else np.zeros((0, 192), dtype=np.float32)
        return emb / (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9)

    def __call__(self, audio: np.ndarray, speech: list[tuple[float, float]] | None = None,
                 num_speakers: int | None = None, threshold: float | None = None) -> Diarization:
        threshold = threshold or THRESHOLDS.get(self.model_id, 0.9)
        key = hashlib.sha1(np.ascontiguousarray(audio, dtype=np.float32).tobytes()).hexdigest()[:20]
        spec = f"{num_speakers or 'auto'}_{threshold}_{'words' if speech else 'energy'}"
        cache = CACHE_DIR / f"{self.model_id.replace('/', '_')}_{key}_{spec}.json"
        if cache.exists():
            d = json.loads(cache.read_text(encoding="utf-8"))
            return Diarization([Turn(**t) for t in d["turns"]], d["speakers"])
        windows = speech_windows(audio, speech)
        result = cluster(windows, self.embed(audio, windows), num_speakers, threshold)
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps({"turns": [asdict(t) for t in result.turns], "speakers": result.speakers}),
                             encoding="utf-8")
        except OSError:
            pass
        return result


def cluster(windows: list[tuple[float, float]], emb: np.ndarray, num_speakers: int | None = None,
            threshold: float = 0.9, min_share: float = 0.03, smooth: int = 5, centre: bool = True,
            refine: int = 5, context: int = 1) -> Diarization:
    """Group windows by speaker. With num_speakers unknown, clusters merge until their average cosine
    distance exceeds threshold; clusters holding under min_share of the speech are folded into the nearest.
    The embeddings are centred first: they share a large common part (channel, language), which otherwise
    makes everyone look alike. Each window is then averaged with `context` neighbours on each side within the
    same stretch of speech, since a voice is recognised better from ~3 s than from 1.5 s."""
    if len(windows) == 0:
        return Diarization([], 0)
    if centre and len(emb) > 1:
        emb = emb - emb.mean(0)
        emb = emb / (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9)
    if context > 0 and len(emb) > 1:
        starts = np.array([s for s, _ in windows])
        hop = float(np.median(np.diff(starts))) if len(starts) > 1 else 0.75
        avg = np.empty_like(emb)
        for i in range(len(emb)):
            lo, hi = max(0, i - context), min(len(emb), i + context + 1)
            near = [j for j in range(lo, hi) if abs(starts[j] - starts[i]) <= context * hop + 0.01]
            avg[i] = emb[near].mean(0)
        emb = avg / (np.linalg.norm(avg, axis=1, keepdims=True) + 1e-9)
    if len(windows) == 1 or num_speakers == 1:
        labels = np.zeros(len(windows), dtype=int)
    else:
        from sklearn.cluster import AgglomerativeClustering

        ac = AgglomerativeClustering(n_clusters=min(num_speakers, len(windows)) if num_speakers else None,
                                     distance_threshold=None if num_speakers else threshold,
                                     metric="cosine", linkage="average")
        labels = ac.fit_predict(emb)
    labels = _fold_small(labels, emb, min_share, keep=num_speakers)
    for _ in range(refine):  # move each window to the speaker whose average voice it is closest to
        names = sorted(set(labels.tolist()))
        cents = np.stack([emb[labels == c].mean(0) for c in names])
        new = np.array(names)[np.argmax(emb @ cents.T, axis=1)]
        if (new == labels).all():
            break
        labels = new
    labels = _smooth(labels, windows, smooth)
    # S1, S2, ... in order of first speaking
    order = {lab: f"S{i + 1}" for i, lab in enumerate(dict.fromkeys(labels.tolist()))}
    turns = []
    for (s, e), lab in zip(windows, labels):
        name = order[lab]
        if turns and turns[-1].speaker == name and s <= turns[-1].end + 0.01:
            turns[-1].end = e
        else:
            turns.append(Turn(s, e, name))
    # where windows of two speakers overlap, split the overlap halfway
    for a, b in zip(turns, turns[1:]):
        if a.speaker != b.speaker and b.start < a.end:
            a.end = b.start = round((a.end + b.start) / 2, 3)
    return Diarization(turns, len(order))


def _fold_small(labels: np.ndarray, emb: np.ndarray, min_share: float, keep: int | None) -> np.ndarray:
    labels = labels.copy()
    while True:
        counts = Counter(labels.tolist())
        if len(counts) <= max(1, keep or 1):
            return labels
        small = min(counts, key=counts.get)
        if counts[small] >= min_share * len(labels):
            return labels
        cents = {c: emb[labels == c].mean(0) for c in counts if c != small}
        mine = emb[labels == small].mean(0)
        labels[labels == small] = max(cents, key=lambda c: float(cents[c] @ mine))


def _smooth(labels: np.ndarray, windows: list[tuple[float, float]], k: int) -> np.ndarray:
    """Majority vote over neighbouring windows within the same stretch of speech; turns rarely last under ~2 s."""
    if k <= 1 or len(labels) < 3:
        return labels
    out = labels.copy()
    half = k // 2
    for i in range(len(labels)):
        lo, hi = max(0, i - half), min(len(labels), i + half + 1)
        near = [labels[j] for j in range(lo, hi) if abs(windows[j][0] - windows[i][0]) <= half * 1.0 + 0.01]
        out[i] = Counter(near).most_common(1)[0][0] if Counter(near).most_common(1)[0][1] > 1 else labels[i]
    return out
