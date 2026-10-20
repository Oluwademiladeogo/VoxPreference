"""Download the Nigerian/West African subset of the Speech Accent Archive used by eval/saa_gold.py.

Source: Weinberger, S. (2015). Speech Accent Archive, George Mason University; audio and IPA transcriptions on OSF
(https://osf.io/yh23d, https://osf.io/e2j5y), licence CC BY-NC-SA 4.0. The file list is eval/saa_west_african_subset.tsv.

python -m eval.fetch_saa
"""
from __future__ import annotations

import csv
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEST = HERE.parent / "data" / "resources" / "speech_accent_archive"


def main():
    with open(HERE / "saa_west_african_subset.tsv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    for sub in ("flac", "transcription_texts"):
        (DEST / sub).mkdir(parents=True, exist_ok=True)
    got = 0
    for r in rows:
        for url, path in ((r.get("flac_url"), DEST / "flac" / f"{r['sample']}.flac"),
                          (r.get("txt_url") if r.get("has_text_ipa") == "True" else None,
                           DEST / "transcription_texts" / f"{r['sample']}.txt")):
            if url and not path.exists():
                urllib.request.urlretrieve(url, path)
                got += 1
    print(f"downloaded {got} files into {DEST}")


if __name__ == "__main__":
    main()
