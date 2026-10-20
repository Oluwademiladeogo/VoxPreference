"""Human verification: export each token as a clip with a labelling page, then score the labels.

python -m pg.review export <analysis.json> <audio files...> --out review/
python -m pg.review score <analysis.json> <labels.csv>
"""
from __future__ import annotations

import argparse
import csv
import html
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from . import audio as audio_io


def export(analysis: dict, audio_by_name: dict[str, np.ndarray], out: Path, pad_s: float = 0.25) -> Path:
    import soundfile as sf

    out = Path(out)
    (out / "clips").mkdir(parents=True, exist_ok=True)
    options = analysis["unit"]["candidates"] + ["other", "unsure"]
    rows = []
    for i, t in enumerate(analysis["tokens"]):
        a = audio_by_name.get(t["recording"])
        if a is None:
            continue
        lo, hi = max(0, int((t["start"] - pad_s) * 16000)), min(len(a), int((t["end"] + pad_s) * 16000))
        clip = f"clips/{i:04d}.wav"
        sf.write(out / clip, a[lo:hi], 16000)
        radios = "".join(
            f'<label><input type="radio" name="t{i}" value="{html.escape(o)}">[{html.escape(o)}]</label> ' for o in options
        )
        rows.append(
            f'<tr data-id="{i}"><td>{i}</td><td><audio controls preload="none" src="{clip}"></audio></td>'
            f'<td>{html.escape(t["word"])}</td><td>{radios}</td>'
            f'<td class="sys">[{html.escape(t["variant"])}] {t["posterior"]:.2f}</td></tr>'
        )
    unit = analysis["unit"]
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>PG review</title><style>
body{{font-family:system-ui,sans-serif;margin:20px}} td{{border-bottom:1px solid #ddd;padding:6px}} label{{margin-right:8px;white-space:nowrap}}
.sys{{display:none;color:#555}} body.show .sys{{display:table-cell}}</style></head><body>
<h1>Listen and label: {html.escape(unit['label'])} (/{html.escape(unit['phoneme'])}/)</h1>
<p>For each clip, choose the sound the speaker used for /{html.escape(unit['phoneme'])}/ in the word. Labels are saved in this browser as you go.
<button id="dl">Download labels.csv</button> <label><input type="checkbox" id="show"> show the system's answer (leave off while labelling)</label></p>
<table>{''.join(rows)}</table>
<script>
const KEY = "pg-review-" + location.pathname;
let saved = {{}};
try {{ saved = JSON.parse(localStorage.getItem(KEY) || "{{}}"); }} catch (e) {{}}
document.querySelectorAll("input[type=radio]").forEach(r => {{
  if (saved[r.name] === r.value) r.checked = true;
  r.addEventListener("change", () => {{ saved[r.name] = r.value; try {{ localStorage.setItem(KEY, JSON.stringify(saved)); }} catch (e) {{}} }});
}});
document.getElementById("show").addEventListener("change", e => document.body.classList.toggle("show", e.target.checked));
document.getElementById("dl").addEventListener("click", () => {{
  const lines = ["token,label"].concat(Object.entries(saved).map(([k, v]) => k.slice(1) + "," + v));
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([lines.join("\\n")], {{type: "text/csv"}}));
  a.download = "labels.csv"; a.click();
}});
</script></body></html>"""
    path = out / "review.html"
    path.write_text(page, encoding="utf-8")
    return path


def score(analysis: dict, labels_csv: Path) -> dict:
    with open(labels_csv, encoding="utf-8") as f:
        labels = {int(r["token"]): r["label"] for r in csv.DictReader(f)}
    tokens = analysis["tokens"]
    pairs = [(labels[i], tokens[i]["variant"], tokens[i]["posterior"]) for i in labels
             if i < len(tokens) and labels[i] not in ("unsure",)]
    conf = defaultdict(Counter)
    for gold, pred, _ in pairs:
        conf[gold][pred] += 1
    n = len(pairs)
    acc = sum(g == p for g, p, _ in pairs) / n if n else float("nan")
    confident = [(g, p) for g, p, q in pairs if q >= 0.9]
    return {
        "labelled": n,
        "accuracy": acc,
        "confident_share": len(confident) / n if n else float("nan"),
        "confident_accuracy": sum(g == p for g, p in confident) / len(confident) if confident else float("nan"),
        "confusion": {g: dict(c) for g, c in conf.items()},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m pg.review")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("analysis")
    e.add_argument("audio", nargs="+")
    e.add_argument("--out", default="pg_review")
    s = sub.add_parser("score")
    s.add_argument("analysis")
    s.add_argument("labels")
    args = ap.parse_args(argv)
    analysis = json.loads(Path(args.analysis).read_text(encoding="utf-8"))
    if args.cmd == "export":
        audio = {Path(p).name: audio_io.load(p) for p in args.audio}
        print(export(analysis, audio, Path(args.out)))
    else:
        print(json.dumps(score(analysis, Path(args.labels)), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
