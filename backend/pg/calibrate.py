"""Calibrate the variant classifier on human-labelled tokens.

The phone model has systematic biases (on Nigerian speech it hears many dental stops [d̪] as [ð]).
Per unit we fit a temperature T and an offset b_v per variant so that the posterior is
softmax(-nll_v / T + b_v), by maximum likelihood of the human labels with a small L2 penalty on
the offsets. Leave-one-speaker-out evaluation shows whether a calibration carries over to
speakers it was not fitted on. Result files live in pg/kb/calibration.json.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

KB = Path(__file__).resolve().parent / "kb" / "calibration.json"


def _matrix(rows: list[dict], labels: list[str]) -> np.ndarray:
    big = 1e4
    return np.array([[r["nll"].get(l) if r["nll"].get(l) is not None else big for l in labels] for r in rows], dtype=float)


def _posteriors(nll: np.ndarray, temperature: float, offsets: np.ndarray) -> np.ndarray:
    z = -nll / temperature + offsets
    z -= z.max(1, keepdims=True)
    p = np.exp(z)
    return p / p.sum(1, keepdims=True)


def fit(rows: list[dict], labels: list[str], class_of: dict[str, str], l2: float = 0.5) -> dict:
    """rows: [{"nll": {label: nll}, "gold": class}]; class_of maps each label to its class."""
    from scipy.optimize import minimize

    nll = _matrix(rows, labels)
    member = np.array([[class_of[l] == r["gold"] for l in labels] for r in rows], dtype=float)
    keep = member.sum(1) > 0
    nll, member = nll[keep], member[keep]

    def loss(theta):
        t, b = math.exp(theta[0]), np.concatenate([[0.0], theta[1:]])
        p = _posteriors(nll, t, b)
        return -np.log((p * member).sum(1) + 1e-12).mean() + l2 * (theta[1:] ** 2).sum() / len(nll)

    theta0 = np.zeros(len(labels))
    res = minimize(loss, theta0, method="L-BFGS-B")
    t = math.exp(res.x[0])
    return {"temperature": round(t, 4), "offsets": {l: round(float(b), 4) for l, b in zip(labels, np.concatenate([[0.0], res.x[1:]]))}}


def predict(row: dict, calib: dict, class_of: dict[str, str]) -> tuple[str, float]:
    labels = list(calib["offsets"])
    nll = _matrix([row], labels)
    p = _posteriors(nll, calib["temperature"], np.array([calib["offsets"][l] for l in labels]))[0]
    by_class = defaultdict(float)
    for l, x in zip(labels, p):
        by_class[class_of[l]] += x
    best = max(by_class, key=by_class.get)
    return best, by_class[best]


def leave_one_speaker_out(rows: list[dict], labels: list[str], class_of: dict[str, str], l2: float = 0.5) -> dict:
    """Accuracy of the raw argmax vs the calibrated classifier on each speaker, fitted on the others."""
    speakers = sorted({r["speaker"] for r in rows})
    raw = cal = n = 0
    for spk in speakers:
        train = [r for r in rows if r["speaker"] != spk]
        test = [r for r in rows if r["speaker"] == spk]
        calib = fit(train, labels, class_of, l2)
        ident = {"temperature": 1.0, "offsets": {l: 0.0 for l in labels}}
        for r in test:
            raw += predict(r, ident, class_of)[0] == r["gold"]
            cal += predict(r, calib, class_of)[0] == r["gold"]
            n += 1
    return {"tokens": n, "speakers": len(speakers), "raw_accuracy": raw / n, "calibrated_accuracy": cal / n}


def load(path: Path = KB) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("units", {})
