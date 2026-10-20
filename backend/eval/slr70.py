"""Prepare SLR70 (Google's crowdsourced Nigerian English, CC BY-SA 4.0) inputs for PG analyses.

Downloads the transcript lists, picks utterances that contain words of each unit (capped per word), fetches
only those WAVs from the remote zips with HTTP range requests, and writes words/files/transcripts/speakers
lists per unit under data/work/slr70/inputs/<unit>/.

python -m eval.slr70 [--units TH-voiceless,TH-voiced,NURSE] [--cap 200]
"""
from __future__ import annotations

import argparse
import collections
import os
import re
import urllib.request
from pathlib import Path

from pg import lexicon
from pg.pipeline import RESOURCES
from pg.tenets import load_units

WORK = Path(__file__).resolve().parents[1] / "data" / "work" / "slr70"
MIRROR = "https://openslr.elda.org/resources/70"
WEAK = {"the", "her", "were", "per", "with", "within", "without"}  # reduced forms, or <th> that may be voiced or not


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", default="TH-voiceless,TH-voiced,NURSE")
    ap.add_argument("--cap", type=int, default=200, help="max utterances per word (common words like 'that' are capped)")
    ap.add_argument("--min-tokens", type=int, default=5)
    args = ap.parse_args(argv)
    WORK.mkdir(parents=True, exist_ok=True)
    text = {}
    for g in ("male", "female"):
        tsv = WORK / f"line_index_{g}.tsv"
        if not tsv.exists():
            urllib.request.urlretrieve(f"{MIRROR}/line_index_{g}.tsv", tsv)
        for line in tsv.read_text(encoding="utf-8").splitlines():
            fid, t = line.split("\t", 1)
            text[fid] = t
    lexs = lexicon.load_default(RESOURCES, names=("britfone", "cmudict"))
    units = load_units()
    keep = set()
    for key in args.units.split(","):
        unit = units[key]
        symbols = lexicon.same_phoneme(unit.phoneme)
        chosen = collections.defaultdict(list)
        for fid, t in text.items():
            for w in set(re.findall(r"[a-z']+", t.lower().replace("’", "'"))):
                if w in WEAK or len(chosen[w]) >= args.cap:
                    continue
                prons = lexs["britfone"].pronunciations(w) or lexs["cmudict"].pronunciations(w)
                if prons and any(s in symbols for p in prons for s in p):
                    chosen[w].append(fid)
        chosen = {w: ids for w, ids in chosen.items() if len(ids) >= args.min_tokens}
        fids = sorted({f for ids in chosen.values() for f in ids})
        keep |= set(fids)
        d = WORK / "inputs" / key
        d.mkdir(parents=True, exist_ok=True)
        (d / "words.txt").write_text(",".join(sorted(chosen)))
        (d / "files.txt").write_text("\n".join(str(WORK / "wav" / f"{f}.wav") for f in fids))
        (d / "transcripts.tsv").write_text("\n".join(f"{f}.wav\t{text[f]}" for f in fids))
        (d / "speakers.tsv").write_text("\n".join(f"{f}.wav\t{'_'.join(f.split('_')[:2])}" for f in fids))
        print(f"{key}: {len(chosen)} words, {sum(len(v) for v in chosen.values())} word tokens, {len(fids)} utterances")
    from remotezip import RemoteZip

    (WORK / "wav").mkdir(exist_ok=True)
    got = 0
    for z in ("en_ng_male.zip", "en_ng_female.zip"):
        with RemoteZip(f"{MIRROR}/{z}") as rz:
            for info in rz.infolist():
                stem = os.path.splitext(os.path.basename(info.filename))[0]
                dest = WORK / "wav" / f"{stem}.wav"
                if stem in keep and not dest.exists():
                    with rz.open(info) as src, open(dest, "wb") as out:
                        out.write(src.read())
                    got += 1
    print(f"fetched {got} new clips; {len(list((WORK / 'wav').glob('*.wav')))} in {WORK / 'wav'}")


if __name__ == "__main__":
    main()
