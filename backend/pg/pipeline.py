"""End-to-end Preference Grammar analysis.

recordings of target words -> where the words are -> which variant of the unit each speaker produced
-> two-level clusters -> candidates with violation marks -> operability table -> preferred form.
"""
from __future__ import annotations

import math
import random
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

import numpy as np

from . import audio as audio_io
from . import calibrate as calibration
from . import lexicon
from .cluster import Clustering, two_level
from .ot import DEFAULT_RANKING, Candidate, Tableau, evaluate
from .phones import DEFAULT_MODEL, FRAME_RATE, Evidence, PhoneModel, classify_slot
from .tenets import Settings, Unit, _overrides as _raw_overrides, assess, common_words, load_typology, load_units, share_dependent, tiers

RESOURCES = Path(__file__).resolve().parents[1] / "data" / "resources"


@dataclass
class Recording:
    name: str
    audio: np.ndarray
    speaker: str = ""
    transcript: str = ""  # empty: the recording is just the target word; "auto": find the words by ASR
    diarize: bool | None = None  # separate speakers inside the recording; None: yes for "auto" recordings with no speaker id
    num_speakers: int | None = None  # how many people talk in it, if known (else estimated)


@dataclass
class Token:
    recording: str
    speaker: str
    word: str
    start: float
    end: float
    variant: str
    posterior: float
    scores: dict
    realised: str  # the best-fitting form of the whole word, in IPA
    heard: str  # free phone decoding of the word, for comparison
    primary: str = ""
    secondary: str = ""
    review: bool = False
    nll: dict = field(default_factory=dict)  # raw CTC scores per variant, for recalibration


@dataclass
class Analysis:
    words: list[str]
    unit: Unit
    canonical: dict
    tokens: list[Token]
    clustering: Clustering | None
    candidates: list[Candidate]
    tableau: Tableau | None
    preferred: list[str]
    warnings: list[str] = field(default_factory=list)
    stability: dict | None = None  # how often each variant wins when speakers are resampled
    superfluous: list[Candidate] = field(default_factory=list)  # attested too rarely to compete

    def to_dict(self) -> dict:
        tab = self.tableau
        return {
            "words": self.words,
            "unit": asdict(self.unit),
            "canonical": self.canonical,
            "tokens": [asdict(t) for t in self.tokens],
            "clusters": None if self.clustering is None else {
                "categories": self.clustering.categories,
                "contrast_matrix": np.round(self.clustering.contrast, 4).tolist(),
                "separation": {k: (None if math.isnan(v) else round(v, 4)) for k, v in self.clustering.separation.items()},
                "subclusters": dict(Counter(self.clustering.secondary)),
            },
            "candidates": [
                {"form": c.form, "segment": c.segment, "tokens": c.tokens, "share": round(c.share, 4),
                 "tier": (tiers(tab) if tab else {}).get(c.segment, ""),
                 "violations": {t: asdict(v) for t, v in c.violations.items()}}
                for c in self.candidates
            ],
            "superfluous": [{"form": c.form, "segment": c.segment, "tokens": c.tokens, "share": round(c.share, 4)}
                            for c in self.superfluous],
            "tableau": None if tab is None else {
                "ranking": tab.ranking, "rows": tab.to_rows(), "markdown": tab.to_markdown(), "html": tab.to_html(),
                "tie": tab.tie,
            },
            "preferred": self.preferred,
            "stability": self.stability,
            "warnings": self.warnings,
        }


class Analyzer:
    def __init__(self, phone_model: str = DEFAULT_MODEL, hidden_layer: int | None = 12, resources: Path = RESOURCES):
        from .kb.fetch import ensure

        ensure(resources)
        self.phones = PhoneModel(phone_model, hidden_layer=hidden_layer)
        self.lexicons = lexicon.load_default(resources, names=("britfone", "cmudict"))
        self.units = load_units()
        self.typology = load_typology()
        self.calibration = calibration.load()
        self._aligner = None
        self._transcriber = None
        self._diarizer = None
        self._turns = {}
        self._vocabulary = None

    @property
    def aligner(self):
        if self._aligner is None:
            from .align import WordAligner

            self._aligner = WordAligner()
        return self._aligner

    @property
    def transcriber(self):
        if self._transcriber is None:
            from .asr import Transcriber

            self._transcriber = Transcriber()
        return self._transcriber

    @property
    def diarizer(self):
        if self._diarizer is None:
            from .diarize import Diarizer

            self._diarizer = Diarizer()
        return self._diarizer

    def speaker_turns(self, rec: Recording):
        """Who speaks when in a recording with several speakers (None when it is not to be separated)."""
        wanted = rec.diarize if rec.diarize is not None else (rec.transcript.strip().lower() == "auto" and not rec.speaker)
        if not wanted:
            return None
        key = (rec.name, len(rec.audio), rec.num_speakers)
        if key not in self._turns:
            # speech is found from loudness, as in the speaker-separation test (eval/diarize_eval.py); Whisper's
            # word times are looser and let silence into the voice samples
            self._turns[key] = self.diarizer(rec.audio, None, rec.num_speakers)
        return self._turns[key]

    def merger_neighbours(self, canonical: dict, unit: Unit) -> dict[str, str]:
        """Real words a variant pronunciation of each target word sounds like (three [tɹiː] -> 'tree'),
        so ASR transcripts that wrote the variant as another word still yield the token."""
        if self._vocabulary is None:
            self._vocabulary = common_words(20000)
        out = {}
        for word, segs in canonical.items():
            for slot in self.slots(segs, unit):
                for c in unit.candidates:
                    if c in lexicon.same_phoneme(unit.phoneme):
                        continue
                    for lex in self.lexicons.values():
                        for alt in lexicon.same_phoneme(c):
                            form = segs[:slot] + [alt] + segs[slot + 1:]
                            for w in lex.homophones(form, exclude=word):
                                if w not in canonical and (self._vocabulary is None or w in self._vocabulary):
                                    out[w] = word
        return out

    def _evidence(self, audio: np.ndarray, start: float, end: float, context_s: float = 1.0, margin: int = 2) -> Evidence:
        """Phone evidence for one word: the model hears a second of context either side (bounded memory
        on long recordings) and the frames are then cut to the word."""
        lo = max(0, int((start - context_s) * 16000))
        hi = min(len(audio), int((end + context_s) * 16000))
        ev = self.phones.run(audio[lo:hi])
        offset = lo / 16000
        return ev.crop(int((start - offset) * FRAME_RATE) - margin, int(math.ceil((end - offset) * FRAME_RATE)) + margin)

    def pronunciations(self, word: str) -> list[list[str]]:
        for name in ("britfone", "cmudict"):
            lex = self.lexicons.get(name)
            if lex and lex.pronunciations(word):
                return [list(p) for p in lex.pronunciations(word)]
        raise KeyError(f"'{word}' is not in the pronouncing lexicons; give its pronunciation explicitly")

    def canonical(self, word: str, unit: Unit | None = None) -> list[str]:
        """The reference pronunciation; with a unit, the first one containing it (lexicons list weak forms
        such as 'will' [wəl] first)."""
        prons = self.pronunciations(word)
        if unit is not None:
            for p in prons:
                if self.slots(p, unit):
                    return p
        return prons[0]

    def slots(self, segs: list[str], unit: Unit) -> list[int]:
        match = lexicon.same_phoneme(unit.phoneme)
        return [i for i, s in enumerate(segs) if s in match]

    def units_in(self, word: str) -> list[Unit]:
        segs = self.canonical(word)
        return [u for u in self.units.values() if self.slots(segs, u)]

    def _context(self, segs: list[str], slot: int) -> dict[int, list[list[str]]]:
        """Plausible alternative realisations for the other vowels/units of the word, so an accent
        feature elsewhere in the word cannot bias the decision about the slot under study."""
        ctx = {}
        for i, s in enumerate(segs):
            if i == slot:
                continue
            for u in self.units.values():
                if s in lexicon.same_phoneme(u.phoneme):
                    ctx[i] = [[s]] + [[c] for c in u.candidates[:3] if c != s]
                    break
        while math.prod(len(v) for v in ctx.values()) > 64:
            ctx.pop(next(iter(ctx)))
        return ctx

    def _token(self, rec: Recording, word: str, segs: list[str], slot: int, unit: Unit, ev: Evidence,
               start: float, end: float, settings: Settings, speaker: str | None = None) -> tuple[Token, np.ndarray | None]:
        calib = self.calibration.get(unit.key, {}) if settings.calibrated else {}
        scores = classify_slot(self.phones, ev, segs, slot, unit.candidates, context=self._context(segs, slot),
                               temperature=calib.get("temperature", 1.0), offsets=calib.get("offsets"))
        best = scores[0]
        if not math.isfinite(best.nll):
            return None, None
        heard = " ".join(p for p, _, _ in self.phones.greedy(ev))
        emb = None
        if ev.hidden is not None and math.isfinite(best.nll):
            ids = self.phones.to_ids(list(best.segs))
            try:
                spans = self.phones.align(ev, ids)
                # the slot's phones sit after the phones of the segments before it
                before = len(self.phones.to_ids(list(best.segs[:slot])))
                n = len(self.phones.to_ids([best.label]))
                lo, hi = spans[before][0], spans[before + n - 1][1] + 1
                emb = ev.hidden[lo:hi].mean(0)
            except (RuntimeError, IndexError, KeyError):
                emb = None
        tok = Token(rec.name, speaker or rec.speaker or rec.name, word, round(start, 3), round(end, 3), best.label,
                    round(best.posterior, 4), {s.label: round(s.posterior, 4) for s in scores},
                    "".join(best.segs), heard,
                    nll={s.label: (round(s.nll, 4) if math.isfinite(s.nll) else None) for s in scores})
        tok.review = best.posterior < settings.review_below
        return tok, emb

    def analyse(self, recordings: list[Recording], words: list[str], unit_key: str | None = None,
                ranking=DEFAULT_RANKING, settings: Settings | None = None, max_candidates: int = 5) -> Analysis:
        settings = settings or Settings()
        words = [w.lower().strip() for w in words if w.strip()]
        if not words:
            raise ValueError("give at least one target word")
        prons = {w: self.pronunciations(w) for w in words}
        if unit_key:
            if unit_key not in self.units:
                raise ValueError(f"unknown unit {unit_key!r}; choose one of {', '.join(self.units)}")
            unit = self.units[unit_key]
        else:
            shared = [u for u in self.units.values() if all(any(self.slots(p, u) for p in prons[w]) for w in words)]
            if not shared:
                raise ValueError("no unit in the knowledge base occurs in every target word; choose one")
            unit = shared[0]
        canonical = {w: self.canonical(w, unit) for w in words}
        missing = [w for w in words if not self.slots(canonical[w], unit)]
        if missing:
            raise ValueError(f"{unit.label} (/{unit.phoneme}/) does not occur in: {', '.join(missing)}")
        warnings, tokens, embeddings = [], [], []
        unfit = 0
        per_word = Counter()

        def add(tok, emb, low_alignment=False):
            nonlocal unfit
            if tok is None:
                unfit += 1
                return
            tok.review = tok.review or low_alignment
            tokens.append(tok)
            embeddings.append(emb)

        validation = unit.validation or {}
        if validation.get("status") != "validated":
            warnings.append(f"{unit.label}: the variant classifier is not validated for this unit "
                            f"({validation.get('note', 'no human-labelled test yet')}); check tokens by ear before relying on the shares")
        for rec in recordings:
            if not rec.transcript.strip():
                clip, offset = audio_io.trim(rec.audio)
                if len(clip) > settings.max_word_seconds * 16000:
                    warnings.append(f"{rec.name}: {len(clip) / 16000:.0f} s is too long for a single-word recording; "
                                    "give its transcript (or 'auto') so the target words can be located")
                    continue
                word = words[0] if len(words) == 1 else _guess_word(rec.name, words)
                if word is None:
                    warnings.append(f"{rec.name}: several target words given; name the file after its word or add a transcript")
                    continue
                ev = self.phones.run(clip)
                for slot in self.slots(canonical[word], unit):
                    add(*self._token(rec, word, canonical[word], slot, unit, ev, offset, offset + len(clip) / 16000, settings))
                continue
            if rec.transcript.strip().lower() == "auto":
                from .asr import find_targets

                # also search for words a stopped/fronted realisation could be transcribed as (three -> tree)
                aliases = self.merger_neighbours(canonical, unit)
                heard = self.transcriber.words(rec.audio)
                targets = set(canonical) | set(aliases)
                hits = find_targets(rec.audio, heard, targets, self.aligner)
                spans = []
                for h in hits:
                    if h.span.word in aliases:
                        h.span.word = aliases[h.span.word]
                    spans.append(h.span)
                if not spans:
                    found = sum(w.word in targets for w in heard)
                    warnings.append(f"{rec.name}: no target word was heard clearly in the automatic transcript "
                                    f"({len(heard)} words transcribed, {found} of them target words, none kept "
                                    "after re-aligning each one with the audio)")
                    continue
            else:
                spans = [s for s in self.aligner.align(rec.audio, rec.transcript) if s.word in canonical]
                if not spans:
                    warnings.append(f"{rec.name}: none of the target words occur in its transcript")
                    continue
            turns = self.speaker_turns(rec)
            if turns is not None:
                warnings.append(f"{rec.name}: speakers separated automatically ({turns.speakers} found"
                                f"{'' if rec.num_speakers is None else ', as given'}); labels are anonymous")
            if settings.max_tokens_per_word:
                spans = _spread(spans, settings.max_tokens_per_word, per_word)
            for span in spans:
                if settings.max_tokens_per_word and per_word[span.word] >= settings.max_tokens_per_word:
                    continue
                per_word[span.word] += 1
                speaker = None
                if turns is not None:
                    who = turns.speaker_at(span.start, span.end)
                    speaker = f"{rec.speaker or rec.name}:{who or 'unknown'}"
                ev = self._evidence(rec.audio, span.start, span.end)
                for slot in self.slots(canonical[span.word], unit):
                    add(*self._token(rec, span.word, canonical[span.word], slot, unit, ev, span.start, span.end, settings,
                                     speaker), low_alignment=span.score < settings.min_alignment_score)
        if unfit:
            warnings.append(f"{unfit} token(s) dropped: the audio was too short for any candidate pronunciation of the word")
        if not tokens:
            return Analysis(words, unit, {w: "".join(s) for w, s in canonical.items()}, [], None, [], None, [], warnings, None)

        labels = [t.variant for t in tokens]
        emb = np.stack(embeddings) if all(e is not None for e in embeddings) else None
        clustering = two_level(labels, emb)
        for t, p, s in zip(tokens, clustering.primary, clustering.secondary):
            t.primary, t.secondary = p, s

        counts, share = variant_shares(tokens, settings.freq_weighting)
        # candidate forms are shown on the target word with the most tokens
        example_word = Counter(t.word for t in tokens).most_common(1)[0][0]
        example = canonical[example_word]
        slot0 = self.slots(example, unit)[0]
        attested = []
        for seg in sorted(counts, key=lambda s: (-share[s], -counts[s])):
            form = "".join(example[:slot0] + [seg] + example[slot0 + 1:])
            attested.append(Candidate(form, seg, tokens=counts[seg], share=share[seg]))
        if self._vocabulary is None:
            self._vocabulary = common_words(settings.disam_vocabulary)
        assess(attested, unit, words, list(self.lexicons.values()), self.typology, settings, self._vocabulary)
        possible = sorted({lab for t in tokens for lab, p in t.scores.items() if p > 0} - set(counts))
        unseen = [Candidate("".join(example[:slot0] + [seg] + example[slot0 + 1:]), seg) for seg in possible]
        assess(unseen, unit, words, list(self.lexicons.values()), self.typology, settings, self._vocabulary)
        admitted = admit(tokens, attested, settings)
        if not admitted:
            warnings.append(f"no variant reached {settings.min_tokens} tokens from {settings.min_speakers} speakers; "
                            "all attested variants compete")
            admitted = attested
        candidates = admitted[:max_candidates]
        superfluous = [c for c in attested if c not in candidates]
        tableau = evaluate(candidates, ranking, unit=unit.label)
        stability = preferred_stability(tokens, attested + unseen, unit, self.typology, ranking, settings, max_candidates)
        return Analysis(words, unit, {w: "".join(s) for w, s in canonical.items()}, tokens, clustering, candidates,
                        tableau, [c.form for c in tableau.winners], warnings, stability, superfluous)


def _spread(spans: list, cap: int, used: Counter) -> list:
    """Keep at most `cap` spans of each word (fewer if some were used already), evenly spaced through the
    recording, so a capped word samples the whole of a long recording and all its speakers, not its opening."""
    by = defaultdict(list)
    for s in spans:
        by[s.word].append(s)
    keep = set()
    for word, group in by.items():
        room = max(0, cap - used[word])
        if len(group) <= room:
            keep.update(map(id, group))
        elif room:
            keep.update(id(group[round(i * (len(group) - 1) / max(1, room - 1))]) for i in range(room))
    return [s for s in spans if id(s) in keep]


# function words with reduced (weak) forms, or <th> that may be voiced or voiceless: poor evidence for a sound
SURVEY_SKIP = {"the", "a", "an", "to", "of", "and", "or", "her", "were", "with", "within", "without", "was", "for"}


def survey(analyzer: "Analyzer", recordings: list[Recording], ranking=DEFAULT_RANKING, settings: Settings | None = None,
           min_occurrences: int = 3, per_word_cap: int = 40) -> dict[str, Analysis]:
    """Analyse every sound in the knowledge base from the same recordings: for each unit, the target words are
    the words of the transcripts (or of the automatic transcript, cached) that contain that sound."""
    from dataclasses import replace as _replace

    settings = _replace(settings or Settings(), max_tokens_per_word=per_word_cap)
    counts = Counter()
    for rec in recordings:
        t = rec.transcript.strip()
        if t.lower() == "auto":
            counts.update(w.word for w in analyzer.transcriber.words(rec.audio))
        elif t:
            from .align import words_of

            counts.update(words_of(t))
    results = {}
    for key, unit in analyzer.units.items():
        words = []
        for w, n in counts.items():
            if n < min_occurrences or w in SURVEY_SKIP:
                continue
            try:
                prons = analyzer.pronunciations(w)
            except KeyError:
                continue
            if any(analyzer.slots(p, unit) for p in prons):
                words.append(w)
        if not words:
            continue
        results[key] = analyzer.analyse(recordings, sorted(words), key, ranking, settings)
    return results


def admit(tokens: list[Token], attested: list[Candidate], settings: Settings) -> list[Candidate]:
    """Variants compete only when attested often enough (min_tokens from min_speakers), so that a few
    misheard tokens cannot introduce candidates; expert overrides admit a variant regardless."""
    speakers = defaultdict(set)
    for t in tokens:
        speakers[t.variant].add(t.speaker)
    forced = {seg for (seg, _), _ in _expert_overrides(settings)}
    return [c for c in attested
            if c.segment in forced or (c.tokens >= settings.min_tokens and len(speakers[c.segment]) >= settings.min_speakers)]


def variant_shares(tokens: list[Token], weighting: str = "tokens") -> tuple[Counter, dict]:
    """Token counts per variant and each variant's share, either of all tokens or averaged over speakers."""
    counts = Counter(t.variant for t in tokens)
    if weighting == "speakers":
        by = defaultdict(Counter)
        for t in tokens:
            by[t.speaker][t.variant] += 1
        share = {v: sum(c[v] / sum(c.values()) for c in by.values()) / len(by) for v in counts}
    else:
        total = sum(counts.values())
        share = {v: n / total for v, n in counts.items()}
    return counts, share


def _draw(t: Token, rng: random.Random) -> str:
    labels = [l for l, p in t.scores.items() if p > 0]
    if not labels:
        return t.variant
    return rng.choices(labels, weights=[t.scores[l] for l in labels])[0]


def preferred_stability(tokens: list[Token], attested: list[Candidate], unit: Unit, typology: dict, ranking,
                        settings: Settings, max_candidates: int = 5, n: int = 1000, seed: int = 0) -> dict | None:
    """How often each variant is preferred when the speakers are resampled with replacement.
    Each token's label is redrawn from its posterior in every resample. Only FreQ and Ped-C depend on
    the sample; every other mark is fixed per variant."""
    by = defaultdict(list)
    for t in tokens:
        by[t.speaker].append(t)
    speakers = sorted(by)
    if len(speakers) < 3:
        return None
    base = {c.segment: c for c in attested}
    frozen = {(seg, tenet) for (seg, tenet), _ in _expert_overrides(settings)}
    rng = random.Random(seed)
    wins = Counter()
    for _ in range(n):
        drawn = [t for s in rng.choices(speakers, k=len(speakers)) for t in by[s]]
        # each token's variant is drawn from its posterior, so classifier uncertainty is propagated too
        sample = [replace(t, variant=_draw(t, rng)) for t in drawn]
        counts, share = variant_shares(sample, settings.freq_weighting)
        cands = []
        top = max(share.values())
        for seg in sorted(counts, key=lambda s: (-share[s], -counts[s])):
            v = dict(base[seg].violations)
            for tenet, mark in share_dependent(seg, share[seg], counts[seg], unit, typology, settings, top).items():
                if (seg, tenet) not in frozen:
                    v[tenet] = mark
            cands.append(Candidate(base[seg].form, seg, counts[seg], share[seg], v))
        cands = admit(sample, cands, settings)[:max_candidates] or cands[:max_candidates]
        winners = evaluate(cands, ranking).winners
        for w in winners:
            wins[w.segment] += 1 / len(winners)
    return {"resamples": n, "speakers": len(speakers),
            "preferred_rate": {seg: round(k / n, 3) for seg, k in wins.most_common()}}



def _expert_overrides(settings: Settings) -> list:
    return _raw_overrides(settings.overrides)


def _guess_word(name: str, words: list[str]) -> str | None:
    parts = set(re.split(r"[^a-z']+", Path(name).stem.lower()))
    hits = [w for w in words if w in parts]
    return max(hits, key=len) if hits else None
