#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


OUTPUT_FIELDS = [
    "target_word",
    "reference_ipa",
    "ipa",
    "count",
    "source_type",
    "reviewer",
    "confidence",
    "validated",
    "label",
    "notes",
    "audio_path",
    "transcript",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file_obj:
        return list(csv.DictReader(file_obj))


def contains_target(transcript: str, target_word: str) -> bool:
    pattern = re.compile(rf"(?<![A-Za-z']){re.escape(target_word)}(?![A-Za-z'])", re.IGNORECASE)
    return bool(pattern.search(transcript or ""))


def fetch_reference_ipa(endpoint: str, target_word: str) -> str:
    data = urllib.parse.urlencode({"word": target_word}).encode("utf-8")
    request = urllib.request.Request(endpoint, data=data, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"warning: could not fetch reference IPA from {endpoint}: {exc}", file=sys.stderr)
        return ""
    return str(payload.get("ipa") or "")


def run_allosaurus(audio_path: Path, lang: str) -> str:
    command = [sys.executable, "-m", "allosaurus.run", "-i", str(audio_path)]
    if lang:
        command.extend(["--lang", lang])
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        print(f"warning: allosaurus failed for {audio_path}: {exc}", file=sys.stderr)
        return ""
    return " ".join(completed.stdout.strip().split())


def build_rows(
    source_rows: list[dict[str, str]],
    target_word: str,
    reference_ipa: str,
    prefill_reference: bool,
    allosaurus: bool,
    allosaurus_lang: str,
    audio_root: Path | None,
    max_rows: int | None,
) -> list[dict[str, str]]:
    output = []
    for row in source_rows:
        transcript = row.get("transcript") or row.get("sentence") or row.get("text") or ""
        if not contains_target(transcript, target_word):
            continue
        audio_path = row.get("path") or row.get("audio") or row.get("audio_path") or ""
        resolved_audio_path = Path(audio_path)
        if audio_root and not resolved_audio_path.is_absolute():
            resolved_audio_path = audio_root / resolved_audio_path

        auto_ipa = ""
        source_type = "expert"
        notes = "reviewer should transcribe the actual target-word pronunciation"
        confidence = ""

        if allosaurus and audio_path and resolved_audio_path.exists():
            auto_ipa = run_allosaurus(resolved_audio_path, allosaurus_lang)
            source_type = "allosaurus"
            notes = "Allosaurus prefill from full audio; reviewer must correct target-word IPA"
            confidence = "0.3"

        if not auto_ipa and prefill_reference:
            auto_ipa = reference_ipa
            source_type = "phonemizer"
            notes = "prefilled reference IPA; reviewer must correct"
            confidence = "0.5"

        output.append(
            {
                "target_word": target_word,
                "reference_ipa": reference_ipa,
                "ipa": auto_ipa,
                "count": "1",
                "source_type": source_type,
                "reviewer": "",
                "confidence": confidence,
                "validated": "false",
                "label": "",
                "notes": notes,
                "audio_path": audio_path,
                "transcript": transcript,
            }
        )
        if max_rows and len(output) >= max_rows:
            break
    return output


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create an expert IPA annotation batch from transcript CSV files."
    )
    parser.add_argument("--target-word", required=True)
    parser.add_argument("--source-csv", action="append", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--reference-ipa", default="")
    parser.add_argument(
        "--ipa-endpoint",
        default="",
        help="Optional endpoint such as https://thebickersteth-voxpreference.hf.space/ipa",
    )
    parser.add_argument(
        "--prefill-reference",
        action="store_true",
        help="Fill ipa with reference_ipa as an unvalidated starting point.",
    )
    parser.add_argument(
        "--allosaurus",
        action="store_true",
        help="Use allosaurus as an unvalidated phone prefill when audio files exist locally.",
    )
    parser.add_argument("--allosaurus-lang", default="ipa")
    parser.add_argument(
        "--audio-root",
        default="",
        help="Directory used to resolve relative audio paths from the source CSV.",
    )
    parser.add_argument("--max-rows", type=int, default=None)
    args = parser.parse_args()

    target_word = args.target_word.strip()
    reference_ipa = args.reference_ipa.strip()
    if not reference_ipa and args.ipa_endpoint:
        reference_ipa = fetch_reference_ipa(args.ipa_endpoint, target_word)

    source_rows: list[dict[str, str]] = []
    for source in args.source_csv:
        source_rows.extend(read_rows(Path(source)))

    output_rows = build_rows(
        source_rows=source_rows,
        target_word=target_word,
        reference_ipa=reference_ipa,
        prefill_reference=args.prefill_reference,
        allosaurus=args.allosaurus,
        allosaurus_lang=args.allosaurus_lang,
        audio_root=Path(args.audio_root) if args.audio_root else None,
        max_rows=args.max_rows,
    )
    write_rows(Path(args.output), output_rows)
    print(f"wrote {len(output_rows)} annotation rows to {args.output}")
    if not output_rows:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
