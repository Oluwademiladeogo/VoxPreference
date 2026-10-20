"""Preference Grammar evaluation (Ugorji): attested forms compete on six ranked, violable tenets.

Evaluation follows Optimality Theory's EVAL: strict domination, so a candidate is eliminated as soon
as it has more violations than some rival on the highest-ranked tenet (or stratum of tenets) where
they differ. Whatever survives every tenet is preferred; more than one survivor is a genuine tie.
"""
from __future__ import annotations

import csv
import html
import io
from dataclasses import dataclass, field

TENETS = ("I-Ac", "ContR", "FreQ", "DisaM", "Pho-S", "Ped-C")
TENET_NAMES = {
    "I-Ac": "International acceptance",
    "ContR": "Contrastiveness",
    "FreQ": "Frequency",
    "DisaM": "Disambiguity",
    "Pho-S": "Phonetic simplicity",
    "Ped-C": "Pedagogic convenience",
}
# column headings as printed in the PG operability table
COLUMN_LABELS = {
    "I-Ac": "*No I-Ac",
    "ContR": "*No ContR",
    "FreQ": "*No FreQ",
    "DisaM": "DisaM",
    "Pho-S": "*Pho-S",
    "Ped-C": "*Ped-C",
}
DEFAULT_RANKING = "I-Ac >> ContR >> FreQ >> DisaM >> Pho-S >> Ped-C"
_ALIASES = {t.lower().replace("-", ""): t for t in TENETS}
_ALIASES.update({name.lower().replace(" ", ""): t for t, name in TENET_NAMES.items()})
_ALIASES.update({"paedagogicconvenience": "Ped-C", "iac": "I-Ac"})


@dataclass
class Violation:
    count: int = 0
    reason: str = ""
    source: str = ""  # what the judgement rests on: data, lexicon, typology, knowledge base, expert


@dataclass
class Candidate:
    form: str  # the word as realised, in IPA (e.g. "tɪŋk")
    segment: str = ""  # realisation of the unit under study (e.g. "t")
    tokens: int = 0
    share: float = 0.0
    violations: dict[str, Violation] = field(default_factory=dict)

    def marks(self, tenet: str) -> int:
        return self.violations.get(tenet, Violation()).count


@dataclass
class Tableau:
    unit: str  # the unit under study, e.g. "<th>" or "NURSE"
    ranking: list[list[str]]
    candidates: list[Candidate]
    winners: list[Candidate]
    eliminated_at: dict[str, int]  # candidate form -> index of the stratum that eliminated it

    @property
    def tie(self) -> bool:
        return len(self.winners) > 1

    def columns(self) -> list[str]:
        return [t for stratum in self.ranking for t in stratum]

    def cell(self, cand: Candidate, tenet: str) -> str:
        """Violation marks for one cell; '!' follows the mark that proved fatal."""
        n = cand.marks(tenet)
        stratum = next(i for i, s in enumerate(self.ranking) if tenet in s)
        if self.eliminated_at.get(cand.form) != stratum or n == 0:
            return "*" * n
        # within the fatal stratum the decisive mark is the first one beyond the survivors' total
        best = self._best_in_stratum(stratum)
        before = sum(cand.marks(t) for t in self.ranking[stratum][: self.ranking[stratum].index(tenet)])
        fatal_at = best - before  # 0-based index of the fatal mark inside this cell
        if 0 <= fatal_at < n:
            return "*" * (fatal_at + 1) + "!" + "*" * (n - fatal_at - 1)
        return "*" * n

    def shaded(self, cand: Candidate, tenet: str) -> bool:
        """Cells below the point where the candidate was already decided are irrelevant (shaded)."""
        stratum = next(i for i, s in enumerate(self.ranking) if tenet in s)
        out = self.eliminated_at.get(cand.form)
        return out is not None and stratum > out

    def _best_in_stratum(self, stratum: int) -> int:
        alive = [c for c in self.candidates if self.eliminated_at.get(c.form, len(self.ranking)) >= stratum]
        return min(sum(c.marks(t) for t in self.ranking[stratum]) for c in alive)

    def to_rows(self) -> list[dict]:
        rows = []
        for c in self.candidates:
            row = {"candidate": c.form, "segment": c.segment, "tokens": c.tokens, "share": round(c.share, 4),
                   "preferred": c in self.winners}
            for t in self.columns():
                row[COLUMN_LABELS[t]] = self.cell(c, t)
            rows.append(row)
        return rows

    def to_csv(self) -> str:
        buf = io.StringIO()
        rows = self.to_rows()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0]) if rows else ["candidate"])
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()

    def to_markdown(self) -> str:
        cols = self.columns()
        head = f"| {self.unit} | " + " | ".join(COLUMN_LABELS[t] for t in cols) + " |"
        lines = [head, "|" + "---|" * (len(cols) + 1)]
        for i, c in enumerate(self.candidates):
            label = f"{chr(97 + i)}. {'☞ ' if c in self.winners else ''}{c.form}"
            cells = [self.cell(c, t) for t in cols]
            lines.append(f"| {label} | " + " | ".join(cells) + " |")
        return "\n".join(lines)

    def to_html(self) -> str:
        cols = self.columns()
        out = ['<table class="pg-tableau"><thead><tr>', f"<th>{html.escape(self.unit)}</th>"]
        out += [f'<th title="{html.escape(TENET_NAMES[t])}">{html.escape(COLUMN_LABELS[t])}</th>' for t in cols]
        out.append("</tr></thead><tbody>")
        for i, c in enumerate(self.candidates):
            win = c in self.winners
            out.append(f'<tr class="{"winner" if win else ""}"><td>{chr(97 + i)}. {"☞ " if win else ""}{html.escape(c.form)}</td>')
            for t in cols:
                v = c.violations.get(t, Violation())
                cls = "shaded" if self.shaded(c, t) else ""
                tip = html.escape(f"{v.reason} [{v.source}]" if v.reason else "")
                out.append(f'<td class="{cls}" title="{tip}">{html.escape(self.cell(c, t))}</td>')
            out.append("</tr>")
        out.append("</tbody></table>")
        return "".join(out)


def parse_ranking(ranking=DEFAULT_RANKING) -> list[list[str]]:
    """Accept 'A >> B >> C', ['A', 'B'], or [['A', 'B'], ['C']] (tenets in one stratum are unranked
    with respect to each other and their marks are pooled). Tenets left out are deleted."""
    if isinstance(ranking, str):
        strata = [part.split(",") for part in ranking.split(">>")]
    else:
        strata = [s if isinstance(s, (list, tuple)) else [s] for s in ranking]
    parsed, seen = [], set()
    for stratum in strata:
        names = []
        for raw in stratum:
            key = str(raw).strip().lower().replace("-", "").replace(" ", "").replace("*no", "").replace("*", "")
            if not key:
                continue
            if key not in _ALIASES:
                raise ValueError(f"unknown tenet {raw!r}; expected one of {', '.join(TENETS)}")
            tenet = _ALIASES[key]
            if tenet in seen:
                raise ValueError(f"tenet {tenet} appears twice in the ranking")
            seen.add(tenet)
            names.append(tenet)
        if names:
            parsed.append(names)
    if not parsed:
        raise ValueError("the ranking must keep at least one tenet")
    return parsed


def evaluate(candidates: list[Candidate], ranking=DEFAULT_RANKING, unit: str = "") -> Tableau:
    strata = parse_ranking(ranking)
    if not candidates:
        raise ValueError("no candidates to evaluate")
    alive = list(candidates)
    eliminated_at: dict[str, int] = {}
    for i, stratum in enumerate(strata):
        totals = [sum(c.marks(t) for t in stratum) for c in alive]
        best = min(totals)
        for c, total in zip(alive, totals):
            if total > best:
                eliminated_at[c.form] = i
        alive = [c for c, total in zip(alive, totals) if total == best]
    return Tableau(unit=unit, ranking=strata, candidates=list(candidates), winners=alive, eliminated_at=eliminated_at)
