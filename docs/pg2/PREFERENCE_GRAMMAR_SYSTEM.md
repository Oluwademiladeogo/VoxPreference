# Preference Grammar System Design

## The Fundamental Fix

Preference Grammar is not an ASR problem first. It is a phonological selection
problem.

The professor's presentation defines PG as a mechanism for standardising
phonological corpora by comparing attested candidate forms against ranked
parameters. The input component is therefore the set of observed forms in
lexical context, not a single normalized text transcript.

The corrected system separates three layers:

1. Evidence collection: audio recordings, speaker metadata, elicitation notes,
   orthographic target word.
2. Variant extraction: expert IPA transcription or validated phoneme extraction.
3. PG operability: scoring and ranking the candidate forms against the six
   tenets.

The previous prototype collapsed these layers into:

audio -> ASR text -> dictionary IPA -> PG ranking

That cannot work reliably because ASR text normalizes away the pronunciation
variation that PG is supposed to evaluate.

## Core Data Contract

The PG engine should receive this shape:

```json
{
  "target_word": "think",
  "reference_ipa": "theta-like reference IPA if available",
  "variants": [
    {
      "ipa": "candidate IPA",
      "count": 1,
      "label": "optional group label",
      "notes": "optional source notes",
      "source_type": "expert",
      "reviewer": "reviewer name",
      "confidence": 1.0,
      "validated": true
    }
  ],
  "sliders": {
    "IA": 6,
    "CO": 5,
    "F": 4,
    "DI": 3,
    "PS": 2,
    "PC": 1
  }
}
```

Counts come from the corpus or elicitation set. If counts are unknown, each
variant can use `count: 1`, but Frequency will then mean "frequency among the
listed variants" rather than real corpus frequency.

For batch annotation, use
[templates/expert_variant_annotations.csv](../templates/expert_variant_annotations.csv)
and import it through `POST /preference/analyze-csv`.

## Tenets

The six PG tenets are represented as:

- `IA`: International Acceptance
- `CO`: Contrastiveness
- `F`: Frequency
- `DI`: Disambiguity
- `PS`: Phonetic Simplicity
- `PC`: Pedagogic Convenience

Default ranking follows the presentation:

`IA > CO > F > DI > PS > PC`

The app uses sliders so researchers can model a different policy, classroom, or
institutional ranking.

## Current Scoring MVP

The backend module [backend/pg_core.py](../backend/pg_core.py) implements
structured scoring:

- International Acceptance: normalized IPA similarity to `reference_ipa`; neutral
  score if no reference is supplied.
- Frequency: variant count divided by total count.
- Contrastiveness: average normalized IPA distance from the other candidate
  variants.
- Disambiguity: confusion-matrix score if supplied, otherwise nearest-neighbour
  IPA distance.
- Phonetic Simplicity: weighted complexity over IPA segments, with penalties for
  rare or harder segments and consonant clusters.
- Pedagogic Convenience: ease-oriented score based on clusters, rare segments,
  length, and syllabic load.

These are MVP heuristics. They make the app operational and transparent, but
they should be reviewed by the linguistics team before being reported as final
research metrics.

## What Must Be Validated Before Claiming Full Automation

1. IPA labels: create expert-reviewed IPA transcriptions for a validation set.
2. Variant extraction: compare any automatic extraction method against expert
   IPA labels using phoneme error rate.
3. Tenet formulas: have the professor or domain experts approve the exact score
   formulas and thresholds.
4. Confusion data: if Disambiguity uses a confusion matrix, define how that
   matrix is collected or computed.
5. Corpus frequency: distinguish true corpus frequency from user-entered sample
   counts.

## Audio Roadmap

The safest path is:

1. Keep manual/expert IPA entry as the source of truth.
2. Add optional ASR only to help identify the target word and segment audio.
3. Add forced alignment to locate the target word in the recording.
4. Add phoneme recognition or phone-level alignment only after expert IPA data
   exists.
5. Keep a correction UI so researchers can edit automatic IPA before PG scoring.

Whisper or WhisperX can help with transcription/alignment, but they do not by
themselves produce validated Nigerian English IPA variants.

## Production Shape

The clean production system should be:

- React frontend for evidence, variants, rankings, and reports.
- One FastAPI backend for PG analysis.
- A separate optional ASR/alignment service.
- A database for projects, recordings, variants, rankings, and result snapshots.
- Exportable reports that include the variants, weights, scores, warnings, and
  selected pronunciation.

The current repo now implements the first two pieces as a usable MVP.
It also records validation metadata so reports can distinguish expert-reviewed
variants from automatic or provisional variants.
