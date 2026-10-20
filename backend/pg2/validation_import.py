from __future__ import annotations

import csv
import math
from collections import defaultdict
from io import TextIOBase
from typing import Any

MAX_ANNOTATION_ROWS = 5000
MAX_CSV_IPA_CHARS = 64

TRUTHY = {"1", "true", "yes", "y", "validated"}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _to_float(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return number


def _to_bool(value: Any) -> bool:
    return _clean(value).lower() in TRUTHY


def rows_from_csv(file_obj: TextIOBase) -> list[dict[str, str]]:
    reader = csv.DictReader(file_obj)
    return [dict(row) for row in reader]


def aggregate_annotation_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"success": False, "errors": ["CSV file has no annotation rows."]}
    if len(rows) > MAX_ANNOTATION_ROWS:
        return {
            "success": False,
            "errors": [f"CSV has too many rows. Limit is {MAX_ANNOTATION_ROWS} rows."],
        }

    first = rows[0]
    target_word = _clean(first.get("target_word") or first.get("word"))
    reference_ipa = _clean(first.get("reference_ipa") or first.get("standard_ipa"))
    grouped: dict[str, dict[str, Any]] = {}
    reviewers_by_ipa: dict[str, set[str]] = defaultdict(set)
    notes_by_ipa: dict[str, list[str]] = defaultdict(list)
    labels_by_ipa: dict[str, set[str]] = defaultdict(set)
    errors = []

    for index, row in enumerate(rows, start=2):
        ipa = _clean(row.get("ipa") or row.get("variant_ipa"))
        if not ipa:
            errors.append(f"Row {index}: ipa is required.")
            continue
        if len(ipa) > MAX_CSV_IPA_CHARS:
            errors.append(f"Row {index}: ipa must be {MAX_CSV_IPA_CHARS} characters or fewer.")
            continue

        row_word = _clean(row.get("target_word") or row.get("word"))
        if row_word and not target_word:
            target_word = row_word
        if row_word and target_word and row_word != target_word:
            errors.append(f"Row {index}: target_word differs from {target_word}.")

        count = max(0.0, _to_float(row.get("count"), 1.0))
        confidence = max(0.0, min(1.0, _to_float(row.get("confidence"), 1.0)))
        reviewer = _clean(row.get("reviewer") or row.get("validated_by"))
        source_type = _clean(row.get("source_type") or row.get("source")) or "expert"
        validated = _to_bool(row.get("validated")) or bool(reviewer and source_type in {"expert", "human"})

        if ipa not in grouped:
            grouped[ipa] = {
                "ipa": ipa,
                "count": 0.0,
                "label": "",
                "notes": "",
                "source_type": source_type,
                "reviewer": "",
                "confidence": confidence,
                "validated": validated,
            }

        grouped[ipa]["count"] += count
        grouped[ipa]["confidence"] = min(grouped[ipa]["confidence"], confidence)
        grouped[ipa]["validated"] = bool(grouped[ipa]["validated"] or validated)
        if reviewer:
            reviewers_by_ipa[ipa].add(reviewer)
        if _clean(row.get("notes")):
            notes_by_ipa[ipa].append(_clean(row.get("notes")))
        if _clean(row.get("label")):
            labels_by_ipa[ipa].add(_clean(row.get("label")))

    if not target_word:
        errors.append("target_word is required in the CSV.")
    if errors:
        return {"success": False, "errors": errors}

    variants = []
    for ipa, variant in grouped.items():
        reviewers = sorted(reviewers_by_ipa[ipa])
        variant["reviewer"] = ", ".join(reviewers) or None
        variant["label"] = ", ".join(sorted(labels_by_ipa[ipa])) or None
        variant["notes"] = " | ".join(notes_by_ipa[ipa]) or None
        variants.append(variant)

    variants.sort(key=lambda item: item["count"], reverse=True)
    return {
        "success": True,
        "target_word": target_word,
        "reference_ipa": reference_ipa,
        "variants": variants,
        "annotation_summary": {
            "row_count": len(rows),
            "variant_count": len(variants),
            "reviewers": sorted({reviewer for reviewers in reviewers_by_ipa.values() for reviewer in reviewers}),
        },
    }
