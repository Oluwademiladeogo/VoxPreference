"""Find where each word of a known transcript is spoken (CTC forced alignment over letters)."""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
import torch

ALIGNER_MODEL = "facebook/wav2vec2-base-960h"
SECONDS_PER_FRAME = 320 / 16000


@dataclass
class WordSpan:
    word: str
    start: float  # seconds
    end: float
    score: float  # mean letter posterior, a rough alignment confidence


def words_of(transcript: str) -> list[str]:
    return [w for w in re.sub(r"[^a-z' ]+", " ", transcript.lower().replace("’", "'")).split() if re.search(r"[a-z]", w)]


class WordAligner:
    def __init__(self, model_id: str = ALIGNER_MODEL):
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

        self.processor = Wav2Vec2Processor.from_pretrained(model_id)
        self.model = Wav2Vec2ForCTC.from_pretrained(model_id).eval()
        self.vocab = self.processor.tokenizer.get_vocab()
        self.blank = self.processor.tokenizer.pad_token_id
        self.upper = all(k.isupper() for k in self.vocab if len(k) == 1 and k.isalpha())

    @torch.no_grad()
    def emissions(self, audio: np.ndarray, window_s: float = 20.0, overlap_s: float = 1.0) -> torch.Tensor:
        """Frame log-posteriors; long audio is processed in overlapping windows to bound memory."""
        win, hop = int(window_s * 16000), int((window_s - overlap_s) * 16000)
        if len(audio) <= win:
            x = self.processor(audio, sampling_rate=16000, return_tensors="pt").input_values
            return torch.log_softmax(self.model(x).logits[0], -1)
        # place every window's frames by its sample offset (320 samples per frame) rather than by counting,
        # because a 20 s window yields 999 frames, not 1000; overlaps are split at their midpoint
        parts, written, half = [], 0, int(overlap_s / 2 / SECONDS_PER_FRAME)
        for start in range(0, len(audio), hop):
            chunk = audio[start:start + win]
            x = self.processor(chunk, sampling_rate=16000, return_tensors="pt").input_values
            lp = torch.log_softmax(self.model(x).logits[0], -1)
            base = start // 320
            last = start + win >= len(audio)
            t0 = max(0, written - base)
            t1 = len(lp) if last else len(lp) - half
            if t1 > t0:
                parts.append(lp[t0:t1])
                written = base + t1
            if last:
                break
        return torch.cat(parts)

    def align(self, audio: np.ndarray, transcript: str) -> list[WordSpan]:
        import torchaudio.functional as AF

        words = words_of(transcript)
        if not words:
            return []
        delim = self.vocab.get("|")
        ids, owner = [], []
        for wi, w in enumerate(words):
            for ch in (w.upper() if self.upper else w):
                if ch in self.vocab:
                    ids.append(self.vocab[ch])
                    owner.append(wi)
            if delim is not None and wi < len(words) - 1:
                ids.append(delim)
                owner.append(-1)
        lp = self.emissions(audio)
        if len(ids) > len(lp):
            raise ValueError("the transcript is longer than the audio can hold")
        labels, scores = AF.forced_align(lp.unsqueeze(0), torch.tensor([ids], dtype=torch.int32), blank=self.blank)
        spans = AF.merge_tokens(labels[0], scores[0].exp())
        if len(spans) != len(ids):
            raise RuntimeError("alignment lost letters")
        out = []
        for wi, w in enumerate(words):
            mine = [s for s, o in zip(spans, owner) if o == wi]
            if not mine:
                continue
            out.append(WordSpan(w, mine[0].start * SECONDS_PER_FRAME, mine[-1].end * SECONDS_PER_FRAME,
                                float(np.mean([s.score for s in mine]))))
        return out
