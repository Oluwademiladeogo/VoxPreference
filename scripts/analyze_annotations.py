#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "pg2"))

from pg_core import analyze_preference_grammar  # noqa: E402
from validation_import import aggregate_annotation_rows  # noqa: E402


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file_obj:
        return list(csv.DictReader(file_obj))


def parse_sliders(raw: str | None) -> dict[str, float] | None:
    if not raw:
        return None
    if raw.strip().startswith("{"):
        return json.loads(raw)

    sliders = {}
    for pair in raw.split(","):
        key, value = pair.split("=", 1)
        sliders[key.strip()] = float(value)
    return sliders


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate an expert IPA annotation CSV and run PG analysis."
    )
    parser.add_argument("annotation_csv")
    parser.add_argument("--sliders", default="IA=6,CO=5,F=4,DI=3,PS=2,PC=1")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    payload = aggregate_annotation_rows(load_rows(Path(args.annotation_csv)))
    if not payload.get("success"):
        print(json.dumps(payload, indent=2), file=sys.stderr)
        return 1

    sliders = parse_sliders(args.sliders)
    if sliders:
        payload["sliders"] = sliders

    result = analyze_preference_grammar(payload)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote PG analysis to {args.output}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
