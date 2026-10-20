# Validated IPA Variant Research

## Finding

I did not find a ready-to-use public Nigerian English corpus with expert IPA
pronunciation-variant labels. Available Nigerian English speech resources are
useful for audio and orthographic transcription, but not enough to directly
produce research-grade PG inputs.

## Useful Sources

### OpenSLR SLR70

OpenSLR SLR70 is the best current public starting point for Nigerian English
audio:

- URL: https://www.openslr.org/70/
- It contains Nigerian English wave files and TSV orthographic transcripts.
- The dataset notes that the data was manually quality checked, but it does not
  provide expert IPA labels.

Use this for speech evidence and target-word extraction, not as validated IPA.

### Montreal Forced Aligner

MFA can align known orthographic transcripts to audio using pronunciation
dictionaries:

- User guide: https://montreal-forced-aligner.readthedocs.io/en/v3.1.0/user_guide/
- Model docs: https://montreal-forced-aligner.readthedocs.io/en/v3.1.0/user_guide/models/
- Dictionary docs: https://montreal-forced-aligner.readthedocs.io/en/stable/user_guide/dictionary.html

MFA is useful for locating words/phones in time and building pronunciation
dictionaries, but its output is only as good as the dictionary and acoustic
model. It should not be treated as expert Nigerian English IPA by default.

### Allosaurus

Allosaurus is a universal phone recognizer:

- GitHub: https://github.com/xinjli/allosaurus
- It can output phone sequences and supports a broad IPA inventory.

Allosaurus can prefill candidate phone strings for expert review. It is not a
replacement for validation, especially for Nigerian English standardisation.

### Universal Speech-to-IPA Work

Recent speech-to-IPA research shows the direction for automation:

- Paper: https://arxiv.org/pdf/2308.03917
- The authors emphasize that IPA label quality strongly affects performance.

This supports the build strategy: collect validated IPA labels first, then train
or adapt an automatic IPA extractor.

## Recommended Dataset Plan

1. Select target lexical items relevant to PG analysis.
2. Collect or extract audio examples for each target item.
3. Segment the target word in each recording.
4. Have at least one trained phonetician or linguistics reviewer annotate the
   IPA variant.
5. Prefer two reviewers for research-grade labels.
6. Adjudicate disagreement into a final accepted IPA variant.
7. Store each annotation with:
   - target word
   - audio/source ID
   - IPA variant
   - reviewer
   - confidence
   - validation status
   - notes
8. Aggregate counts by IPA variant and pass those variants to the PG engine.

## Data Template

Use [templates/expert_variant_annotations.csv](../templates/expert_variant_annotations.csv).

Required columns:

- `target_word`
- `ipa`

Recommended columns:

- `reference_ipa`
- `count`
- `source_type`
- `reviewer`
- `confidence`
- `validated`
- `label`
- `notes`

## Current Product Support

The backend now supports:

- JSON variant analysis: `POST /preference/analyze`
- CSV expert annotation import: `POST /preference/analyze-csv`
- CLI annotation batch creation from transcript CSVs.
- CLI PG analysis from a completed annotation CSV.

The frontend now supports manual expert metadata entry for each variant:

- source type
- reviewer
- confidence
- validated flag
- notes

## Local CLI Workflow

Build an annotation sheet from the existing transcript CSVs:

```bash
python3 scripts/build_annotation_batch.py \
  --target-word language \
  --source-csv voxpreference/data/train.csv \
  --source-csv voxpreference/data/val.csv \
  --output work/annotations/language_annotations.csv \
  --ipa-endpoint https://thebickersteth-voxpreference.hf.space/ipa \
  --prefill-reference \
  --max-rows 50
```

This creates rows with:

- target word
- optional reference IPA
- source audio path
- transcript context
- unvalidated IPA prefill, if requested

The reviewer must listen to the audio, replace `ipa` with the actual observed
target-word pronunciation, enter `reviewer`, set `confidence`, and set
`validated=true`.

If the OpenSLR audio files are present locally and Allosaurus is installed, an
unvalidated phone prefill can be attempted:

```bash
python3 scripts/build_annotation_batch.py \
  --target-word language \
  --source-csv voxpreference/data/train.csv \
  --output work/annotations/language_annotations.csv \
  --audio-root /path/to/openslr70 \
  --allosaurus \
  --prefill-reference
```

Run PG on a completed annotation CSV:

```bash
python3 scripts/analyze_annotations.py \
  work/annotations/language_annotations.csv \
  --output work/results/language_pg_result.json
```

The repository includes a small example template:

```bash
python3 scripts/analyze_annotations.py templates/expert_variant_annotations.csv
```

## What Remains To Fully Automate

The system can now run the full PG decision layer, but full automatic IPA
extraction still needs a validated label set. The next engineering stage should
add:

1. Audio clipping around target words.
2. MFA/WhisperX alignment as a helper.
3. Allosaurus or speech-to-IPA prefill.
4. Reviewer correction UI.
5. Inter-reviewer agreement and adjudication.
6. A small validated Nigerian English IPA dataset exported for model training.

Only after that should the project claim automatic pronunciation analysis.
