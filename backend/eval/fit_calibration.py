"""Validate the variant classifier per unit on gold-labelled tokens, and fit calibration where it truly helps.

Metrics, with speaker-bootstrap 95% intervals: accuracy beside the majority-class baseline, balanced accuracy,
Cohen's kappa (agreement beyond chance; a constant predictor scores 0), and the error in the estimated variant
shares (total variation distance), which is what PG's Frequency tenet consumes. Calibration is evaluated on
held-out speakers and kept only if it raises kappa with an interval that excludes zero, because under class
imbalance accuracy rewards predicting the majority class for every token.

Writes pg/kb/calibration.json and each unit's "validation" entry in pg/kb/units.json (--write).

python -m eval.fit_calibration [--rows data/work/saa_rows.json] [--write]
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import random
from pathlib import Path

import numpy as np

from eval.saa_gold import BACKEND, CLASS, to_class
from pg.calibrate import KB, fit, predict
from pg.tenets import KB_DIR, load_units

VALIDATED_KAPPA = 0.5  # substantial agreement beyond chance, on held-out speakers


def kappa(gold: list[str], pred: list[str]) -> float:
    n = len(gold)
    labels = sorted(set(gold) | set(pred))
    po = sum(g == p for g, p in zip(gold, pred)) / n
    gc, pc = collections.Counter(gold), collections.Counter(pred)
    pe = sum(gc[l] * pc[l] for l in labels) / n / n
    return 0.0 if pe == 1 else (po - pe) / (1 - pe)


def metrics(gold: list[str], pred: list[str]) -> dict:
    n = len(gold)
    gc = collections.Counter(gold)
    recalls = [sum(g == p for g, p in zip(gold, pred) if g == c) / k for c, k in gc.items()]
    pc = collections.Counter(pred)
    tvd = 0.5 * sum(abs(gc[c] / n - pc[c] / n) for c in set(gc) | set(pc))
    return {"accuracy": sum(g == p for g, p in zip(gold, pred)) / n, "majority": max(gc.values()) / n,
            "balanced_accuracy": float(np.mean(recalls)), "kappa": kappa(gold, pred), "share_tvd": tvd}


def bootstrap(rows: list[dict], preds: list[str], n: int = 1000, seed: int = 0) -> dict:
    """95% intervals over speakers (resampled with replacement)."""
    by = collections.defaultdict(list)
    for i, r in enumerate(rows):
        by[r["speaker"]].append(i)
    spk = sorted(by)
    rng = random.Random(seed)
    draws = collections.defaultdict(list)
    for _ in range(n):
        idx = [i for s in rng.choices(spk, k=len(spk)) for i in by[s]]
        m = metrics([rows[i]["gold"] for i in idx], [preds[i] for i in idx])
        for k, v in m.items():
            draws[k].append(v)
    return {k: (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) for k, v in draws.items()}


def raw_prediction(r: dict, labels: list[str], class_of: dict) -> str:
    """The deployed closed-set decision without calibration: the candidate with the lowest CTC loss."""
    scored = [(r["nll"][l], l) for l in labels if r["nll"].get(l) is not None]
    return class_of[min(scored)[1]] if scored else "other"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default=str(BACKEND / "data" / "work" / "saa_rows.json"))
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--l2", type=float, default=0.5)
    args = ap.parse_args(argv)
    rows = json.loads(Path(args.rows).read_text(encoding="utf-8"))
    units = load_units()
    calibrations, validation = {}, {}
    for unit_key in CLASS:
        labels = list(units[unit_key].candidates)
        class_of = {l: to_class(unit_key, l) for l in labels}
        rs = [r for r in rows if r["unit"] == unit_key and r["gold"] in set(class_of.values()) and r.get("nll")]
        if len({r["speaker"] for r in rs}) < 3:
            continue
        gold = [r["gold"] for r in rs]
        raw = [raw_prediction(r, labels, class_of) for r in rs]
        # leave-one-speaker-out calibrated predictions
        cal = [None] * len(rs)
        for spk in sorted({r["speaker"] for r in rs}):
            train = [r for r in rs if r["speaker"] != spk]
            c = fit(train, labels, class_of, args.l2)
            for i, r in enumerate(rs):
                if r["speaker"] == spk:
                    cal[i] = predict(r, c, class_of)[0]
        m_raw, m_cal = metrics(gold, raw), metrics(gold, cal)
        ci_raw = bootstrap(rs, raw)
        # bootstrap the kappa gain over speakers
        by = collections.defaultdict(list)
        for i, r in enumerate(rs):
            by[r["speaker"]].append(i)
        spk, rng, gains = sorted(by), random.Random(1), []
        for _ in range(1000):
            idx = [i for s in rng.choices(spk, k=len(spk)) for i in by[s]]
            g = [gold[i] for i in idx]
            gains.append(kappa(g, [cal[i] for i in idx]) - kappa(g, [raw[i] for i in idx]))
        gain_lo, gain_hi = np.percentile(gains, [2.5, 97.5])
        keep = bool(gain_lo > 0)
        chosen = m_cal if keep else m_raw
        print(f"\n{unit_key}: {len(rs)} tokens, {len(spk)} speakers")
        for name, m in (("raw", m_raw), ("calibrated, held-out speakers", m_cal)):
            print(f"   {name:30s} accuracy {m['accuracy']:.0%} (majority {m['majority']:.0%})  balanced {m['balanced_accuracy']:.0%}  "
                  f"kappa {m['kappa']:.2f}  share error {m['share_tvd']:.2f}  predicted {dict(collections.Counter(raw if name == 'raw' else cal))}")
        print(f"   raw 95% CI: accuracy {ci_raw['accuracy'][0]:.0%}-{ci_raw['accuracy'][1]:.0%}, kappa {ci_raw['kappa'][0]:.2f}-{ci_raw['kappa'][1]:.2f}")
        print(f"   kappa gain from calibration {np.mean(gains):+.2f} (95% CI {gain_lo:+.2f} to {gain_hi:+.2f}) -> {'kept' if keep else 'not kept'}")
        if keep:
            calibrations[unit_key] = {**fit(rs, labels, class_of, args.l2),
                                      "fitted_on": f"{len(rs)} human-labelled tokens from {len(spk)} speakers"}
        validated = chosen["kappa"] >= VALIDATED_KAPPA
        validation[unit_key] = {
            "status": "validated" if validated else "not validated",
            "kappa": round(chosen["kappa"], 2), "accuracy": round(chosen["accuracy"], 2),
            "majority_baseline": round(chosen["majority"], 2), "balanced_accuracy": round(chosen["balanced_accuracy"], 2),
            "share_error": round(chosen["share_tvd"], 2), "calibrated": keep,
            "note": (f"kappa {chosen['kappa']:.2f} on {len(rs)} tokens from {len(spk)} Nigerian speakers "
                     f"(Speech Accent Archive; one paragraph, so new words are untested)"),
        }
    if args.write:
        KB.write_text(json.dumps({
            "about": "Per-unit temperature and variant offsets fitted by pg/calibrate.py on human-labelled Nigerian tokens "
                     "(Speech Accent Archive, phonetician IPA). Kept only where they raise Cohen's kappa on held-out speakers "
                     "with a speaker-bootstrap interval above zero. Refit with eval/fit_calibration.py when more labels exist.",
            "model": "facebook/wav2vec2-xlsr-53-espeak-cv-ft", "date": datetime.date.today().isoformat(), "units": calibrations,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        path = KB_DIR / "units.json"
        kb = json.loads(path.read_text(encoding="utf-8"))
        for key, unit in kb["units"].items():
            unit["validation"] = validation.get(key, {"status": "not validated", "note": "no human-labelled test yet"})
        path.write_text(json.dumps(kb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("\nwrote", KB, "and validation entries in", path)


if __name__ == "__main__":
    main()
