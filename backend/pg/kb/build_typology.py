"""Rebuild typology.json from PHOIBLE (python -m pg.kb.build_typology).

world_frequency: share of the world's languages whose inventory has the segment (exact match,
non-marginal phonemes, each language weighted equally across its inventories).
substrate: share of each Nigerian substrate language's PHOIBLE inventories that have the segment
(broad match, so dental t̪ counts as t and length is ignored).
"""
from __future__ import annotations

import csv
import json
import unicodedata
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PHOIBLE = HERE.parents[1] / "data" / "resources" / "phoible" / "phoible.csv"
SUBSTRATE = {"Hausa": "haus1257", "Igbo": "nucl1417", "Yoruba": "yoru1245"}

SEGMENTS = ["p", "b", "t", "d", "t̪", "d̪", "k", "ɡ", "f", "v", "θ", "ð", "s", "z", "ʃ", "ʒ", "h", "tʃ", "dʒ", "m", "n",
            "ŋ", "l", "ɹ", "r", "w", "j", "ɸ", "kp", "ɡb",
            "i", "ɪ", "e", "ɛ", "æ", "a", "ɑ", "ɒ", "ɔ", "o", "ʊ", "u", "ʌ", "ɐ", "ə", "ɜ", "ɚ", "ɝ",
            "iː", "uː", "ɑː", "ɔː", "ɜː", "eɪ", "aɪ", "ɔɪ", "əʊ", "oʊ", "aʊ", "ɪə", "eə", "ɛə", "ʊə"]
# PHOIBLE spells some segments differently
PHOIBLE_FORM = {"tʃ": "t̠ʃ", "dʒ": "d̠ʒ", "ɡb": "ɡb", "kp": "kp"}

REFERENCE = {
    "about": "RP reference phonemes (Britfone symbols) used to decide whether a variant merges with another phoneme.",
    "consonants": ["p", "b", "t", "d", "k", "ɡ", "f", "v", "θ", "ð", "s", "z", "ʃ", "ʒ", "h", "tʃ", "dʒ", "m", "n", "ŋ",
                   "l", "ɹ", "w", "j"],
    "short_vowels": ["ɪ", "ɛ", "æ", "ɐ", "ɒ", "ʊ", "ə"],
    "long_vowels": ["iː", "ɑː", "ɔː", "uː", "ɜː"],
    "diphthongs": ["eɪ", "aɪ", "ɔɪ", "əʊ", "aʊ", "ɪə", "ɛə", "ʊə"],
    # phonetic symbols a recogniser or transcriber may use, mapped to the RP phoneme they would merge with;
    # Nigerian monophthongs [e] and [o] are absent on purpose: they are not RP phonemes, so they merge with nothing
    "maps_to": {"t̪": "t", "d̪": "d", "r": "ɹ", "ɾ": "ɹ", "g": "ɡ", "ʌ": "ɐ", "a": "æ", "ɔ": "ɒ", "ɑ": "ɑː", "i": "iː",
                "u": "uː", "ɜ": "ɜː", "ɝ": "ɜː", "ɚ": "ɜː", "əː": "ɜː", "oʊ": "əʊ", "eə": "ɛə", "e": None, "o": None},
    "core_note": "Lingua Franca Core (Jenkins 2000; Walker 2010): consonant contrasts are core except those involving θ and ð; "
                 "vowel quantity (long or diphthong vs short) is core; vowel quality is not, except the NURSE vowel.",
}


def _norm(s: str) -> str:
    return unicodedata.normalize("NFC", s.replace("g", "ɡ"))


def _broad(s: str) -> str:
    s = unicodedata.normalize("NFD", s).replace("t̠ʃ", "tʃ").replace("d̠ʒ", "dʒ")
    s = "".join(c for c in s if not unicodedata.combining(c) and c not in "ːˑʰʲʷʼ")
    return unicodedata.normalize("NFC", s.replace("g", "ɡ"))


def build(phoible: Path = PHOIBLE) -> dict:
    inv_segs, inv_lang = defaultdict(set), {}
    with open(phoible, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["Marginal"] == "TRUE" or not row["Glottocode"] or row["Glottocode"] == "NA":
                continue
            inv = row["InventoryID"]
            inv_lang[inv] = row["Glottocode"]
            for alt in row["Phoneme"].split("|"):  # UPSID writes place-ambiguous phonemes as t̪|t
                inv_segs[inv].add(_norm(alt))
    by_lang = defaultdict(list)
    for inv, lang in inv_lang.items():
        by_lang[lang].append(inv_segs[inv])
    world = {}
    for seg in SEGMENTS:
        form = _norm(PHOIBLE_FORM.get(seg, seg))
        share = sum(sum(form in s for s in invs) / len(invs) for invs in by_lang.values()) / len(by_lang)
        world[seg] = round(share, 4)
    substrate = {}
    for name, glotto in SUBSTRATE.items():
        invs = [{_broad(x) for x in s} for s in by_lang.get(glotto, [])]
        substrate[name] = {seg: round(sum(_broad(seg) in s for s in invs) / len(invs), 3) if invs else None for seg in SEGMENTS}
    return {
        "source": {
            "phoible": "PHOIBLE 2.0 (Moran & McCloy eds., doi:10.5281/zenodo.2626687), data CC BY 4.0, file backend/data/resources/phoible/phoible.csv",
            "languages_counted": len(by_lang),
            "substrate_glottocodes": SUBSTRATE,
        },
        "world_frequency": world,
        "substrate": substrate,
        "reference": REFERENCE,
    }


if __name__ == "__main__":
    out = build()
    (HERE / "typology.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    w = out["world_frequency"]
    print({k: w[k] for k in ("θ", "ð", "t", "t̪", "s", "z", "f", "ɪ", "ɜ", "əʊ", "o", "ɔ")})
    for lang, pres in out["substrate"].items():
        print(lang, {k: pres[k] for k in ("θ", "t", "s", "z", "f", "v", "ɔ", "o", "ɪ", "əʊ")})
