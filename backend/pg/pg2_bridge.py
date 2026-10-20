"""Score the PG2 pages' attested variants with Ugorji's Preference Grammar: strict ranking of the six tenets.

The PG2 pages send whole-word IPA variants with counts and six sliders (0-6). The slider order becomes the
ranking (equal values are unranked with each other and their marks pooled; 0 deletes a tenet). Each variant is
lined up with the word's dictionary pronunciation to find the one sound it changes (e.g. [tɪŋk] changes /θ/
of "think" to [t]); the tenets are then judged by pg.tenets and the winner chosen by pg.ot, exactly as for
audio analyses. PG2's own validation summary and warnings are kept. Variants that do not line up with a single
sound of the word fall back to PG2's weighted method, with a warning saying so.
"""
from __future__ import annotations

from pathlib import Path

from . import lexicon
from .ot import COLUMN_LABELS, TENET_NAMES, Candidate, evaluate
from .tenets import Settings, assess, common_words, load_typology, load_units, tiers

RESOURCES = Path(__file__).resolve().parents[1] / "data" / "resources"
SLIDER_TENETS = {"IA": "I-Ac", "CO": "ContR", "F": "FreQ", "DI": "DisaM", "PS": "Pho-S", "PC": "Ped-C"}
ROW_KEYS = {"I-Ac": "international_acceptance", "ContR": "contrastiveness", "FreQ": "frequency",
            "DisaM": "disambiguity", "Pho-S": "phonetic_simplicity", "Ped-C": "pedagogic_convenience"}


class StrictScorer:
    def __init__(self, resources: Path = RESOURCES):
        from .kb.fetch import ensure

        ensure(resources)
        self.lexicons = lexicon.load_default(resources, names=("britfone", "cmudict"))
        self.units = load_units()
        self.typology = load_typology()
        self.settings = Settings()
        self.vocabulary = common_words(self.settings.disam_vocabulary)

    def pronunciations(self, word: str) -> list[list[str]]:
        for name in ("britfone", "cmudict"):
            lex = self.lexicons.get(name)
            if lex and lex.pronunciations(word):
                return [list(p) for p in lex.pronunciations(word)]
        return []

    def line_up(self, word: str, forms: list[str]):
        """(unit, canonical segments, slot, {form: segment}) for the first sound of the word that every
        variant either keeps or replaces, with the rest of the word unchanged; None if there is none."""
        variants = {f: lexicon.segments(f) for f in forms}
        for unit in self.units.values():
            same = lexicon.same_phoneme(unit.phoneme)
            for pron in self.pronunciations(word):
                for slot in (i for i, s in enumerate(pron) if s in same):
                    found = {}
                    for form, segs in variants.items():
                        if len(segs) != len(pron) or any(
                            not _same(a, b) for i, (a, b) in enumerate(zip(segs, pron)) if i != slot
                        ):
                            break
                        found[form] = segs[slot]
                    else:
                        if len(set(found.values())) == len(found):
                            return unit, pron, slot, found
        return None

    def score(self, payload: dict, weighted: dict) -> dict:
        """weighted: PG2's own result for the same payload (validation summary, warnings, rows)."""
        word = str(payload.get("target_word") or payload.get("targetWord") or "").strip().lower()
        rows = {r["ipa"]: r for r in weighted["tableRows"]}
        lined = self.line_up(word, list(rows))
        if lined is None:
            weighted["warnings"] = weighted.get("warnings", []) + [
                "These variants could not be lined up with one sound of the word in the knowledge base, "
                "so they were scored with PG2's weighted method instead of strict ranking."]
            return weighted
        unit, pron, slot, segment_of = lined
        ranking = ranking_from(payload)
        total = sum(float(r["count"]) for r in rows.values()) or 1.0
        cands = [Candidate(form, segment_of[form], tokens=int(round(float(r["count"]))), share=float(r["count"]) / total)
                 for form, r in rows.items()]
        assess(cands, unit, [word], list(self.lexicons.values()), self.typology, self.settings, self.vocabulary)
        tab = evaluate(cands, ranking, unit=unit.label)
        tier_of = tiers(tab)
        order = sorted(cands, key=lambda c: (c not in tab.winners, -tab.eliminated_at.get(c.form, len(tab.ranking)), -c.share))
        out_rows = []
        for c in order:
            row = dict(rows[c.form])
            for tenet, key in ROW_KEYS.items():
                row[key] = tab.cell(c, tenet) if tenet in tab.columns() else ""
            stratum = tab.eliminated_at.get(c.form)
            row["outcome"] = "preferred" if c in tab.winners else "out at " + ", ".join(tab.ranking[stratum])
            row["tier"] = tier_of.get(c.segment, "")
            row["sound"] = f"[{c.segment}]"
            row["unmet_tenets"] = [f"{t}: {c.violations[t].reason}" for t in tab.columns()
                                   if c.marks(t) and c.violations[t].reason]
            row.pop("weighted_score", None)
            out_rows.append(row)
        result = dict(weighted)
        result.update({
            "method": "Strict ranking (Ugorji's Preference Grammar)",
            "scoring": "strict",
            "ranking": " >> ".join(", ".join(s) for s in tab.ranking),
            "sound": {"key": unit.key, "label": unit.label, "phoneme": unit.phoneme,
                      "reference": "".join(pron), "validation": unit.validation},
            "bestTranscription": " / ".join(c.form for c in tab.winners),
            "tie": tab.tie,
            "weightedScore": None,
            "tableRows": out_rows,
            "finalTable": {r["ipa"]: {k: r[k] for k in ROW_KEYS.values()} | {"outcome": r["outcome"]} for r in out_rows},
            "operabilityTable": {"columns": [COLUMN_LABELS[t] for t in tab.columns()], "rows": tab.to_rows(),
                                 "html": tab.to_html()},
            "tenetNames": {t: TENET_NAMES[t] for t in tab.columns()},
        })
        result.pop("weights", None)
        if not result.get("referenceIpa"):
            result["warnings"] = [w for w in result.get("warnings", []) if "neutral score" not in w]
        if tab.tie:
            result["warnings"] = result.get("warnings", []) + [
                "The ranking does not separate the surviving forms: they are tied."]
        return result


def _same(a: str, b: str) -> bool:
    return a == b or b in lexicon.same_phoneme(a) or a in lexicon.same_phoneme(b)


def ranking_from(payload: dict) -> str:
    """'I-Ac >> ContR, FreQ >> ...' from PG2 sliders (higher = more important; equal = pooled; 0 = deleted),
    or from an explicit list of slider codes in priority order."""
    order = payload.get("ranking") or payload.get("criteria_ranking")
    if isinstance(order, list) and order:
        return " >> ".join(SLIDER_TENETS.get(str(k).upper(), str(k)) for k in order)
    sliders = payload.get("sliders") or payload.get("criteria") or {}
    values = {}
    for code, tenet in SLIDER_TENETS.items():
        try:
            values[tenet] = float(sliders.get(code, 0) if sliders else 6 - list(SLIDER_TENETS).index(code))
        except (TypeError, ValueError):
            values[tenet] = 0.0
    kept = sorted({v for v in values.values() if v > 0}, reverse=True)
    if not kept:
        raise ValueError("every tenet is set to 0; keep at least one")
    return " >> ".join(", ".join(t for t, v in values.items() if v == level) for level in kept)
