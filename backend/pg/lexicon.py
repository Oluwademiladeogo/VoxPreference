"""Pronouncing lexicons in IPA, used for canonical forms and for Disambiguity (homophones/minimal pairs).

Supports CMUdict (ARPABET, General American), Britfone (RP-like IPA) and open-dict ipa-dict files.
"""
from __future__ import annotations

import csv
import pickle
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ARPABET_TO_IPA = {
    "AA": "ɑ", "AE": "æ", "AH": "ʌ", "AO": "ɔ", "AW": "aʊ", "AY": "aɪ", "EH": "ɛ", "ER": "ɝ", "EY": "eɪ",
    "IH": "ɪ", "IY": "i", "OW": "oʊ", "OY": "ɔɪ", "UH": "ʊ", "UW": "u",
    "B": "b", "CH": "tʃ", "D": "d", "DH": "ð", "F": "f", "G": "ɡ", "HH": "h", "JH": "dʒ", "K": "k", "L": "l",
    "M": "m", "N": "n", "NG": "ŋ", "P": "p", "R": "ɹ", "S": "s", "SH": "ʃ", "T": "t", "TH": "θ", "V": "v",
    "W": "w", "Y": "j", "Z": "z", "ZH": "ʒ",
}
_UNSTRESSED = {"AH": "ə", "ER": "ɚ"}

# multi-character phones, longest first, so IPA strings can be split into segments
MULTI = sorted(
    ["tʃ", "dʒ", "aɪ", "aʊ", "eɪ", "oʊ", "ɔɪ", "əʊ", "ɪə", "eə", "ʊə", "ɛə", "iː", "uː", "ɑː", "ɔː", "ɜː", "ɝ", "ɚ",
     "t̪", "d̪"],
    key=len, reverse=True,
)
_STRIP = re.compile(r"[ˈˌ.\s/\[\]]")
# symbols different lexicons use for the same reference phoneme (Britfone writes modern RP: STRUT ɐ, DRESS ɛ)
EQUIVALENT = {"ɜː": {"ɝ", "ɜ"}, "iː": {"i"}, "uː": {"u"}, "ɔː": {"ɔ"}, "ɑː": {"ɑ"}, "əʊ": {"oʊ"}, "e": {"ɛ"},
              "ɛ": {"e"}, "ʌ": {"ɐ"}, "ɐ": {"ʌ"}, "eə": {"ɛə"}, "ɛə": {"eə"}}


def same_phoneme(a: str) -> set[str]:
    return {a} | EQUIVALENT.get(a, set())


def normalise_ipa(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = s.replace("g", "ɡ").replace("ɫ", "l").replace("r", "ɹ").replace("ʤ", "dʒ").replace("ʧ", "tʃ")
    s = s.replace("ʼ", "").replace("'", "")
    return unicodedata.normalize("NFC", _STRIP.sub("", s))


def segments(ipa: str) -> list[str]:
    """Split an IPA string into phone segments (diphthongs, affricates and length marks kept together)."""
    s = normalise_ipa(ipa)
    out, i = [], 0
    while i < len(s):
        for m in MULTI:
            if s.startswith(m, i):
                out.append(m)
                i += len(m)
                break
        else:
            ch = s[i]
            i += 1
            # attach combining diacritics and length to the previous segment
            while i < len(s) and (unicodedata.combining(s[i]) or s[i] in "ːˑʰʷʲ̃"):
                ch += s[i]
                i += 1
            out.append(ch)
    return out


def arpabet_to_ipa(phones: list[str]) -> list[str]:
    out = []
    for p in phones:
        base, stress = re.match(r"([A-Z]+)(\d?)", p).groups()
        if base in _UNSTRESSED and stress == "0":
            out.append(_UNSTRESSED[base])
        else:
            out.append(ARPABET_TO_IPA[base])
    return out


@dataclass
class Lexicon:
    name: str
    entries: dict[str, list[tuple[str, ...]]] = field(default_factory=lambda: defaultdict(list))

    def add(self, word: str, segs: list[str]):
        word = word.lower()
        segs = tuple(segs)
        prons = self.entries.setdefault(word, [])
        if segs not in prons:
            prons.append(segs)

    def pronunciations(self, word: str) -> list[tuple[str, ...]]:
        return list(self.entries.get(word.lower(), []))

    def __contains__(self, word: str) -> bool:
        return word.lower() in self.entries

    def __len__(self) -> int:
        return len(self.entries)

    def index(self) -> dict[tuple[str, ...], set[str]]:
        """pronunciation -> words, for homophone lookups"""
        if not hasattr(self, "_index"):
            idx = defaultdict(set)
            for w, prons in self.entries.items():
                for p in prons:
                    idx[p].add(w)
            self._index = idx
        return self._index

    def homophones(self, segs, exclude: str = "") -> set[str]:
        return {w for w in self.index().get(tuple(segs), set()) if w != exclude.lower()}

    def merger_pairs(self, a: str, b: str, words=None) -> list[tuple[str, str]]:
        """Word pairs kept apart only by the a/b contrast, i.e. that become homophones if a merges with b."""
        if a == b:
            return []
        idx = self.index()
        pairs = []
        for pron, ws in idx.items():
            if a not in pron:
                continue
            merged = tuple(b if s == a else s for s in pron)
            for w1 in ws:
                if words is not None and w1 not in words:
                    continue
                for w2 in idx.get(merged, ()):
                    if w2 != w1 and (words is None or w2 in words):
                        pairs.append((w1, w2))
        return sorted(set(pairs))


def load_cmudict(path) -> Lexicon:
    lex = Lexicon("cmudict")
    with open(path, encoding="latin-1") as f:
        for line in f:
            if not line.strip() or line.startswith(";;;"):
                continue
            line = line.split("#")[0].strip()
            parts = line.split()
            word = re.sub(r"\(\d+\)$", "", parts[0])
            if not re.match(r"^[a-zA-Z][a-zA-Z'.-]*$", word):
                continue
            try:
                lex.add(word, arpabet_to_ipa(parts[1:]))
            except (AttributeError, KeyError):
                continue
    return lex


def load_britfone(path) -> Lexicon:
    lex = Lexicon("britfone")
    with open(path, encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            word = re.sub(r"\(\d+\)$", "", row[0].strip())
            lex.add(word, segments(row[1]))
    return lex


def load_ipa_dict(path, name="ipa-dict") -> Lexicon:
    lex = Lexicon(name)
    with open(path, encoding="utf-8") as f:
        for line in f:
            if "\t" not in line:
                continue
            word, prons = line.rstrip("\n").split("\t", 1)
            for p in prons.split(","):
                lex.add(word, segments(p))
    return lex


CACHE_VERSION = 2  # bump when segments() or the loaders change, so stale parses are not reused


def _cached(path: Path, loader, *args) -> Lexicon:
    """Parse once, then reuse a pickle next to the source file (rebuilt when the source changes)."""
    cache = path.with_name(f"{path.name}.v{CACHE_VERSION}.pkl")
    if cache.exists() and cache.stat().st_mtime >= path.stat().st_mtime:
        with open(cache, "rb") as f:
            return pickle.load(f)
    lex = loader(path, *args)
    lex.entries = dict(lex.entries)
    try:
        with open(cache, "wb") as f:
            pickle.dump(lex, f)
    except OSError:
        pass
    return lex


def load_default(resources: Path, names=("cmudict", "britfone", "ipa-dict-en_US", "ipa-dict-en_UK")) -> dict[str, Lexicon]:
    """Load the lexicons present under backend/data/resources/lexicons."""
    d = Path(resources) / "lexicons"
    found = {}
    for p in sorted(d.rglob("cmudict*")):
        if p.suffix in (".dict", ".txt") or p.name.endswith("0.7b"):
            found["cmudict"] = (p, load_cmudict)
            break
    for p in sorted(d.rglob("britfone.main*.csv")):
        found["britfone"] = (p, load_britfone)
        break
    for tag in ("en_US", "en_UK"):
        for p in sorted(d.rglob(f"*{tag}*.txt")):
            found[f"ipa-dict-{tag}"] = (p, lambda path, t=tag: load_ipa_dict(path, f"ipa-dict-{t}"))
            break
    return {name: _cached(*found[name]) for name in names if name in found}
