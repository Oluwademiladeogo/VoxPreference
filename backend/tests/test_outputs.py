import csv
import io
import json

import numpy as np

from pg import audio as audio_io
from pg.cluster import two_level
from pg.ot import Candidate, Violation, evaluate
from pg.pipeline import Analysis, Token
from pg.report import contrast_csv, html_report, subclusters_csv, tokens_csv, vtt, write_all
from pg.review import export, score
from pg.tenets import Unit


def fake_analysis():
    unit = Unit("TH-voiceless", "<th>", "θ", ["θ", "t", "s"], ["θ", "t"])
    toks = [
        Token("a.wav", "spk1", "think", 0.1, 0.5, "t", 0.95, {"t": 0.95, "θ": 0.05}, "tɪŋk", "t ɪ ŋ k"),
        Token("b.wav", "spk2", "think", 0.2, 0.6, "θ", 0.60, {"θ": 0.6, "t": 0.4}, "θɪŋk", "θ ɪ ŋ k", review=True),
        Token("c.wav", "spk3", "think", 0.0, 0.4, "t", 0.99, {"t": 0.99}, "tɪŋk", "t ɪ ŋ k"),
    ]
    clustering = two_level([t.variant for t in toks], np.eye(3) + 0.01)
    for t, p, s in zip(toks, clustering.primary, clustering.secondary):
        t.primary, t.secondary = p, s
    cands = [Candidate("tɪŋk", "t", 2, 2 / 3, {"DisaM": Violation(1, "three/tree", "lexicon")}),
             Candidate("θɪŋk", "θ", 1, 1 / 3, {"Pho-S": Violation(1, "rare", "typology")})]
    tab = evaluate(cands, unit="<th>")
    return Analysis(["think"], unit, {"think": "θɪŋk"}, toks, clustering, cands, tab, [c.form for c in tab.winners])


def test_csv_outputs_have_expected_shape():
    a = fake_analysis()
    rows = list(csv.reader(io.StringIO(tokens_csv(a))))
    assert rows[0][:6] == ["recording", "speaker", "word", "start", "end", "variant"] and len(rows) == 4
    sub = list(csv.reader(io.StringIO(subclusters_csv(a))))
    assert sub[0][0] == "θ"  # the phoneme under study sits at cell (0,0)
    assert set(sub[0][1:]) == {"t.1", "θ.1"}
    con = list(csv.reader(io.StringIO(contrast_csv(a))))
    assert con[0] == ["θ", "t", "θ"] and float(con[1][1]) == 1.0
    assert "WEBVTT" in vtt(a, "a.wav") and "<th>=t" in vtt(a, "a.wav")
    assert "θɪŋk" in html_report(a) and "operability" in html_report(a).lower()


def test_to_dict_is_json_serialisable_and_write_all(tmp_path):
    a = fake_analysis()
    d = json.loads(json.dumps(a.to_dict(), ensure_ascii=False))
    assert d["preferred"] == ["θɪŋk"] and d["tableau"]["rows"][0]["candidate"] == "tɪŋk"
    names = {p.name for p in write_all(a, tmp_path)}
    assert {"analysis.json", "tokens.csv", "operability_table.csv", "report.html", "a.vtt"} <= names


def test_review_export_and_score(tmp_path):
    a = fake_analysis()
    audio = {n: np.zeros(16000, dtype=np.float32) for n in ("a.wav", "b.wav", "c.wav")}
    page = export(a.to_dict(), audio, tmp_path)
    assert page.exists() and len(list((tmp_path / "clips").glob("*.wav"))) == 3
    labels = tmp_path / "labels.csv"
    labels.write_text("token,label\n0,t\n1,t\n2,unsure\n", encoding="utf-8")
    res = score(a.to_dict(), labels)
    assert res["labelled"] == 2 and res["accuracy"] == 0.5


def test_trim_finds_the_word_in_silence():
    sr = 16000
    t = np.arange(int(0.4 * sr)) / sr
    tone = 0.5 * np.sin(2 * np.pi * 220 * t).astype(np.float32)
    x = np.concatenate([np.zeros(sr, np.float32), tone, np.zeros(sr, np.float32)])
    clip, offset = audio_io.trim(x, sr, pad_s=0.0)
    assert abs(offset - 1.0) < 0.02 and abs(len(clip) / sr - 0.4) < 0.03


def test_load_resamples_wav_bytes():
    import soundfile as sf

    buf = io.BytesIO()
    sf.write(buf, np.zeros(44100, dtype=np.float32), 44100, format="WAV")
    out = audio_io.load(buf.getvalue())
    assert out.dtype == np.float32 and abs(len(out) - 16000) <= 1
