"""How well speaker separation works, on made-up conversations whose speakers are known.

Utterances from different SLR70 Nigerian English speakers are joined into one recording in short turns
(1-3 utterances each, small pauses), as in a panel podcast. We then score how much of the speech is given to
the right speaker (after matching our anonymous labels to the true speakers) and whether the number of
speakers was found. Same-sex speakers are included, which is the harder case.

    python -m eval.diarize_eval [--conversations 8] [--minutes 4]
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

from pg.audio import load
from pg.diarize import Diarizer, cluster, speech_windows

SLR70 = Path(__file__).resolve().parents[1] / "data" / "work" / "slr70" / "wav"
SR = 16000


def by_speaker() -> dict[str, list[Path]]:
    out = defaultdict(list)
    for p in sorted(SLR70.glob("*.wav")):
        out[p.stem.rsplit("_", 1)[0]].append(p)
    return {s: ps for s, ps in out.items() if len(ps) >= 20}


def conversation(speakers: list[str], files: dict[str, list[Path]], seconds: float, rng: random.Random):
    pieces, truth, t, last = [], [], 0.0, None
    while t < seconds:
        who = rng.choice([s for s in speakers if s != last] or speakers)
        last = who
        for _ in range(rng.randint(1, 3)):
            audio = load(rng.choice(files[who]))
            gap = np.zeros(int(rng.uniform(0.15, 0.6) * SR), dtype=np.float32)
            pieces += [audio, gap]
            truth.append((t, t + len(audio) / SR, who))
            t += (len(audio) + len(gap)) / SR
    return np.concatenate(pieces), truth


def score(truth, dia, step: float = 0.05) -> float:
    """Share of speech time given to the right speaker, under the best one-to-one matching of labels."""
    true_names = sorted({w for _, _, w in truth})
    hyp_names = sorted({t.speaker for t in dia.turns}) or ["none"]
    m = np.zeros((len(true_names), len(hyp_names)))
    total = 0.0
    for s, e, who in truth:
        for x in np.arange(s, e, step):
            got = dia.speaker_at(x, x + step, reach=0.0)
            total += step
            if got is not None:
                m[true_names.index(who), hyp_names.index(got)] += step
    r, c = linear_sum_assignment(-m)
    return float(m[r, c].sum() / total)


def clip_score(truth, dia) -> tuple[float, float]:
    """Share of clips (a sentence each) credited to the right speaker, the way a word inside it is credited,
    under the best matching of labels; and the same for 0.4 s pieces from the middle of each clip."""
    true_names = sorted({w for _, _, w in truth})
    hyp = sorted({t.speaker for t in dia.turns}) or ["none"]
    whole, piece = np.zeros((len(true_names), len(hyp))), np.zeros((len(true_names), len(hyp)))
    for s, e, who in truth:
        for m, (a, b) in ((whole, (s, e)), (piece, ((s + e) / 2 - 0.2, (s + e) / 2 + 0.2))):
            got = dia.speaker_at(a, b)
            if got is not None:
                m[true_names.index(who), hyp.index(got)] += 1
    out = []
    for m in (whole, piece):
        r, c = linear_sum_assignment(-m)
        out.append(float(m[r, c].sum() / len(truth)))
    return tuple(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conversations", type=int, default=8)
    ap.add_argument("--minutes", type=float, default=4)
    ap.add_argument("--thresholds", default="0.8,0.9")
    ap.add_argument("--seed", type=int, default=0, help="a new seed gives conversations not used for tuning")
    ap.add_argument("--out", default="data/work/diarize_eval.json")
    ap.add_argument("--model", default=None, help="speaker model (default: pg.diarize.SPEAKER_MODEL)")
    args = ap.parse_args()
    files = by_speaker()
    rng = random.Random(args.seed)
    diarizer = Diarizer(args.model) if args.model else Diarizer()
    rows = []
    for i in range(args.conversations):
        n = [2, 3, 4, 5][i % 4]
        speakers = rng.sample(sorted(files), n)
        audio, truth = conversation(speakers, files, args.minutes * 60, rng)
        windows = speech_windows(audio)
        emb = diarizer.embed(audio, windows)
        cache = Path(args.out).with_suffix("") / f"conv{i}.npz"
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez(cache, emb=emb, windows=np.array(windows), truth=np.array(truth, dtype=object), speakers=speakers)
        row = {"speakers": n, "ids": speakers, "seconds": round(len(audio) / SR)}
        for th in [float(x) for x in args.thresholds.split(",")]:
            d = cluster(windows, emb, None, th)
            row[f"auto_{th}"] = {"found": d.speakers, "accuracy": round(score(truth, d), 3),
                                 "word_level": round(clip_score(truth, d)[1], 3)}
        d = cluster(windows, emb, n)
        row["known_n"] = {"found": d.speakers, "accuracy": round(score(truth, d), 3),
                          "word_level": round(clip_score(truth, d)[1], 3)}
        rows.append(row)
        print(json.dumps(row), flush=True)
    Path(args.out).write_text(json.dumps(rows, indent=1))
    keys = [k for k in rows[0] if k.startswith("auto_") or k == "known_n"]
    for k in keys:
        acc = np.mean([r[k]["accuracy"] for r in rows])
        right_n = np.mean([r[k]["found"] == r["speakers"] for r in rows])
        word = np.mean([r[k]["word_level"] for r in rows])
        print(f"{k}: words credited right {word:.3f}, speech time {acc:.3f}, right number of speakers in {right_n:.0%}")


if __name__ == "__main__":
    main()
