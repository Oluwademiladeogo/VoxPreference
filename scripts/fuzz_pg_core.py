#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import random
import string
import sys
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "pg2"))

from pg_core import analyze_preference_grammar  # noqa: E402
from validation_import import aggregate_annotation_rows, rows_from_csv  # noqa: E402


IPA_CHARS = "ptkbdgfszmnŋlrjwθðʃʒaeiouɪʊɔəɜʌæɛːˈˌ "


def random_ipa() -> str:
    return "".join(random.choice(IPA_CHARS) for _ in range(random.randint(0, 80))).strip()


def random_value():
    values = [
        None,
        "",
        "abc",
        "-10",
        "999999999999",
        "NaN",
        "Infinity",
        float("nan"),
        float("inf"),
        random.random() * 100,
    ]
    return random.choice(values)


def assert_jsonable(result: dict) -> None:
    encoded = json.dumps(result, allow_nan=False)
    decoded = json.loads(encoded)
    assert isinstance(decoded, dict)


def run_payload_cases() -> None:
    cases = [
        {},
        {"target_word": "", "variants": []},
        {"target_word": "think", "variants": [{"ipa": "θɪŋk", "count": "NaN"}]},
        {"target_word": "think", "variants": [{"ipa": "θɪŋk", "count": "Infinity"}]},
        {"target_word": "think", "variants": [{"ipa": "x" * 10000, "count": 1}]},
        {
            "target_word": "think",
            "reference_ipa": "θɪŋk",
            "variants": [
                {"ipa": "θɪŋk", "count": 1},
                {"ipa": "θɪŋk", "count": 2},
                {"ipa": "tɪŋk", "count": -1},
            ],
            "sliders": {"IA": "NaN", "CO": "Infinity", "F": -2},
        },
    ]

    for _ in range(300):
        variants = []
        for _ in range(random.randint(0, 35)):
            variants.append(
                {
                    "ipa": random_ipa(),
                    "count": random_value(),
                    "confidence": random_value(),
                    "source_type": random.choice(["expert", "asr", "?", "", None]),
                    "validated": random.choice([True, False, "true", "no", None]),
                    "reviewer": "".join(random.choice(string.ascii_letters) for _ in range(8)),
                }
            )
        cases.append(
            {
                "target_word": random.choice(["think", "", "x" * 200]),
                "reference_ipa": random_ipa(),
                "variants": variants,
                "sliders": {key: random_value() for key in ["IA", "CO", "F", "DI", "PS", "PC"]},
            }
        )

    for index, payload in enumerate(cases):
        result = analyze_preference_grammar(payload)
        assert_jsonable(result)
        if result.get("success"):
            assert result["tableRows"], index
            assert math.isfinite(float(result["weightedScore"])), index


def run_csv_cases() -> None:
    csv_texts = [
        "",
        "target_word,ipa,count\nthink,θɪŋk,1\nthink,tɪŋk,2\n",
        "target_word,ipa,count\nthink,,1\n",
        "target_word,ipa,count\nthink,θɪŋk,NaN\nthink,θɪŋk,Infinity\n",
    ]

    for csv_text in csv_texts:
        rows = rows_from_csv(StringIO(csv_text)) if csv_text else []
        result = aggregate_annotation_rows(rows)
        assert_jsonable(result)

    generated = StringIO()
    writer = csv.DictWriter(generated, fieldnames=["target_word", "ipa", "count", "reviewer"])
    writer.writeheader()
    for _ in range(200):
        writer.writerow(
            {
                "target_word": "stress",
                "ipa": random_ipa() or "s",
                "count": random_value(),
                "reviewer": "fuzzer",
            }
        )
    result = aggregate_annotation_rows(rows_from_csv(StringIO(generated.getvalue())))
    assert_jsonable(result)


def main() -> int:
    random.seed(42)
    run_payload_cases()
    run_csv_cases()
    print("fuzz ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
