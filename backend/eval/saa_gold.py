"""Gold evaluation on the Nigerian speakers of the Speech Accent Archive (narrow IPA by trained phoneticians).

Each speaker reads the same paragraph. The transcription is aligned to the paragraph (dynamic programming,
so repeated or skipped words are handled), segments inside each target word are aligned to the reference
pronunciation to read off the realisation of the unit, and the pipeline's own token scorer is run on the
audio. Reports token accuracy per unit and whether operability tables built from the expert labels and from
the automatic labels prefer the same form; writes every token (with raw scores) for calibration.

python -m eval.saa_gold [--calibrated] [--out data/work/saa_rows.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import numpy as np

from pg import audio as audio_io, lexicon
from pg.ot import Candidate, evaluate
from pg.pipeline import Analyzer, Recording
from pg.tenets import Settings, assess

BACKEND = Path(__file__).resolve().parents[1]
SAA = BACKEND / "data" / "resources" / "speech_accent_archive"
PARAGRAPH = ("Please call Stella. Ask her to bring these things with her from the store: Six spoons of fresh snow peas, "
             "five thick slabs of blue cheese, and maybe a snack for her brother Bob. We also need a small plastic snake "
             "and a big toy frog for the kids. She can scoop these things into three red bags, and we will go meet her "
             "Wednesday at the train station.")
PWORDS = re.findall(r"[a-z']+", PARAGRAPH.lower())
UNIT_OF = {
    "things": "TH-voiceless", "thick": "TH-voiceless", "three": "TH-voiceless",
    "these": "TH-voiced", "the": "TH-voiced", "brother": "TH-voiced",
    "her": "NURSE",
    "snow": "GOAT", "go": "GOAT", "also": "GOAT",
    "maybe": "FACE", "snake": "FACE", "train": "FACE", "station": "FACE",
    "bring": "KIT", "six": "KIT", "big": "KIT", "kids": "KIT", "will": "KIT",
    "please": "FLEECE", "cheese": "FLEECE", "peas": "FLEECE", "meet": "FLEECE", "need": "FLEECE", "she": "FLEECE",
    "we": "FLEECE",
}
# gold symbols (broad) and predicted labels map onto comparable classes per unit
CLASS = {
    "TH-voiceless": {"θ": "θ", "t": "t", "s": "s", "f": "f", "d": "d", "ð": "ð", "z": "z"},
    "TH-voiced": {"ð": "ð", "d": "d", "z": "z", "v": "v", "θ": "θ", "t": "t", "s": "z"},
    "NURSE": {"ɜ": "ɜː", "ɜː": "ɜː", "ɝ": "ɜː", "ɚ": "ɜː", "ɛ": "ɛ", "e": "ɛ", "a": "a", "æ": "a", "ɑ": "a", "ɐ": "ə",
              "ɔ": "ɔ", "ɒ": "ɔ", "o": "ɔ", "ə": "ə", "ʌ": "ə"},
    "GOAT": {"əʊ": "əʊ", "oʊ": "əʊ", "ou": "əʊ", "ɔʊ": "əʊ", "o": "o", "ɔ": "ɔ", "ɒ": "ɔ"},
    "FACE": {"eɪ": "eɪ", "ei": "eɪ", "ɛɪ": "eɪ", "e": "e", "ɛ": "ɛ"},
    "KIT": {"ɪ": "ɪ", "i": "i", "iː": "i", "e": "e", "ɛ": "e"},
    "FLEECE": {"i": "iː", "iː": "iː", "ɪ": "ɪ"},
}
DIPHTHONGS = {"oʊ", "əʊ", "ou", "ɔʊ", "eɪ", "ei", "ɛɪ", "aɪ", "ai", "aʊ", "au", "ɔɪ", "oɪ"}
LOOKALIKE = {"ⅼ": "l", "а": "a", "і": "i", "ǝ": "ə", "ʧ": "tʃ", "ʤ": "dʒ", "I": "ɪ", "g": "ɡ", "ɫ": "l", "ε": "ɛ"}
STRIP = set("ːˑʰʲˠ̆ʼ")
VOWELS = set("aeiouæɑɒɔəɛɜɪʊʌɐɚɝœøy")


def clean(text: str) -> list[str]:
    text = "\n".join(l for l in text.splitlines() if "[" in l or not re.search(r"speaker", l, re.I))
    text = unicodedata.normalize("NFD", text)
    for a, b in LOOKALIKE.items():
        text = text.replace(a, b)
    return [w for w in re.sub(r"[\[\]ˈˌ.,]", " ", text).split() if w]


def broad(seg: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", seg) if not unicodedata.combining(c) and c not in STRIP)
    return s.replace("r", "ɹ").replace("ɾ", "ɹ")


def segs_of(word: str) -> list[str]:
    """Segments with diacritics attached; affricates and vowel + offglide diphthongs kept whole."""
    s, out, i = unicodedata.normalize("NFD", word), [], 0
    while i < len(s):
        ch = s[i]
        i += 1
        if ch in ("t", "d") and s[i:i + 1] in ("ʃ", "ʒ"):
            ch += s[i]
            i += 1
        while i < len(s) and (unicodedata.combining(s[i]) or s[i] in STRIP):
            ch += s[i]
            i += 1
        out.append(ch)
    merged, i = [], 0
    while i < len(out):
        if i + 1 < len(out) and broad(out[i]) + broad(out[i + 1]) in DIPHTHONGS:
            merged.append(out[i] + out[i + 1])
            i += 2
        else:
            merged.append(out[i])
            i += 1
    return merged


def seg_cost(a: str, b: str) -> float:
    a, b = broad(a), broad(b)
    if a == b:
        return 0.0
    return 0.6 if (a[:1] in VOWELS) == (b[:1] in VOWELS) else 1.0


def align(xs, ys, cost, gap: float):
    n, m = len(xs), len(ys)
    D = np.zeros((n + 1, m + 1))
    D[:, 0] = np.arange(n + 1) * gap
    D[0, :] = np.arange(m + 1) * gap
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i, j] = min(D[i - 1, j - 1] + cost(xs[i - 1], ys[j - 1]), D[i - 1, j] + gap, D[i, j - 1] + gap)
    pairs, i, j = [], n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and np.isclose(D[i, j], D[i - 1, j - 1] + cost(xs[i - 1], ys[j - 1])):
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i > 0 and np.isclose(D[i, j], D[i - 1, j] + gap):
            pairs.append((i - 1, None))
            i -= 1
        else:
            pairs.append((None, j - 1))
            j -= 1
    return pairs[::-1]


def to_class(unit: str, symbol: str) -> str:
    b = broad(symbol)
    if b[:2] in ("tʃ", "dʒ"):
        return "other"
    for key in (symbol, b, b[:2], b[:1]):
        if key in CLASS[unit]:
            return CLASS[unit][key]
    return "other"


def gold_tokens(an: Analyzer, canon: dict, speaker_file: Path):
    """(orthographic labels of every transcribed word, [(label index, word, unit, gold symbol)])"""
    twords = clean(speaker_file.read_text(encoding="utf-8"))

    def word_cost(pw, tw):
        a, b = canon.get(pw, list(pw)), segs_of(tw)
        pairs = align(a, b, seg_cost, 1.0)
        return sum(seg_cost(a[i], b[j]) if i is not None and j is not None else 1.0 for i, j in pairs) / max(len(a), len(b))

    labels, golds = [], []
    for pi, ti in align(PWORDS, twords, word_cost, 0.9):
        if ti is None:
            continue
        if pi is not None and word_cost(PWORDS[pi], twords[ti]) < 0.75:
            labels.append(PWORDS[pi])
        else:  # repeats take the label of the paragraph word they echo
            best = min(set(PWORDS), key=lambda w: word_cost(w, twords[ti]))
            labels.append(best if word_cost(best, twords[ti]) < 0.5 else None)
        w = labels[-1]
        if w in UNIT_OF:
            unit = an.units[UNIT_OF[w]]
            slot = an.slots(canon[w], unit)[0]
            tsegs = segs_of(twords[ti])
            sp = dict(align(canon[w], tsegs, seg_cost, 1.0))
            golds.append((len(labels) - 1, w, unit.key, tsegs[sp[slot]] if sp.get(slot) is not None else "∅"))
    return labels, golds


def summarise(rows: list[dict], an: Analyzer) -> None:
    for unit_key in CLASS:
        rs = [r for r in rows if r["unit"] == unit_key and r["gold"] != "other"]
        if not rs:
            continue
        acc = np.mean([r["gold"] == r["pred"] for r in rs])
        conf = collections.defaultdict(collections.Counter)
        for r in rs:
            conf[r["gold"]][r["pred"]] += 1
        print(f"\n{unit_key}: {len(rs)} tokens, {len({r['speaker'] for r in rs})} speakers, token accuracy {acc:.1%}")
        for g in sorted(conf, key=lambda k: -sum(conf[k].values())):
            print(f"   gold {g}: {dict(conf[g].most_common())}")
        sure = [r for r in rs if r["posterior"] >= 0.9]
        if sure:
            print(f"   confident (p >= 0.9): {len(sure) / len(rs):.0%} of tokens, accuracy {np.mean([r['gold'] == r['pred'] for r in sure]):.1%}")
        unit = an.units[unit_key]
        words = sorted({r["word"] for r in rs})
        winners = {}
        for source in ("gold", "pred"):
            counts = collections.Counter(r[source] for r in rs)
            total = sum(counts.values())
            cands = [Candidate(seg, seg, n, n / total) for seg, n in counts.most_common(5)]
            assess(cands, unit, words, list(an.lexicons.values()), an.typology, Settings())
            winners[source] = [c.segment for c in evaluate(cands).winners]
            print(f"   {'expert' if source == 'gold' else 'automatic':9s}: "
                  + ", ".join(f"{c.segment} {c.share:.0%}" for c in cands) + f" -> preferred {winners[source]}")
        print(f"   same preferred form: {winners['gold'] == winners['pred']}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--saa", default=str(SAA))
    ap.add_argument("--out", default=str(BACKEND / "data" / "work" / "saa_rows.json"))
    ap.add_argument("--calibrated", action="store_true", help="score with kb/calibration.json (default: raw scores)")
    args = ap.parse_args(argv)
    an = Analyzer()
    settings = Settings(calibrated=args.calibrated)
    canon = {}
    for w in set(PWORDS):
        prons = an.pronunciations(w) if (w in an.lexicons["britfone"] or w in an.lexicons["cmudict"]) else []
        if not prons:
            continue
        unit = an.units[UNIT_OF[w]] if w in UNIT_OF else None
        canon[w] = an.canonical(w, unit)
    rows, t0 = [], time.time()
    saa = Path(args.saa)
    for txt in sorted((saa / "transcription_texts").glob("*.txt")):
        spk = txt.stem
        flac = saa / "flac" / f"{spk}.flac"
        if spk.startswith("krio") or not flac.exists():
            continue
        labels, golds = gold_tokens(an, canon, txt)
        audio = audio_io.load(flac)
        spans = an.aligner.align(audio, " ".join(l for l in labels if l))
        span_of, k = {}, 0
        for li, l in enumerate(labels):
            if l:
                span_of[li] = spans[k] if k < len(spans) else None
                k += 1
        rec = Recording(flac.name, audio, speaker=spk)
        for li, w, unit_key, gseg in golds:
            span = span_of.get(li)
            if span is None:
                continue
            unit = an.units[unit_key]
            ev = an._evidence(audio, span.start, span.end)
            slot = an.slots(canon[w], unit)[0]
            tok, _ = an._token(rec, w, canon[w], slot, unit, ev, span.start, span.end, settings)
            rows.append({"speaker": spk, "word": w, "unit": unit_key, "gold_symbol": gseg, "gold": to_class(unit_key, gseg),
                         "label": tok.variant, "pred": to_class(unit_key, tok.variant), "posterior": tok.posterior,
                         "nll": tok.nll, "heard": tok.heard})
        print(f"{spk}: {sum(r['speaker'] == spk for r in rows)} tokens ({time.time() - t0:.0f}s)", flush=True)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=0), encoding="utf-8")
    summarise(rows, an)
    print("\nrows written to", out)


if __name__ == "__main__":
    sys.exit(main())
