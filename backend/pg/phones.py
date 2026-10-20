"""Acoustic phone evidence from a CTC phone recogniser.

Text-to-IPA only gives dictionary forms; Preference Grammar needs the forms speakers actually
produced. A multilingual CTC phone model gives per-frame phone posteriors, and competing
pronunciations of a word are compared by their CTC likelihood (a forced choice among the
variants under study), which is far more reliable than free phone decoding.
"""
from __future__ import annotations

import itertools
import json
import math
from dataclasses import dataclass

import numpy as np
import torch

DEFAULT_MODEL = "facebook/wav2vec2-xlsr-53-espeak-cv-ft"
FRAME_RATE = 50  # wav2vec2 emits one frame per 20 ms

# lexicon symbols that some phone vocabularies spell differently
FALLBACKS = {
    "ɝ": ["ɜː", "ɚ", "ɜ"], "ɚ": ["ə"], "ɜ": ["ɜː"], "ɜː": ["ɜ"], "i": ["iː"], "iː": ["i"], "u": ["uː"], "uː": ["u"],
    "ɑ": ["ɑː"], "ɑː": ["ɑ"], "ɔ": ["ɔː"], "ɔː": ["ɔ"], "ɒ": ["ɔ"], "əʊ": ["oʊ"], "oʊ": ["əʊ"], "o": ["oʊ"],
    "e": ["ɛ"], "ɛ": ["e"], "ɹ": ["r"], "r": ["ɹ"], "ɡ": ["g"], "t̪": ["t"], "d̪": ["d"], "ɪə": ["iə"],
    "eə": ["ɛɹ", "ɛ"], "ʊə": ["ʊɹ"], "ɐ": ["ʌ"],
}


@dataclass
class Evidence:
    logp: np.ndarray  # (frames, vocab) log posteriors
    hidden: np.ndarray | None  # (frames, dim) features from one transformer layer, for clustering

    def crop(self, start: int, end: int) -> "Evidence":
        start, end = max(0, start), min(len(self.logp), end)
        return Evidence(self.logp[start:end], None if self.hidden is None else self.hidden[start:end])


class PhoneModel:
    def __init__(self, model_id: str = DEFAULT_MODEL, hidden_layer: int | None = None):
        from huggingface_hub import hf_hub_download
        from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC

        self.model_id = model_id
        self.extractor = Wav2Vec2FeatureExtractor.from_pretrained(model_id)
        self.model = Wav2Vec2ForCTC.from_pretrained(model_id).eval()
        with open(hf_hub_download(model_id, "vocab.json"), encoding="utf-8") as f:
            vocab = json.load(f)
        if vocab and isinstance(next(iter(vocab.values())), dict):  # multilingual vocab files nest by language
            vocab = next(iter(vocab.values()))
        self.tok2id = vocab
        self.id2tok = {i: t for t, i in vocab.items()}
        self.blank = self.model.config.pad_token_id
        self.special = {i for t, i in vocab.items() if t.startswith("<") and t.endswith(">")} | {self.blank}
        self.hidden_layer = hidden_layer

    @torch.no_grad()
    def run(self, audio: np.ndarray, sr: int = 16000) -> Evidence:
        inputs = self.extractor(audio, sampling_rate=sr, return_tensors="pt")
        out = self.model(inputs.input_values, output_hidden_states=self.hidden_layer is not None)
        logp = torch.log_softmax(out.logits[0].float(), dim=-1).numpy()
        hidden = None
        if self.hidden_layer is not None:
            hidden = out.hidden_states[self.hidden_layer][0].float().numpy()
        return Evidence(logp, hidden)

    def has(self, seg: str) -> bool:
        return seg in self.tok2id

    def to_ids(self, segs: list[str]) -> list[int]:
        ids = []
        for s in segs:
            if s in self.tok2id:
                ids.append(self.tok2id[s])
                continue
            alt = next((a for a in FALLBACKS.get(s, []) if a in self.tok2id), None)
            if alt is not None:
                ids.append(self.tok2id[alt])
                continue
            # split unknown clusters (e.g. diphthongs) into known symbols
            parts, i = [], 0
            while i < len(s):
                for j in range(len(s), i, -1):
                    if s[i:j] in self.tok2id:
                        parts.append(self.tok2id[s[i:j]])
                        i = j
                        break
                else:
                    raise KeyError(f"phone {s!r} cannot be expressed in {self.model_id}'s vocabulary")
            ids.extend(parts)
        return ids

    def greedy(self, ev: Evidence) -> list[tuple[str, int, int]]:
        """Free phone decoding: (phone, first frame, last frame) per emitted phone."""
        best = ev.logp.argmax(-1)
        out, prev = [], None
        for t, k in enumerate(best):
            k = int(k)
            if k != prev and k not in self.special:
                out.append([self.id2tok[k], t, t])
            elif k == prev and out and k not in self.special:
                out[-1][2] = t
            prev = k
        return [tuple(x) for x in out]

    def nll(self, ev: Evidence, ids: list[int]) -> float:
        """Negative CTC log-likelihood of a phone sequence (inf when it cannot fit the frames)."""
        if not ids:
            return float(-ev.logp[:, self.blank].sum())
        lp = torch.from_numpy(ev.logp).unsqueeze(1)
        loss = torch.nn.functional.ctc_loss(
            lp, torch.tensor([ids]), torch.tensor([lp.shape[0]]), torch.tensor([len(ids)]),
            blank=self.blank, reduction="sum", zero_infinity=False,
        )
        return float(loss)

    def align(self, ev: Evidence, ids: list[int]) -> list[tuple[int, int]]:
        """Frame span of each phone in ids, by CTC forced alignment."""
        import torchaudio.functional as AF

        emissions = torch.from_numpy(ev.logp).unsqueeze(0)
        labels, _ = AF.forced_align(emissions, torch.tensor([ids], dtype=torch.int32), blank=self.blank)
        labels = labels[0].tolist()
        spans, k, prev = [], -1, self.blank
        for t, lab in enumerate(labels):
            if lab != self.blank and (lab != prev or prev == self.blank):
                k += 1
                spans.append([t, t])
            elif lab != self.blank:
                spans[k][1] = t
            prev = lab
        if len(spans) != len(ids):
            raise RuntimeError("alignment did not recover every phone")
        return [tuple(s) for s in spans]


@dataclass
class SlotScore:
    label: str  # the variant (e.g. "t")
    segs: tuple[str, ...]  # the full word as scored
    nll: float
    posterior: float


# spellings a phone model may prefer for the same variant class; a class is scored by its best spelling
SPELLINGS = {
    "t": [["t"], ["t̪"]], "d": [["d"], ["d̪"]], "s": [["s"], ["s̪"]], "ɜː": [["ɜː"], ["ɜ"], ["ɚ"]],
    "ɔ": [["ɔ"], ["ɔː"], ["ɒ"]], "a": [["a"], ["aː"], ["æ"], ["ɑ"], ["ɑː"]], "ɛ": [["ɛ"], ["ɛː"]],
    "e": [["e"], ["eː"]], "o": [["o"], ["oː"]], "iː": [["iː"], ["i"]], "i": [["i"], ["iː"]],
    "əʊ": [["əʊ"], ["oʊ"]], "eɪ": [["eɪ"], ["ei"]], "ʌ": [["ʌ"], ["ɐ"]], "uː": [["uː"], ["u"]],
}


def score_slot(model: PhoneModel, ev: Evidence, word: list[str], slot: int, variants: dict,
               context: dict[int, list[list[str]]] | None = None, temperature: float = 1.0,
               offsets: dict[str, float] | None = None) -> list[SlotScore]:
    """Forced choice among the variants for word[slot].

    variants maps a label to the segments that replace word[slot] ([] for deletion), or to a list of
    alternative spellings (lists of segments), scored by the best one. context optionally lists
    alternative realisations for other slots (e.g. KIT as ɪ or i); each variant is scored with its
    best-fitting context so accent features elsewhere in the word do not bias the comparison."""
    context = context or {}
    others = [i for i in range(len(word)) if i != slot]
    alts = [context.get(i, [[word[i]]]) for i in others]
    scores = []
    for label, reps in variants.items():
        if not reps or isinstance(reps[0], str):
            reps = [reps]
        best_nll, best_segs = math.inf, None
        for rep in reps:
            for combo in itertools.product(*alts):
                segs = []
                for i in range(len(word)):
                    if i == slot:
                        segs.extend(rep)
                    else:
                        segs.extend(combo[others.index(i)])
                try:
                    ids = model.to_ids(segs)
                except KeyError:
                    continue
                v = model.nll(ev, ids)
                if v < best_nll:
                    best_nll, best_segs = v, tuple(segs)
        scores.append(SlotScore(label, best_segs or tuple(), best_nll, 0.0))
    # calibrated score: -nll / T + offset (offsets correct the model's systematic biases; see calibrate.py)
    offsets = offsets or {}
    logits = [-s.nll / temperature + offsets.get(s.label, 0.0) if math.isfinite(s.nll) else -math.inf for s in scores]
    top = max(logits)
    if math.isfinite(top):
        weights = [math.exp(z - top) if math.isfinite(z) else 0.0 for z in logits]
        total = sum(weights)
        for s, w in zip(scores, weights):
            s.posterior = w / total
    order = sorted(range(len(scores)), key=lambda i: (-logits[i], scores[i].nll))
    return [scores[i] for i in order]


# phones an outside-the-candidates realisation may be reported as: plain IPA consonants and vowels,
# not the multilingual vocabulary's tone-numbered or language-specific tokens
_OPEN_SET_OK = set("pbtdkɡqʔmnŋɲɳfvθðszʃʒçxɣχhɦlɹrɾɻjwʋɸβaeiouæɑɒɔəɛɜɪʊʌɐɨʉøœy") | {"tʃ", "dʒ", "ts", "kp", "ɡb", "t̪"}


def classify_slot(model: PhoneModel, ev: Evidence, word: list[str], slot: int, candidates: list[str],
                  context: dict[int, list[list[str]]] | None = None, temperature: float = 1.0,
                  open_set: int = 0, offsets: dict[str, float] | None = None, margin: float = 1.0) -> list[SlotScore]:
    """Score the unit's candidate variants (each over its usual spellings).

    With open_set > 0, the phones the model hears most in the slot are scored too, so a realisation
    outside the candidate set can be reported under its own symbol; an outside phone is kept only if it
    beats every candidate by `margin` nats. Off by default: on the Nigerian gold set it never improved
    accuracy. If no candidate fits the frames (clip shorter than the word), every score is infinite and
    every posterior 0; callers should drop such tokens."""
    variants = {c: SPELLINGS.get(c, [[c]]) for c in candidates}
    scores = score_slot(model, ev, word, slot, variants, context, temperature, offsets)
    if open_set <= 0 or not math.isfinite(scores[0].nll):
        return scores
    try:
        ids = model.to_ids(list(scores[0].segs))
        spans = model.align(ev, ids)
        before = len(model.to_ids([s for i, s in enumerate(scores[0].segs) if i < slot]))
        lo, hi = spans[before][0], spans[before][1] + 1
    except (KeyError, RuntimeError, IndexError):
        return scores
    known = {seg for reps in variants.values() for rep in reps for seg in rep}
    mass = np.exp(ev.logp[lo:hi]).mean(0)
    extra = {}
    for k in np.argsort(-mass):
        tok = model.id2tok[int(k)]
        if int(k) in model.special or tok in known or tok in extra or tok not in _OPEN_SET_OK:
            continue
        extra[tok] = [tok]
        if len(extra) >= open_set:
            break
    outside = score_slot(model, ev, word, slot, extra, context, temperature, offsets) if extra else []
    best_known = scores[0].nll
    winners = {o.label: extra[o.label] for o in outside if o.nll < best_known - margin * temperature}
    return score_slot(model, ev, word, slot, {**variants, **winners}, context, temperature, offsets) if winners else scores
