import numpy as np

from pg.calibrate import fit, leave_one_speaker_out, predict


def biased_rows(n_per=30, seed=0):
    """A classifier that systematically prefers 'ð' by 1.5 nats when the truth is 'd'."""
    rng = np.random.default_rng(seed)
    rows = []
    for spk in range(6):
        for _ in range(n_per):
            gold = "d" if rng.random() < 0.5 else "ð"
            base = {"d": 5.0, "ð": 5.0}
            base[gold] -= 1.0  # evidence for the truth
            base["ð"] -= 1.5  # but a bias towards ð
            nll = {k: v + rng.normal(0, 0.4) for k, v in base.items()}
            rows.append({"speaker": f"s{spk}", "gold": gold, "nll": nll})
    return rows


def test_calibration_removes_a_systematic_bias():
    rows = biased_rows()
    labels, class_of = ["ð", "d"], {"ð": "ð", "d": "d"}
    calib = fit(rows, labels, class_of)
    assert calib["offsets"]["d"] > 0.5  # learns to favour d
    res = leave_one_speaker_out(rows, labels, class_of)
    assert res["raw_accuracy"] < 0.65 and res["calibrated_accuracy"] > 0.85


def test_predict_merges_labels_of_one_class():
    calib = {"temperature": 1.0, "offsets": {"ɛ": 0.0, "e": 0.0, "a": 0.0}}
    cls, p = predict({"nll": {"ɛ": 2.0, "e": 2.0, "a": 1.5}}, calib, {"ɛ": "ɛ", "e": "ɛ", "a": "a"})
    assert cls == "ɛ" and p > 0.5
