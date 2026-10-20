"""Tune the speaker clustering on embeddings saved by eval.diarize_eval (no model needed).

    python -m eval.diarize_tune [data/work/diarize_eval]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from eval.diarize_eval import clip_score, score
from pg.diarize import cluster


def load(folder: Path):
    for p in sorted(folder.glob("conv*.npz")):
        d = np.load(p, allow_pickle=True)
        yield p.stem, d["emb"], [tuple(w) for w in d["windows"]], [tuple(t) for t in d["truth"]], len(d["speakers"])


def main():
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else "data/work/diarize_eval")
    convs = list(load(folder))
    configs = [(th, rf, sm) for th in (0.6, 0.7, 0.8) for rf in (0, 5) for sm in (1, 3, 5, 9)]
    results = {cfg: [] for cfg in configs}
    for name, emb, windows, truth, n in convs:
        for th, rf, sm in configs:
            d = cluster(windows, emb, None, th, smooth=sm, refine=rf)
            results[(th, rf, sm)].append((score(truth, d), d.speakers == n, d.speakers - n, clip_score(truth, d)[1]))
        k = cluster(windows, emb, n)
        print(name, n, "known count:", round(score(truth, k), 3), "word-level:", round(clip_score(truth, k)[1], 3), flush=True)
    for (th, rf, sm), r in results.items():
        print(f"threshold={th} refine={rf} smooth={sm}: accuracy {np.mean([x[0] for x in r]):.3f}, "
              f"word-level {np.mean([x[3] for x in r]):.3f}, right count {np.mean([x[1] for x in r]):.0%}, mean count error {np.mean([x[2] for x in r]):+.2f}")


if __name__ == "__main__":
    main()
