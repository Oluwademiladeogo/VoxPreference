# Automated Preference Grammar (`pg`)

Automates Ugorji's Preference Grammar (PG): from recordings of target words spoken by many speakers, it finds
which variants of a sound speakers actually produce, clusters them, ranks the attested variants on the six PG
tenets, and outputs the operability table and the preferred form.

```
recordings + target word(s) + tenet ranking
  -> locate the words: whole clip | forced alignment to a transcript | speech recognition   audio.py align.py asr.py
  -> which variant of the unit each token realises (acoustic forced choice + open set)      phones.py
  -> primary clusters (variants) and secondary clusters (acoustic sub-variants)             cluster.py
  -> candidates (attested >= 3 tokens from >= 2 speakers) with marks for the six tenets      tenets.py
  -> operability table (strict domination, as in OT) -> preferred form, tiers, stability    ot.py pipeline.py
  -> CSV / VTT / JSON / HTML outputs, and a listening page for human checking               report.py review.py
```

## Why not ASR + text-to-IPA

Converting recognised *words* to IPA (e.g. eSpeak) returns the dictionary pronunciation, so every speaker's
"think" comes out as /θɪŋk/ whatever they said. PG's input is the set of *attested* forms, so the variant has to
come from the audio. `phones.py` uses a multilingual CTC phone recogniser
(`facebook/wav2vec2-xlsr-53-espeak-cv-ft`) and makes a forced choice (the GOP-SF / PP-AF method of the
mispronunciation-detection literature): each candidate pronunciation of the word ([θɪŋk], [tɪŋk], [sɪŋk]…)
is scored by its CTC likelihood against the audio, over the usual spellings of each variant ([t]/[t̪]), with
the word's other vowels allowed to vary so an accent feature elsewhere cannot bias the decision. Low-confidence
tokens are flagged for listening. (An open-set option also scores the phones the model hears most in the slot, so a
realisation outside the candidate set is reported under its own symbol; it is off by default because it never
improved accuracy on the gold set.)

## Measured accuracy (Nigerian English): what is and is not validated

Development gold set: the 22 Nigerian speakers of the Speech Accent Archive, narrow IPA by trained phoneticians
(`python -m eval.saa_gold`, then `python -m eval.fit_calibration`). Figures are for the deployed closed-set
classifier; calibration is used only where it raised kappa on held-out speakers with a bootstrap interval above
zero (only /ð/). Kappa measures agreement beyond chance: a classifier that always answers the commonest variant
scores 0, however high its accuracy.

| Unit | Tokens | Accuracy (95% CI by speaker) | Majority baseline | Kappa | Error in variant shares | Status |
|---|---|---|---|---|---|---|
| <th> /θ/ | 85 | 82% (73–91) | 58% | 0.68 | 0.08 | validated |
| <th> /ð/ (calibrated) | 129 | 81% | 53% | 0.64 | 0.09 | validated |
| KIT | 112 | 81% (73–89) | 76% | 0.55 | 0.08 | validated |
| NURSE ("her") | 86 | 43% (24–63) | 41% | 0.23 | 0.41 | **not validated** |
| GOAT | 68 | 72% (60–84) | 87% | 0.16 | 0.13 | **not validated** |
| FACE | 89 | 54% (41–65) | 72% | 0.13 | 0.17 | **not validated** |
| FLEECE | 183 | 90% (86–94) | 92% | 0.06 | 0.05 | **not validated** |

For the not-validated units the acoustic evidence the phone model gives is weak (a class-balanced calibration does
not rescue them either), so analyses of those sounds carry a warning and their shares should be checked by ear.
Known limits, from an independent QA review:

- **Same paragraph, new speakers only.** Every speaker reads the same text, so these numbers show transfer to new
  speakers, not to new words; NURSE is tested only on "her", often a weak form. Treat the set as development data
  and validate on 150–300 double-labelled tokens of other words before publishing results.
- **The model leans towards dictionary forms.** It was trained on eSpeak transcriptions of Common Voice text,
  and its errors run towards RP (gold [d] heard as [ð] 36 times, the reverse once); its vocabulary has [t̪] but no
  [d̪]. Raw shares therefore overstate the RP variant; the /ð/ calibration corrects most of this.
- **"Same preferred form" is not an accuracy test.** With the default knowledge base the RP form wins NURSE, KIT
  and FLEECE whenever it is attested at all, and TH, GOAT and FACE hinge only on whether one share passes 20%.
  The stability figure redraws each token's variant from its posterior and resamples speakers, so it reflects
  classifier uncertainty, but only as far as the posteriors are honest (they are for the validated units).
- **Acoustic sub-clusters and the contrast matrix are exploratory**: they barely separate the variants.
- On Mandarin-L1 learners (speechocean762) TH/DH accuracy was 47%/53%: do not assume transfer to other accents.

## How each tenet is computed

The PG sources assign marks by analyst judgement and give no algorithm. These rules are a documented
operationalisation that reproduces both evaluations Ugorji published, mark for mark: <th> in "think"
(Ugorji 2010: 58) and the GOAT vowel (reported by Jowitt 2015: 8) (`tests/test_tenets.py`).

| Tenet | Mark when | Evidence |
|---|---|---|
| I-Ac | the variant is outside the internationally accepted realisations of the unit (e.g. /θ/: θ, t, t̪, f) | `kb/units.json` (RP/GA, established L1-variety norms, Lingua Franca Core, ICAO) |
| ContR | the variant neutralises a contrast crucial to international intelligibility: consonant contrasts except those of θ/ð, vowel length, the NURSE quality | Lingua Franca Core (Jenkins 2000; Walker 2010) |
| FreQ | the variant's share of tokens (or of speakers' usage) is below 20% | the analysed recordings |
| DisaM | the variant merges the unit with another RP phoneme so that common words sound alike (the target word's homophones, or minimal pairs among the 20,000 most frequent words) | CMUdict + Britfone, `wordfreq` |
| Pho-S | the variant is absent from at least two of Hausa, Igbo, Yoruba, or occurs in under 15% of the world's languages | PHOIBLE 2.0 |
| Ped-C | the variant is absent from those languages and used by under 20% of the speakers analysed (no local model to teach from), or experts list it as difficult | PHOIBLE + data |

These marks are configurable defaults pending the PG experts' judgement, not PG's own verdicts: the rules were chosen so that the only two published evaluations come out right (a fit to seven candidates, not a validation), and conventions decide some outcomes. For example, Nigerian [e] and [o] are treated as non-RP phonemes; under Gimson's notation, where RP DRESS is /e/, FACE [e] would merge with DRESS and lose to [eɪ]. The open questions are listed in `RESEARCH.md` §6.

Default ranking `I-Ac >> ContR >> FreQ >> DisaM >> Pho-S >> Ped-C`. Experts can override any mark
(`Settings.overrides`, e.g. `{"t|DisaM": 0}`), re-rank, pool tenets into one stratum (`"I-Ac, ContR >> FreQ"`),
or delete tenets. Results depend on who was recorded: FreQ measured on less-educated speech can flip "think"
to [t] (θ ≈ 16% there; Akande 2005), so the analysis reports how often the preferred form wins when the
speakers are resampled (`stability`). Losing candidates are classed as allophones of the formal inventory
(no I-Ac or ContR mark) or as the outer norm.

## Use

```bash
# single-word recordings (one file per speaker), unit inferred from the word
python -m pg --words think --audio recordings/*.wav --out results/
# sentences with transcripts (TSV: file name<TAB>transcript), a lexical set, a different ranking
python -m pg --words bird,work,girl --unit NURSE --audio clips/*.wav --transcripts transcripts.tsv \
  --speakers speakers.tsv --ranking "FreQ >> I-Ac >> ContR >> DisaM >> Pho-S >> Ped-C" --out results/
# unscripted audio (podcasts, interviews): words are found by speech recognition
python -m pg --words think,three,thing --unit TH-voiceless --asr --audio episode1.mp3 --out results/
# listen to the tokens and label them, then measure accuracy against your labels
python -m pg.review export results/analysis.json recordings/*.wav --out review/
python -m pg.review score results/analysis.json labels.csv
```

The API (`app.py`) exposes `GET /pg/units` and `POST /pg/analyze` with the same options.

Outputs: `operability_table.csv`, `tokens.csv` (every token with variant, confidence, clusters),
`subclusters.csv` (members of each sub-cluster; the phoneme under study is at cell (0,0)),
`contrast_matrix.csv` (cosine similarity between variant clusters), one `.vtt` per recording,
`analysis.json`, and `report.html`.

## Setup

`pip install -r requirements.txt` (on an Intel Mac: `requirements-tested.txt`, which pins the last
PyTorch with Intel wheels). The lexicons download on first use (`python -m pg.kb.fetch`); models download from
Hugging Face. `kb/typology.json` is built from PHOIBLE by `python -m pg.kb.build_typology`.
Tests: `pytest` in `backend/`. Reproduce the evaluation: `python -m eval.fetch_saa`, `python -m eval.saa_gold`, `python -m eval.fit_calibration` (add `--write` to refresh `kb/calibration.json` and the validation status in `kb/units.json`); SLR70 inputs: `python -m eval.slr70`.
