"""Reproduce the findings about the final-year-project speech-to-text model, from public files only.

    python -m eval.fyp_audit            # training logs, labels and split (a few seconds)
    python -m eval.fyp_audit --wer      # also the stock model's word error rate on the original split (minutes)
    python -m eval.fyp_audit --weights  # also compare every weight with the stock model (downloads 378 MB)

1. Training logs: the TensorBoard event files published with thebickersteth/wav2vec2-nigerian-english on
   Hugging Face, read without TensorFlow. They show the loss, gradient norm and learning rate of every logged step.
2. Labels: the original script (commit e72090d) lowercased the transcripts; the stock tokenizer has only
   upper-case letters, so every letter becomes <unk>. Counted on the training half of the original split.
3. Split: the original 90/10 split (sklearn, random_state=42) re-run on the SLR70 line index; speakers and
   sentences shared between training and validation are counted.
4. --wer: facebook/wav2vec2-base-960h, unchanged, on that validation split, scored like the thesis (WER, S/D/I).
5. --weights: every tensor of the published fine-tune compared with the stock model.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import struct
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLR70 = ROOT / "data" / "work" / "slr70"
FINETUNE = "thebickersteth/wav2vec2-nigerian-english"
STOCK = "facebook/wav2vec2-base-960h"


# ---- a minimal TensorBoard event reader (TFRecord framing + the few protobuf fields we need) ----
def _varint(b: bytes, i: int) -> tuple[int, int]:
    shift = out = 0
    while True:
        c = b[i]
        i += 1
        out |= (c & 0x7F) << shift
        if c < 0x80:
            return out, i
        shift += 7


def _fields(b: bytes):
    i = 0
    while i < len(b):
        key, i = _varint(b, i)
        num, wire = key >> 3, key & 7
        if wire == 0:
            v, i = _varint(b, i)
        elif wire == 1:
            v, i = b[i:i + 8], i + 8
        elif wire == 2:
            n, i = _varint(b, i)
            v, i = b[i:i + n], i + n
        elif wire == 5:
            v, i = b[i:i + 4], i + 4
        else:
            raise ValueError(f"unsupported wire type {wire}")
        yield num, wire, v


def read_scalars(path: Path) -> dict[str, list[tuple[int, float]]]:
    data, out, i = path.read_bytes(), defaultdict(list), 0
    while i + 12 <= len(data):
        (n,) = struct.unpack("<Q", data[i:i + 8])
        record = data[i + 12:i + 12 + n]
        i += 12 + n + 4
        step = 0
        for num, _, v in _fields(record):
            if num == 2:
                step = v
            elif num == 5:  # Summary
                for snum, _, sv in _fields(v):
                    if snum != 1:  # Value
                        continue
                    tag, val = None, None
                    for vnum, vwire, vv in _fields(sv):
                        if vnum == 1:
                            tag = vv.decode()
                        elif vnum == 2 and vwire == 5:
                            (val,) = struct.unpack("<f", vv)
                        elif vnum == 8:  # TensorProto: float_val (5, packed) or tensor_content (4)
                            for tnum, twire, tv in _fields(vv):
                                if tnum == 5 and twire == 2 and len(tv) >= 4:
                                    (val,) = struct.unpack("<f", tv[:4])
                                elif tnum == 5 and twire == 5:
                                    (val,) = struct.unpack("<f", tv)
                                elif tnum == 4 and len(tv) >= 4:
                                    (val,) = struct.unpack("<f", tv[:4])
                    if tag is not None and val is not None:
                        out[tag].append((step, val))
    return out


def training_logs() -> dict:
    from huggingface_hub import HfApi, hf_hub_download

    files = [f for f in HfApi().list_repo_files(FINETUNE) if "tfevents" in f]
    scalars = defaultdict(list)
    for f in files:
        for tag, pts in read_scalars(Path(hf_hub_download(FINETUNE, f))).items():
            scalars[tag] += pts
    summary = {}
    for tag, pts in sorted(scalars.items()):
        vals = [v for _, v in pts]
        summary[tag] = {"points": len(vals), "steps": [pts[0][0], pts[-1][0]],
                        "nan": sum(math.isnan(v) for v in vals),
                        "distinct": sorted({round(v, 6) for v in vals if not math.isnan(v)})[:5]}
    return {"files": files, "scalars": summary}


# ---- labels and split ----
def slr70_index():
    import pandas as pd

    frames = [pd.read_csv(SLR70 / f"line_index_{g}.tsv", sep="\t", names=["path", "transcript"])
              for g in ("male", "female")]
    return pd.concat(frames, ignore_index=True)


def original_clean(text: str) -> str:  # finetune_model.py at commit e72090d
    return re.sub(r"[^a-zA-Z' ]+", "", text.lower()).strip()


def labels() -> dict:
    from transformers import Wav2Vec2Processor

    tok = Wav2Vec2Processor.from_pretrained(STOCK).tokenizer
    train, _ = original_split()
    ids = Counter()
    for t in train["transcript"]:
        ids.update(tok(original_clean(t)).input_ids)
    unk, delim = tok.unk_token_id, tok.convert_tokens_to_ids("|")
    letters = sum(n for i, n in ids.items() if tok.convert_ids_to_tokens(i).isalpha())
    return {"training_utterances": len(train), "unk_tokens": ids[unk], "letter_tokens": letters,
            "word_delimiters": ids[delim], "vocabulary_letters_are_upper_case": all(
                k.isupper() for k in tok.get_vocab() if len(k) == 1 and k.isalpha())}


def original_split():
    from sklearn.model_selection import train_test_split

    df = slr70_index()
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)  # as in split_shuffle_data.py at e72090d
    train, val = train_test_split(df, test_size=0.1, random_state=42)
    for d in (train, val):
        d["speaker"] = d["path"].str.split("_").str[:2].str.join("_")
    return train, val


def split() -> dict:
    train, val = original_split()
    shared = set(train["speaker"]) & set(val["speaker"])
    in_train = val["transcript"].isin(set(train["transcript"]))
    return {"train": len(train), "validation": len(val), "speakers": int(train["speaker"].nunique()),
            "speakers_in_both": len(shared), "validation_sentences_also_in_training": int(in_train.sum())}


def fetch_wavs(stems: set[str]) -> None:
    """Fetch only the missing clips from the SLR70 zips (HTTP range requests), as eval/slr70.py does."""
    import os

    from remotezip import RemoteZip

    from eval.slr70 import MIRROR

    dest_dir = SLR70 / "wav"
    dest_dir.mkdir(parents=True, exist_ok=True)
    missing = {s for s in stems if not (dest_dir / f"{s}.wav").exists()}
    for z in ("en_ng_male.zip", "en_ng_female.zip"):
        if not missing:
            break
        with RemoteZip(f"{MIRROR}/{z}") as rz:
            for info in rz.infolist():
                stem = os.path.splitext(os.path.basename(info.filename))[0]
                if stem in missing:
                    with rz.open(info) as src, open(dest_dir / f"{stem}.wav", "wb") as out:
                        out.write(src.read())
                    missing.discard(stem)


def wer() -> dict:
    import jiwer
    import torch
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

    from pg.audio import load

    _, val = original_split()
    fetch_wavs(set(val["path"]))
    proc, model = Wav2Vec2Processor.from_pretrained(STOCK), Wav2Vec2ForCTC.from_pretrained(STOCK).eval()
    refs, hyps = [], []
    for _, row in val.iterrows():
        wav = SLR70 / "wav" / f"{row['path']}.wav"
        if not wav.exists():
            continue
        x = proc(load(wav), sampling_rate=16000, return_tensors="pt").input_values
        with torch.inference_mode():
            ids = model(x).logits.argmax(-1)
        hyps.append(proc.batch_decode(ids)[0].lower().strip())
        refs.append(original_clean(row["transcript"]))
    o = jiwer.process_words(refs, hyps)
    return {"utterances": len(refs), "wer": round(o.wer, 4), "substitutions": o.substitutions,
            "deletions": o.deletions, "insertions": o.insertions, "hits": o.hits,
            "cer": round(jiwer.cer(refs, hyps), 4)}


def weights() -> dict:
    from huggingface_hub import hf_hub_download
    from safetensors.numpy import load_file

    import numpy as np

    a = load_file(hf_hub_download(FINETUNE, "model.safetensors"))
    b = load_file(hf_hub_download(STOCK, "model.safetensors"))
    # newer transformers save the weight-normalised convolution under new names; same tensors
    renamed = {"wav2vec2.encoder.pos_conv_embed.conv.parametrizations.weight.original0": "wav2vec2.encoder.pos_conv_embed.conv.weight_g",
               "wav2vec2.encoder.pos_conv_embed.conv.parametrizations.weight.original1": "wav2vec2.encoder.pos_conv_embed.conv.weight_v"}
    a = {renamed.get(k, k): v for k, v in a.items()}
    common = sorted(set(a) & set(b))
    differ = [k for k in common if a[k].shape != b[k].shape or (a[k] != b[k]).any()]
    extra = {k: {"shape": list(a[k].shape), "nan_values": int(np.isnan(a[k]).sum())} for k in sorted(set(a) - set(b))}
    return {"tensors_compared": len(common), "tensors_that_differ": differ,
            "only_in_finetune": extra, "only_in_stock": sorted(set(b) - set(a))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wer", action="store_true")
    ap.add_argument("--weights", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "data" / "work" / "fyp_audit.json"))
    args = ap.parse_args()
    result = {"training_logs": training_logs(), "labels": labels(), "split": split()}
    if args.wer:
        result["stock_model_wer"] = wer()
    if args.weights:
        result["weights"] = weights()
    Path(args.out).write_text(json.dumps(result, indent=1, ensure_ascii=False))
    print(json.dumps(result, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
