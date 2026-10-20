from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any


TENETS = {
    "IA": "International Acceptance",
    "CO": "Contrastiveness",
    "F": "Frequency",
    "DI": "Disambiguity",
    "PS": "Phonetic Simplicity",
    "PC": "Pedagogic Convenience",
}

DEFAULT_PRIORITY = ["IA", "CO", "F", "DI", "PS", "PC"]

STRESS_AND_BOUNDARY_MARKS = set("/[]()ˈˌ.")
MULTI_CHAR_SEGMENTS = [
    "tʃ",
    "dʒ",
    "aɪ",
    "aʊ",
    "ɔɪ",
    "eɪ",
    "oʊ",
    "əʊ",
    "ɪə",
    "eə",
    "ʊə",
    "iː",
    "uː",
    "ɑː",
    "ɔː",
    "ɜː",
]

VOWELS = set("aeiouɑɒɔəɜɪʊʌæɛɐɚɝ")
COMMON_SEGMENTS = set(
    "p b t d k g f v s z h m n ŋ l r j w θ ð ʃ ʒ tʃ dʒ "
    "i ɪ e ɛ æ a ɑ ɒ ɔ ə ɜ ʌ ʊ u aɪ aʊ ɔɪ eɪ oʊ əʊ ɪə eə ʊə "
    "iː uː ɑː ɔː ɜː"
    .split()
)
RARE_OR_HARD_SEGMENTS = set("θ ð ʒ ŋ ɜː ʊə".split())
MAX_VARIANTS = 25
MAX_IPA_CHARS = 64
MAX_TEXT_CHARS = 256
MAX_COUNT = 1_000_000


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return number


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def clean_text(value: Any, max_chars: int = MAX_TEXT_CHARS) -> str:
    return str(value or "").strip()[:max_chars]


@dataclass(frozen=True)
class PronunciationVariant:
    ipa: str
    count: float = 1.0
    label: str | None = None
    notes: str | None = None
    source_type: str = "expert"
    reviewer: str | None = None
    confidence: float | None = None
    validated: bool = False


def normalize_ipa(ipa: str) -> str:
    return " ".join((ipa or "").strip().split())[:MAX_IPA_CHARS]


def tokenize_ipa(ipa: str) -> list[str]:
    cleaned = normalize_ipa(ipa)
    tokens: list[str] = []
    i = 0
    while i < len(cleaned):
        char = cleaned[i]
        if char.isspace() or char in STRESS_AND_BOUNDARY_MARKS:
            i += 1
            continue

        matched = None
        for segment in MULTI_CHAR_SEGMENTS:
            if cleaned.startswith(segment, i):
                matched = segment
                break

        if matched:
            tokens.append(matched)
            i += len(matched)
            continue

        if i + 1 < len(cleaned) and cleaned[i + 1] == "ː":
            tokens.append(cleaned[i : i + 2])
            i += 2
            continue

        tokens.append(char)
        i += 1
    return tokens


def is_vowel(segment: str) -> bool:
    return any(char in VOWELS for char in segment)


def edit_distance(a: list[str], b: list[str]) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)

    previous = list(range(len(b) + 1))
    for i, left in enumerate(a, start=1):
        current = [i]
        for j, right in enumerate(b, start=1):
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + (0 if left == right else 1),
                )
            )
        previous = current
    return previous[-1]


def normalized_distance(left: str, right: str) -> float:
    left_tokens = tokenize_ipa(left)
    right_tokens = tokenize_ipa(right)
    longest = max(len(left_tokens), len(right_tokens), 1)
    return min(1.0, edit_distance(left_tokens, right_tokens) / longest)


def normalized_similarity(left: str, right: str) -> float:
    return round(1.0 - normalized_distance(left, right), 3)


def consonant_cluster_penalty(tokens: list[str]) -> float:
    longest = 0
    current = 0
    for token in tokens:
        if is_vowel(token):
            longest = max(longest, current)
            current = 0
        else:
            current += 1
    longest = max(longest, current)
    if longest <= 1:
        return 0.0
    if longest == 2:
        return 0.12
    return 0.22


def phonetic_simplicity(ipa: str) -> float:
    tokens = tokenize_ipa(ipa)
    if not tokens:
        return 0.0

    complexity = 0.0
    for token in tokens:
        if is_vowel(token):
            complexity += 0.65
        else:
            complexity += 1.0
        if token in RARE_OR_HARD_SEGMENTS:
            complexity += 0.35
        if token not in COMMON_SEGMENTS:
            complexity += 0.2
        if "ː" in token:
            complexity += 0.08

    avg_complexity = complexity / len(tokens)
    score = 1.0 - min(0.9, (avg_complexity - 0.55) / 2.2)
    score -= consonant_cluster_penalty(tokens)
    return round(max(0.0, min(1.0, score)), 3)


def pedagogic_convenience(ipa: str) -> float:
    tokens = tokenize_ipa(ipa)
    if not tokens:
        return 0.0

    syllables = max(1, sum(1 for token in tokens if is_vowel(token)))
    cluster_penalty = consonant_cluster_penalty(tokens)
    rare_count = sum(1 for token in tokens if token in RARE_OR_HARD_SEGMENTS)
    length_penalty = min(0.25, max(0, len(tokens) - 5) * 0.035)
    syllable_penalty = min(0.2, max(0, syllables - 2) * 0.06)
    rare_penalty = min(0.25, rare_count * 0.08)
    score = 1.0 - cluster_penalty - length_penalty - syllable_penalty - rare_penalty
    return round(max(0.0, min(1.0, score)), 3)


def contrastiveness(ipa: str, all_ipas: list[str]) -> float:
    others = [other for other in all_ipas if other != ipa]
    if not others:
        return 0.5
    distances = [normalized_distance(ipa, other) for other in others]
    return round(max(0.0, min(1.0, sum(distances) / len(distances))), 3)


def disambiguity(ipa: str, all_ipas: list[str], confusion_matrix: dict[str, Any] | None) -> float:
    if confusion_matrix:
        labels = confusion_matrix.get("labels") or []
        matrix = confusion_matrix.get("matrix") or []
        if ipa in labels:
            index = labels.index(ipa)
            try:
                row = [float(value) for value in matrix[index]]
                total = sum(row)
                if total > 0:
                    return round(max(0.0, min(1.0, float(row[index]) / total)), 3)
            except (IndexError, TypeError, ValueError):
                pass

    others = [other for other in all_ipas if other != ipa]
    if not others:
        return 0.5
    nearest_distance = min(normalized_distance(ipa, other) for other in others)
    return round(max(0.0, min(1.0, nearest_distance)), 3)


def build_weights(sliders: dict[str, Any] | None = None, ranking: list[str] | None = None) -> dict[str, float]:
    if sliders:
        values = {}
        for key in TENETS:
            values[key] = clamp(safe_float(sliders.get(key, 0), 0.0), 0.0, 100.0)
    else:
        ordered = [key for key in (ranking or DEFAULT_PRIORITY) if key in TENETS]
        missing = [key for key in DEFAULT_PRIORITY if key not in ordered]
        ordered.extend(missing)
        values = {key: float(len(ordered) - index) for index, key in enumerate(ordered)}

    total = sum(values.values())
    if total <= 0:
        values = {key: float(len(DEFAULT_PRIORITY) - index) for index, key in enumerate(DEFAULT_PRIORITY)}
        total = sum(values.values())

    return {key: round(value / total, 6) for key, value in values.items()}


def parse_variants(raw_variants: list[dict[str, Any]]) -> list[PronunciationVariant]:
    if not isinstance(raw_variants, list):
        return []

    grouped: dict[str, dict[str, Any]] = {}
    for item in raw_variants[:MAX_VARIANTS]:
        if not isinstance(item, dict):
            continue
        ipa = normalize_ipa(str(item.get("ipa", "")))
        if not ipa:
            continue
        count = clamp(safe_float(item.get("count", 1), 1.0), 0.0, MAX_COUNT)
        source_type = str(item.get("source_type") or item.get("source") or "expert").strip().lower()
        if source_type not in {"expert", "human", "auto", "asr", "phonemizer", "allosaurus", "mfa", "imported"}:
            source_type = "imported"

        confidence = (
            safe_float(item.get("confidence"), None)
            if item.get("confidence") not in (None, "")
            else None
        )
        if confidence is not None:
            confidence = clamp(confidence, 0.0, 1.0)

        validated_value = item.get("validated", False)
        if isinstance(validated_value, str):
            validated = validated_value.strip().lower() in {"1", "true", "yes", "y", "validated"}
        else:
            validated = bool(validated_value)

        reviewer = clean_text(item.get("reviewer") or item.get("validated_by")) or None
        if source_type in {"expert", "human"} and reviewer:
            validated = True

        if ipa in grouped:
            grouped[ipa]["count"] = clamp(grouped[ipa]["count"] + count, 0.0, MAX_COUNT)
            grouped[ipa]["validated"] = bool(grouped[ipa]["validated"] or validated)
            if reviewer and reviewer not in grouped[ipa]["reviewers"]:
                grouped[ipa]["reviewers"].append(reviewer)
            if confidence is not None:
                grouped[ipa]["confidence"] = min(
                    grouped[ipa]["confidence"] if grouped[ipa]["confidence"] is not None else confidence,
                    confidence,
                )
            continue

        grouped[ipa] = {
            "ipa": ipa,
            "count": count,
            "label": clean_text(item.get("label")) or None,
            "notes": clean_text(item.get("notes"), 500) or None,
            "source_type": source_type,
            "reviewers": [reviewer] if reviewer else [],
            "confidence": confidence,
            "validated": validated,
        }

    variants: list[PronunciationVariant] = []
    for item in grouped.values():
        variants.append(
            PronunciationVariant(
                ipa=item["ipa"],
                count=item["count"],
                label=item["label"],
                notes=item["notes"],
                source_type=item["source_type"],
                reviewer=", ".join(item["reviewers"]) or None,
                confidence=item["confidence"],
                validated=item["validated"],
            )
        )
    return variants


def analyze_preference_grammar(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"success": False, "errors": ["JSON payload must be an object."]}

    target_word = clean_text(payload.get("target_word") or payload.get("targetWord"))
    raw_variants = payload.get("variants") or []
    reference_ipa = normalize_ipa(str(payload.get("reference_ipa") or payload.get("standard_ipa") or ""))
    sliders = payload.get("sliders") or payload.get("criteria") or None
    ranking = payload.get("ranking") or payload.get("criteria_ranking") or None
    confusion_matrix = payload.get("confusion_matrix")

    errors = []
    warnings = []
    if not target_word:
        errors.append("target_word is required.")
    if not isinstance(raw_variants, list):
        errors.append("variants must be a list.")
    elif len(raw_variants) > MAX_VARIANTS:
        errors.append(f"At most {MAX_VARIANTS} IPA variants can be analyzed at once.")
    elif any(len(str(item.get("ipa", ""))) > MAX_IPA_CHARS for item in raw_variants if isinstance(item, dict)):
        errors.append(f"Each IPA variant must be {MAX_IPA_CHARS} characters or fewer.")

    variants = [] if errors else parse_variants(raw_variants)
    if not errors and not variants:
        errors.append("At least one IPA pronunciation variant is required.")

    if errors:
        return {"success": False, "errors": errors}

    if not reference_ipa:
        warnings.append(
            "International Acceptance used a neutral score because no reference IPA was supplied."
        )
    if len(variants) == 1:
        warnings.append(
            "Only one variant was supplied; contrastiveness and disambiguity are neutral."
        )
    if not any(variant.validated for variant in variants):
        warnings.append(
            "No expert-validated variants were supplied; treat the selected pronunciation as provisional."
        )
    if any(variant.source_type in {"auto", "asr", "phonemizer", "allosaurus", "mfa"} for variant in variants):
        warnings.append(
            "Some variants came from automatic extraction; review them before using the result as research evidence."
        )

    total_count = sum(variant.count for variant in variants) or len(variants)
    all_ipas = [variant.ipa for variant in variants]
    weights = build_weights(sliders=sliders, ranking=ranking)

    rows = []
    for variant in variants:
        frequency = variant.count / total_count if total_count else 0.0
        scores = {
            "international_acceptance": normalized_similarity(variant.ipa, reference_ipa)
            if reference_ipa
            else 0.5,
            "contrastiveness": contrastiveness(variant.ipa, all_ipas),
            "frequency": round(frequency, 3),
            "disambiguity": disambiguity(variant.ipa, all_ipas, confusion_matrix),
            "phonetic_simplicity": phonetic_simplicity(variant.ipa),
            "pedagogic_convenience": pedagogic_convenience(variant.ipa),
        }
        weighted_score = (
            scores["international_acceptance"] * weights["IA"]
            + scores["contrastiveness"] * weights["CO"]
            + scores["frequency"] * weights["F"]
            + scores["disambiguity"] * weights["DI"]
            + scores["phonetic_simplicity"] * weights["PS"]
            + scores["pedagogic_convenience"] * weights["PC"]
        )
        unmet = [name for name, score in scores.items() if score < 0.5]
        rows.append(
            {
                "ipa": variant.ipa,
                "label": variant.label,
                "count": variant.count,
                "notes": variant.notes,
                "source_type": variant.source_type,
                "reviewer": variant.reviewer,
                "confidence": variant.confidence,
                "validated": variant.validated,
                **scores,
                "weighted_score": round(weighted_score, 4),
                "unmet_tenets": unmet,
            }
        )

    rows.sort(key=lambda row: row["weighted_score"], reverse=True)
    best = rows[0]
    final_table = {
        row["ipa"]: {
            "international_acceptance": row["international_acceptance"],
            "contrastiveness": row["contrastiveness"],
            "frequency": row["frequency"],
            "disambiguity": row["disambiguity"],
            "phonetic_simplicity": row["phonetic_simplicity"],
            "pedagogic_convenience": row["pedagogic_convenience"],
            "weighted_score": row["weighted_score"],
        }
        for row in rows
    }

    return {
        "success": True,
        "targetWord": target_word,
        "referenceIpa": reference_ipa or None,
        "weights": weights,
        "tenets": TENETS,
        "tableRows": rows,
        "finalTable": final_table,
        "bestTranscription": best["ipa"],
        "weightedScore": best["weighted_score"],
        "validationSummary": {
            "variantCount": len(variants),
            "validatedCount": sum(1 for variant in variants if variant.validated),
            "automaticCount": sum(
                1
                for variant in variants
                if variant.source_type in {"auto", "asr", "phonemizer", "allosaurus", "mfa"}
            ),
            "reviewers": sorted(
                {variant.reviewer for variant in variants if variant.reviewer}
            ),
        },
        "warnings": warnings,
        "method": "pg_core_v1_direct_ipa",
    }
