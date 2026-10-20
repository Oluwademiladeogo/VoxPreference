"""Find target words in unscripted speech (podcasts, interviews) that has no transcript.

Whisper transcribes with word timestamps; each hit of a target word is then re-aligned against its
neighbouring words with the letter aligner, because ASR word times are only approximate, and hits
whose alignment is poor are dropped instead of being scored.
"""
from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from .align import WordAligner, WordSpan, words_of

ASR_MODEL = "openai/whisper-small"
CACHE_DIR = Path(os.environ.get("PG_CACHE", Path(__file__).resolve().parents[1] / "data" / "cache" / "asr"))


@dataclass
class Hit:
    span: WordSpan  # refined position of the target word
    context: str  # the words around it, as transcribed


class Transcriber:
    def __init__(self, model_id: str = ASR_MODEL):
        from transformers import pipeline

        self.model_id = model_id
        self.pipe = pipeline("automatic-speech-recognition", model=model_id, device="cpu")

    def words(self, audio: np.ndarray) -> list[WordSpan]:
        """Word spans for the whole recording. Transcripts are cached on disk (keyed by the audio), because
        transcribing an hour of speech on a CPU takes about an hour and a survey reuses it for every sound."""
        key = hashlib.sha1(np.ascontiguousarray(audio, dtype=np.float32).tobytes()).hexdigest()[:20]
        cache = CACHE_DIR / f"{self.model_id.replace('/', '_')}_{key}.json"
        if cache.exists():
            return drop_loops([WordSpan(**w) for w in json.loads(cache.read_text(encoding="utf-8"))])
        spans = self._transcribe(audio, progress=cache.with_suffix(".partial.jsonl"))
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps([asdict(w) for w in spans]), encoding="utf-8")
            cache.with_suffix(".partial.jsonl").unlink(missing_ok=True)
        except OSError:
            pass
        return drop_loops(spans)

    def _transcribe(self, audio: np.ndarray, window_s: float = 30.0, overlap_s: float = 2.0,
                    progress: Path | None = None) -> list[WordSpan]:
        """Transcribe in 30 s windows that overlap by 2 s, each decoded on its own. (The pipeline's own chunk
        merging crashes on some long recordings when a word in an overlap has no timestamp.) A word is kept from
        the window where it lies in the middle part, so words cut at a window edge come from the neighbour.
        Each finished window is appended to `progress`, so an interrupted run resumes where it stopped; a window
        that fails is skipped with a warning."""
        sr, total = 16000, len(audio) / 16000
        step = window_s - overlap_s
        starts = [i * step for i in range(max(1, int(np.ceil((total - overlap_s) / step))))]
        done = {}
        if progress is not None and progress.exists():
            for line in progress.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                    done[row["window"]] = row["words"]
                except (ValueError, KeyError):
                    continue
        spans = []
        for i, s0 in enumerate(starts):
            if i not in done:
                try:
                    done[i] = self._window(audio[int(s0 * sr):int((s0 + window_s) * sr)])
                except Exception as e:  # one bad window must not lose an hour of transcription
                    print(f"warning: speech recognition failed on {s0:.0f}-{s0 + window_s:.0f} s ({type(e).__name__}); skipped")
                    continue
                if progress is not None:
                    try:
                        progress.parent.mkdir(parents=True, exist_ok=True)
                        with progress.open("a", encoding="utf-8") as f:
                            f.write(json.dumps({"window": i, "words": done[i]}) + "\n")
                    except OSError:
                        pass
            lo = s0 + (overlap_s / 2 if i > 0 else 0.0)
            hi = s0 + window_s - (overlap_s / 2 if i < len(starts) - 1 else -1.0)
            for w, a, b in done[i]:
                mid = s0 + (a + b) / 2
                if lo <= mid < hi:
                    spans.append(WordSpan(w, round(s0 + a, 3), round(s0 + b, 3), 1.0))
        return spans

    def _window(self, clip: np.ndarray) -> list[list]:
        """[word, start, end] (seconds from the start of the clip) for a clip of at most 30 s."""
        out = self.pipe({"raw": clip, "sampling_rate": 16000}, return_timestamps="word",
                        generate_kwargs={"language": "en", "task": "transcribe"})
        words = []
        for chunk in out.get("chunks", []):
            start, end = chunk["timestamp"]
            if start is None:
                continue
            for w in words_of(chunk["text"]):
                words.append([w, float(start), float(end if end is not None else start + 0.3)])
        return words


def drop_loops(spans: list[WordSpan], max_repeats: int = 3, max_n: int = 8, pile: int = 3) -> list[WordSpan]:
    """Remove Whisper's repetition loops. On long conversational audio Whisper can get stuck repeating a phrase
    ("i like this" x103), inventing words that were never said: a phrase of 1-8 words repeated more than
    max_repeats times in a row keeps only its first occurrence, and words stacked on one timestamp (pile or
    more sharing a start, with no duration) are dropped. A lone word with no duration is real but untimed (some
    transformers versions return many of these); it gets a nominal 0.3 s, as find_targets re-aligns it anyway."""
    starts = Counter(round(w.start, 2) for w in spans if w.end - w.start <= 0.01)
    words = []
    for w in spans:
        if w.end - w.start > 0.01:
            words.append(w)
        elif starts[round(w.start, 2)] < pile:
            words.append(WordSpan(w.word, w.start, w.start + 0.3, w.score))
    keep = [True] * len(words)
    i = 0
    while i < len(words):
        jumped = False
        for n in range(1, max_n + 1):
            gram = [w.word for w in words[i:i + n]]
            if len(gram) < n:
                break
            reps = 1
            while [w.word for w in words[i + reps * n:i + (reps + 1) * n]] == gram:
                reps += 1
            if reps > max_repeats:
                for k in range(i + n, i + reps * n):
                    keep[k] = False
                i += reps * n
                jumped = True
                break
        if not jumped:
            i += 1
    return [w for w, k in zip(words, keep) if k]


def find_targets(audio: np.ndarray, asr_words: list[WordSpan], targets: set[str], aligner: WordAligner,
                 context: int = 2, pad_s: float = 0.15, min_score: float = 0.2) -> list[Hit]:
    """Re-align every transcribed occurrence of a target word inside a short window of its neighbours."""
    hits = []
    for i, w in enumerate(asr_words):
        if w.word not in targets:
            continue
        lo, hi = max(0, i - context), min(len(asr_words), i + context + 1)
        window = asr_words[lo:hi]
        t0 = max(0.0, window[0].start - pad_s)
        t1 = min(len(audio) / 16000, window[-1].end + pad_s)
        segment = audio[int(t0 * 16000):int(t1 * 16000)]
        text = " ".join(x.word for x in window)
        try:
            spans = aligner.align(segment, text)
        except (ValueError, RuntimeError):
            continue
        mine = spans[i - lo] if len(spans) == len(window) else None
        if mine is None or mine.word != w.word or mine.score < min_score:
            continue
        hits.append(Hit(WordSpan(w.word, t0 + mine.start, t0 + mine.end, mine.score), text))
    return hits
