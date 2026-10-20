"""Command line: python -m pg --words think --audio recordings/*.wav --out results/

Recordings are single words unless --transcripts gives a TSV of <file name>\t<transcript> lines, or
--asr is set for unscripted audio (the target words are then found by speech recognition).
A TSV of <file name>\t<speaker> lines can be passed with --speakers.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import audio as audio_io
from .ot import DEFAULT_RANKING
from .pipeline import Analyzer, Recording, survey
from .report import write_all
from .tenets import settings_from


def _tsv(path: str | None) -> dict[str, str]:
    if not path:
        return {}
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if "\t" in line:
            k, v = line.split("\t", 1)
            out[Path(k.strip()).name] = v.strip()
            out[Path(k.strip()).stem] = v.strip()
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m pg", description="Preference Grammar analysis of recordings")
    ap.add_argument("--words", help="comma-separated target words, e.g. think,three,thank")
    ap.add_argument("--survey", action="store_true",
                    help="analyse every sound in the knowledge base, choosing the target words from the transcripts")
    ap.add_argument("--unit", help="knowledge-base unit, e.g. TH-voiceless or NURSE (default: inferred from the words)")
    ap.add_argument("--audio", nargs="+", required=True, help="audio files")
    ap.add_argument("--transcripts", help="TSV: file name, transcript (omit for single-word recordings)")
    ap.add_argument("--asr", action="store_true",
                    help="unscripted audio (podcasts, interviews): find the target words by speech recognition")
    ap.add_argument("--speakers", help="TSV: file name, speaker id (a file with an id counts as that one speaker)")
    ap.add_argument("--no-diarize", action="store_true",
                    help="with --asr, do not separate the speakers inside each recording (by default they are separated)")
    ap.add_argument("--num-speakers", type=int, help="with --asr, how many people talk in each recording, if known")
    ap.add_argument("--ranking", default=DEFAULT_RANKING, help=f'tenet ranking (default "{DEFAULT_RANKING}")')
    ap.add_argument("--settings", help="JSON object overriding tenet thresholds, e.g. {\"freq_threshold\": 0.15}")
    ap.add_argument("--out", default="pg_results", help="output folder")
    args = ap.parse_args(argv)

    transcripts, speakers = _tsv(args.transcripts), _tsv(args.speakers)
    recordings = []
    for f in args.audio:
        p = Path(f)
        transcript = transcripts.get(p.name, transcripts.get(p.stem, "auto" if args.asr else ""))
        recordings.append(Recording(p.name, audio_io.load(p), speaker=speakers.get(p.name, speakers.get(p.stem, "")),
                                    transcript=transcript, diarize=False if args.no_diarize else None,
                                    num_speakers=args.num_speakers))
    unnamed = sum(not r.speaker for r in recordings) if not args.asr or args.no_diarize else 0
    if unnamed:
        print(f"warning: {unnamed} recording(s) have no speaker id (--speakers), so each counts as a separate speaker "
              "for the minimum-speaker rule and the stability resampling")
    settings = settings_from(json.loads(args.settings) if args.settings else None)
    if args.survey:
        run_survey(Analyzer(), recordings, args, settings)
        return
    if not args.words:
        ap.error("--words is required unless --survey is given")
    analysis = Analyzer().analyse(recordings, args.words.split(","), args.unit, args.ranking, settings)
    for p in write_all(analysis, Path(args.out)):
        print(p)
    if analysis.tableau:
        print()
        print(analysis.tableau.to_markdown())
        print("\npreferred:", ", ".join(analysis.preferred))
    for w in analysis.warnings:
        print("warning:", w)


def run_survey(analyzer, recordings, args, settings):
    results = survey(analyzer, recordings, args.ranking, settings)
    out = Path(args.out)
    rows = ["| Sound | Classifier | Tokens | Speakers | Variant shares | Preferred | Stable in |", "|---|---|---|---|---|---|---|"]
    summary = {}
    for key, a in results.items():
        write_all(a, out / key)
        status = (a.unit.validation or {}).get("status", "not validated")
        shares = ", ".join(f"[{c.segment}] {c.share:.0%}" for c in a.candidates) or "-"
        rate = max((a.stability or {}).get("preferred_rate", {}).values(), default=None)
        stable = f"{rate:.0%}" if rate is not None else "-"
        speakers = len({t.speaker for t in a.tokens})
        rows.append(f"| {a.unit.label} /{a.unit.phoneme}/ | {status} | {len(a.tokens)} | {speakers} | {shares} | "
                    f"{', '.join(a.preferred) or '-'} | {stable} |")
        summary[key] = {"status": status, "tokens": len(a.tokens), "speakers": speakers, "words": a.words,
                        "candidates": [{"segment": c.segment, "share": round(c.share, 4), "tokens": c.tokens} for c in a.candidates],
                        "preferred": a.preferred, "stability": a.stability, "warnings": a.warnings}
    out.mkdir(parents=True, exist_ok=True)
    (out / "survey.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (out / "survey.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(rows))
    print("\nper-sound results in", out)


if __name__ == "__main__":
    main()
