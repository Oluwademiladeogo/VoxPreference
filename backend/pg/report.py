"""Write an Analysis to the files the PG framework calls for (CSV, VTT, JSON and an HTML report)."""
from __future__ import annotations

import csv
import html
import io
import json
from collections import defaultdict
from pathlib import Path

from .pipeline import Analysis


def _csv(rows: list[list]) -> str:
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    return buf.getvalue()


def tokens_csv(a: Analysis) -> str:
    rows = [["recording", "speaker", "word", "start", "end", "variant", "posterior", "cluster", "subcluster", "review",
             "realised", "heard", "scores"]]
    for t in a.tokens:
        rows.append([t.recording, t.speaker, t.word, t.start, t.end, t.variant, t.posterior, t.primary, t.secondary,
                     t.review, t.realised, t.heard, json.dumps(t.scores, ensure_ascii=False)])
    return _csv(rows)


def subclusters_csv(a: Analysis) -> str:
    """Members of every sub-cluster, one column each, with the phoneme under study at cell (0,0)."""
    groups = defaultdict(list)
    for t in a.tokens:
        groups[t.secondary].append(f"{t.recording}@{t.start:.2f}")
    names = sorted(groups, key=lambda g: (-len(groups[g]), g))
    rows = [[a.unit.phoneme] + names]
    for i in range(max((len(v) for v in groups.values()), default=0)):
        rows.append([""] + [groups[g][i] if i < len(groups[g]) else "" for g in names])
    return _csv(rows)


def contrast_csv(a: Analysis) -> str:
    if a.clustering is None:
        return ""
    cats = a.clustering.categories
    rows = [[a.unit.phoneme] + cats]
    for i, c in enumerate(cats):
        rows.append([c] + [round(float(x), 4) for x in a.clustering.contrast[i]])
    return _csv(rows)


def vtt(a: Analysis, recording: str) -> str:
    def ts(s: float) -> str:
        return f"{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{s % 60:06.3f}"

    cues = ["WEBVTT", ""]
    for t in (t for t in a.tokens if t.recording == recording):
        cues += [f"{ts(t.start)} --> {ts(t.end)}", f"{t.word} [{t.realised}] {a.unit.label}={t.variant} (p={t.posterior:.2f})", ""]
    return "\n".join(cues)


def html_report(a: Analysis) -> str:
    tab = a.tableau
    rows = "".join(
        f"<tr class='{'review' if t.review else ''}'><td>{html.escape(t.recording)}</td><td>{html.escape(t.speaker)}</td>"
        f"<td>{html.escape(t.word)}</td><td>{t.start:.2f}–{t.end:.2f}</td><td>[{html.escape(t.variant)}]</td>"
        f"<td>{t.posterior:.2f}</td><td>{html.escape(t.secondary)}</td><td>{html.escape(t.heard)}</td></tr>"
        for t in a.tokens
    )
    cands = "".join(f"<li>[{html.escape(c.segment)}] {html.escape(c.form)}: {c.tokens} tokens ({c.share:.0%})</li>" for c in a.candidates)
    warn = "".join(f"<li>{html.escape(w)}</li>" for w in a.warnings)
    preferred = ", ".join(html.escape(p) for p in a.preferred) or "—"
    stab = ""
    if a.stability:
        rates = ", ".join(f"[{html.escape(k)}] {v:.0%}" for k, v in a.stability["preferred_rate"].items())
        top = max(a.stability["preferred_rate"].values())
        caution = "" if top >= 0.8 else (" <b>Not stable:</b> the preferred form depends on which speakers are included; "
                                        "collect more speakers or check the low-confidence tokens.")
        stab = (f"<p>Preferred in resamples of the {a.stability['speakers']} speakers "
                f"({a.stability['resamples']} bootstrap draws): {rates}.{caution}</p>")
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>PG analysis</title><style>
body{{font-family:system-ui,sans-serif;margin:24px;max-width:1100px}} table{{border-collapse:collapse;margin:12px 0}}
td,th{{border:1px solid #bbb;padding:4px 8px;text-align:left}} .shaded{{background:#ddd}} .winner td:first-child{{font-weight:bold}}
tr.review{{background:#fff4d6}} .ipa{{font-size:1.2em}}</style></head><body>
<h1>Preference Grammar analysis: {html.escape(a.unit.label)} in {html.escape(', '.join(a.words))}</h1>
<p class="ipa">Preferred form: <b>{preferred}</b></p>{stab}
<h2>Operability table</h2>{tab.to_html() if tab else '<p>No tokens.</p>'}
<p>Ranking: {html.escape(' >> '.join(','.join(s) for s in tab.ranking)) if tab else ''}. Hover a cell for the evidence behind each mark.</p>
<h2>Attested candidates</h2><ul>{cands}</ul>
<h2>Tokens</h2><p>Highlighted rows are below the confidence threshold and should be checked by ear.</p>
<table><tr><th>recording</th><th>speaker</th><th>word</th><th>time (s)</th><th>variant</th><th>posterior</th><th>sub-cluster</th><th>free phone decoding</th></tr>{rows}</table>
{'<h2>Warnings</h2><ul>' + warn + '</ul>' if warn else ''}</body></html>"""


def write_all(a: Analysis, out_dir: Path) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "analysis.json": json.dumps(a.to_dict(), ensure_ascii=False, indent=1),
        "tokens.csv": tokens_csv(a),
        "subclusters.csv": subclusters_csv(a),
        "contrast_matrix.csv": contrast_csv(a),
        "operability_table.csv": a.tableau.to_csv() if a.tableau else "",
        "report.html": html_report(a),
    }
    for rec in sorted({t.recording for t in a.tokens}):
        files[f"vtt/{Path(rec).stem}.vtt"] = vtt(a, rec)
    written = []
    for name, text in files.items():
        p = out / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        written.append(p)
    return written
