"""Assign Preference Grammar violation marks to candidates.

The PG sources assign marks by analyst judgement and give no algorithm. The rules below are a
documented operationalisation that reproduces, mark for mark, both evaluations Ugorji published:
<th> in 'think' (Ugorji 2010: 58) and the GOAT vowel (reported by Jowitt 2015: 8). Every mark
records the evidence it rests on, and PG experts can override any of them (Settings.overrides).

I-Ac   the variant is outside the internationally accepted realisations of the unit (knowledge base:
       RP/GA, established L1-variety norms, Lingua Franca Core, ICAO).
ContR  the variant neutralises a contrast crucial to international intelligibility (LFC core:
       consonant contrasts except those of θ/ð; vowel length; the NURSE quality).
FreQ   the variant's share of the attested tokens is below freq_threshold.
DisaM  the variant merges the unit with another reference phoneme and so makes common words
       sound alike (homophones of the target word, or minimal pairs lost across the lexicon).
Pho-S  the variant is absent from most Nigerian substrate languages (Hausa, Igbo, Yoruba) or rare
       in the world's languages (PHOIBLE).
Ped-C  the variant is absent from the substrate languages and rarely used by the speakers analysed,
       so there is no local model to teach from; or PG experts list it as difficult.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .lexicon import Lexicon, same_phoneme
from .ot import Candidate, Violation, parse_ranking

KB_DIR = Path(__file__).resolve().parent / "kb"
NURSE_QUALITIES = {"ɜː", "ɜ", "ɝ", "ɚ", "əː"}


@dataclass
class Unit:
    key: str
    label: str  # as shown in the operability table, e.g. "<th>"
    phoneme: str  # the reference (RP) segment, e.g. "θ"
    candidates: list[str]  # realisations to test for in the audio
    international: list[str]  # realisations within international norms (I-Ac)
    pedagogic_difficult: list[str] = field(default_factory=list)  # Ped-C, as judged by experts
    lexical_set: str = ""
    notes: str = ""
    sources: list[str] = field(default_factory=list)
    validation: dict = field(default_factory=dict)  # result of the human-labelled test of the classifier


@dataclass
class Settings:
    freq_threshold: float = 0.2  # *No FreQ below this share of the attested tokens
    freq_weighting: str = "tokens"  # "tokens", or "speakers" so that every speaker counts equally
    # "threshold": *No FreQ below freq_threshold (reproduces Ugorji's published tables);
    # "most_frequent": every variant but the most frequent gets *No FreQ, so ranking FreQ first picks the commonest form
    freq_mode: str = "threshold"
    disam_min_pairs: int = 1  # DisaM when a merger loses at least this many minimal pairs...
    disam_vocabulary: int = 20000  # ...among the most frequent words of English
    phos_world_threshold: float = 0.15  # *Pho-S when fewer than this share of the world's languages have the segment
    substrate_languages: tuple = ("Hausa", "Igbo", "Yoruba")
    substrate_absent_min: int = 2  # *Pho-S when absent from at least this many substrate languages
    pedc_share_threshold: float = 0.2  # *Ped-C when substrate-absent and used by fewer than this share
    min_tokens: int = 3  # a variant needs this many tokens...
    min_speakers: int = 2  # ...from this many speakers to compete; rarer ones are listed as superfluous
    review_below: float = 0.75  # flag tokens whose variant posterior is below this for human review
    min_alignment_score: float = 0.2  # flag tokens whose word alignment is this unsure
    max_tokens_per_word: int = 0  # 0 = no cap; a survey caps very common words so they do not swamp a sound
    max_word_seconds: float = 10.0  # longer recordings without a transcript are rejected, not scored whole
    calibrated: bool = True  # apply kb/calibration.json (bias correction fitted on human-labelled tokens)
    overrides: dict = field(default_factory=dict)  # {"segment|tenet": count} set by PG experts


def settings_from(raw: dict | None) -> Settings:
    """Settings from a JSON object, rejecting unknown names with a clear message."""
    raw = dict(raw or {})
    known = set(Settings.__dataclass_fields__)
    unknown = sorted(set(raw) - known)
    if unknown:
        raise ValueError(f"unknown setting(s) {', '.join(unknown)}; valid settings: {', '.join(sorted(known))}")
    if "substrate_languages" in raw:
        raw["substrate_languages"] = tuple(raw["substrate_languages"])
    return Settings(**raw)


def load_units(path: Path = KB_DIR / "units.json") -> dict[str, Unit]:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return {k: Unit(key=k, **v) for k, v in raw["units"].items()}


def load_typology(path: Path = KB_DIR / "typology.json") -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def common_words(n: int) -> set[str] | None:
    try:
        from wordfreq import top_n_list
    except ImportError:
        return None
    return set(top_n_list("en", n))


def reference_phoneme(seg: str, typology: dict) -> str | None:
    """The RP phoneme a realisation would merge with, or None when it is not an RP phoneme (e.g. [o], [e])."""
    ref = typology["reference"]
    inventory = set(ref["consonants"] + ref["short_vowels"] + ref["long_vowels"] + ref["diphthongs"])
    if seg in inventory:
        return seg
    if seg in ref["maps_to"]:
        return ref["maps_to"][seg]
    for alt in same_phoneme(seg):
        if alt in inventory:
            return alt
    return None


def _is_long(ph: str, typology: dict) -> bool:
    ref = typology["reference"]
    return ph in ref["long_vowels"] or ph in ref["diphthongs"]


def _substrate_absent(seg: str, typology: dict, settings: Settings) -> list[str]:
    out = []
    for lang in settings.substrate_languages:
        share = typology["substrate"].get(lang, {}).get(seg)
        if share is None or share <= 0.5:
            out.append(lang)
    return out


def assess(candidates: list[Candidate], unit: Unit, words, lexicons: list[Lexicon], typology: dict,
           settings: Settings | None = None, vocabulary: set[str] | None = None) -> list[Candidate]:
    """Fill in candidate.violations for all six tenets. words: the target word(s) the unit was studied in."""
    settings = settings or Settings()
    words = [words] if isinstance(words, str) else list(words)
    vocabulary = vocabulary if vocabulary is not None else common_words(settings.disam_vocabulary)
    target = reference_phoneme(unit.phoneme, typology) or unit.phoneme
    top_share = max((c.share for c in candidates), default=0.0)
    for c in candidates:
        seg, v = c.segment, c.violations
        v["I-Ac"] = _international(seg, unit)
        v["ContR"] = _contrastiveness(seg, unit, target, typology)
        v["DisaM"] = _disambiguity(seg, unit, target, words, lexicons, vocabulary, typology, settings)
        v["Pho-S"] = _simplicity(seg, typology, settings)
        v.update(share_dependent(seg, c.share, c.tokens, unit, typology, settings, top_share))
        for (o_seg, tenet), count in _overrides(settings.overrides):
            if o_seg == seg:
                v[tenet] = Violation(int(count), "set by PG experts", "expert")
    return candidates


def share_dependent(seg: str, share: float, tokens: int, unit: Unit, typology: dict, settings: Settings,
                    top_share: float | None = None) -> dict:
    """The two marks that depend on how often the variant was used: FreQ and Ped-C.
    top_share is the share of the most frequent competing variant (for freq_mode "most_frequent")."""
    basis = "of speakers' usage" if settings.freq_weighting == "speakers" else "of tokens"
    if settings.freq_mode == "most_frequent":
        top = share if top_share is None else top_share
        if share >= top - 1e-9:
            freq = Violation(0, f"the most frequent variant: {share:.0%} {basis} ({tokens} tokens)", "data")
        else:
            freq = Violation(1, f"{share:.0%} {basis} ({tokens} tokens), less than the most frequent variant's {top:.0%}", "data")
    elif share >= settings.freq_threshold:
        freq = Violation(0, f"{share:.0%} {basis} ({tokens} tokens)", "data")
    else:
        freq = Violation(1, f"only {share:.0%} {basis} ({tokens} tokens); threshold {settings.freq_threshold:.0%}", "data")
    absent = _substrate_absent(seg, typology, settings)
    if seg in unit.pedagogic_difficult:
        pedc = Violation(1, f"[{seg}] is listed by PG experts as difficult to teach for /{unit.phoneme}/", "knowledge base")
    elif len(absent) >= settings.substrate_absent_min and share < settings.pedc_share_threshold:
        pedc = Violation(1, f"[{seg}] is absent from {', '.join(absent)} and used in only {share:.0%} {basis}, "
                            "so learners have no local model", "typology (PHOIBLE) + data")
    elif len(absent) >= settings.substrate_absent_min:
        pedc = Violation(0, f"absent from {', '.join(absent)}, but used in {share:.0%} {basis}, so locally teachable",
                         "typology (PHOIBLE) + data")
    else:
        pedc = Violation(0, f"[{seg}] exists in the substrate languages", "typology (PHOIBLE)")
    return {"FreQ": freq, "Ped-C": pedc}


def _international(seg: str, unit: Unit) -> Violation:
    accepted = ", ".join(f"[{s}]" for s in unit.international)
    if seg in unit.international:
        return Violation(0, f"[{seg}] is an internationally accepted realisation of /{unit.phoneme}/ ({accepted})", "knowledge base")
    return Violation(1, f"[{seg}] is outside the international norms for /{unit.phoneme}/ ({accepted})", "knowledge base")


def _contrastiveness(seg: str, unit: Unit, target: str, typology: dict) -> Violation:
    ref = reference_phoneme(seg, typology)
    cons = typology["reference"]["consonants"]
    src = "Lingua Franca Core"
    if seg in same_phoneme(unit.phoneme) or ref == target:
        return Violation(0, f"realises /{unit.phoneme}/ itself", src)
    if target in cons:
        if target in ("θ", "ð"):
            return Violation(0, f"contrasts of /{target}/ are not core to international intelligibility", src)
        if ref in cons:
            return Violation(1, f"merges /{target}/ with /{ref}/, a core consonant contrast", src)
        return Violation(0, f"[{seg}] merges with no reference consonant", src)
    if unit.lexical_set == "NURSE" or target == "ɜː":
        if seg in NURSE_QUALITIES:
            return Violation(0, "keeps the NURSE quality", src)
        return Violation(1, "the NURSE vowel quality is core to international intelligibility", src)
    if ref is None:
        return Violation(0, f"[{seg}] is not an RP phoneme, so it neutralises no contrast", src)
    if _is_long(target, typology) != _is_long(ref, typology):
        return Violation(1, f"neutralises the vowel-length contrast between /{target}/ and /{ref}/", src)
    return Violation(0, f"/{target}/~/{ref}/ is a vowel-quality contrast, not core", src)


def _disambiguity(seg: str, unit: Unit, target: str, words: list[str], lexicons: list[Lexicon], vocabulary,
                  typology: dict, settings: Settings) -> Violation:
    ref = reference_phoneme(seg, typology)
    if seg in same_phoneme(unit.phoneme) or ref == target:
        return Violation(0, f"keeps /{unit.phoneme}/ distinct", "lexicon")
    if ref is None:
        return Violation(0, f"[{seg}] is not an RP phoneme, so it creates no homophones", "lexicon")
    targets, refs = same_phoneme(target) | same_phoneme(unit.phoneme), same_phoneme(ref)
    homophones, pairs = {}, set()
    for lex in lexicons:
        for word in words:
            for pron in lex.pronunciations(word):
                for r in refs:
                    form = tuple(r if s in targets else s for s in pron)
                    same = {w for w in lex.homophones(form, exclude=word) if vocabulary is None or w in vocabulary}
                    if same:
                        homophones.setdefault(word, set()).update(same)
        for t in targets:
            for r in refs:
                pairs |= set(lex.merger_pairs(t, r, words=vocabulary))
    if homophones:
        clash = "; ".join(f"'{w}' would sound like {', '.join(sorted(h)[:4])}" for w, h in homophones.items())
        return Violation(1, clash, "lexicon")
    if len(pairs) >= settings.disam_min_pairs:
        examples = ", ".join(f"{a}/{b}" for a, b in sorted(pairs)[:4])
        return Violation(1, f"merging /{target}/ with /{ref}/ makes {len(pairs)} common word pairs sound alike (e.g. {examples})", "lexicon")
    return Violation(0, f"no common words would be confused (/{target}/~/{ref}/)", "lexicon")


def _simplicity(seg: str, typology: dict, settings: Settings) -> Violation:
    absent = _substrate_absent(seg, typology, settings)
    world = typology["world_frequency"].get(seg)
    src = "typology (PHOIBLE)"
    if len(absent) >= settings.substrate_absent_min:
        return Violation(1, f"[{seg}] is absent from {', '.join(absent)}", src)
    if world is not None and world < settings.phos_world_threshold:
        return Violation(1, f"[{seg}] occurs in only {world:.0%} of the world's languages", src)
    world_txt = "" if world is None else f"; in {world:.0%} of the world's languages"
    return Violation(0, f"[{seg}] exists in most substrate languages{world_txt}", src)


def _overrides(raw) -> list:
    """Accept {(segment, tenet): n}, {"segment|tenet": n} (JSON-friendly) or [{"segment", "tenet", "count"}]."""
    items = []
    if isinstance(raw, dict):
        for k, n in raw.items():
            seg, tenet = k if isinstance(k, tuple) else k.split("|", 1)
            items.append(((seg, tenet), n))
    else:
        items = [((o["segment"], o["tenet"]), o.get("count", 1)) for o in raw or []]
    return [((seg, parse_ranking(tenet)[0][0]), n) for (seg, tenet), n in items]


def tiers(tableau) -> dict[str, str]:
    """Output classes (after Benjamin-Ohwodede & Osewa 2023): the winner is the formal standard; a loser that
    satisfies I-Ac and ContR is an allophone within the formal inventory; other losers belong to the outer norm."""
    out = {}
    for c in tableau.candidates:
        if c in tableau.winners:
            out[c.segment] = "preferred (formal standard)"
        elif c.marks("I-Ac") == 0 and c.marks("ContR") == 0:
            out[c.segment] = "allophone (formal inventory)"
        else:
            out[c.segment] = "outer (informal) norm"
    return out
