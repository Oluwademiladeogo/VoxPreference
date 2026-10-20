# Research notes behind the `pg` pipeline

Condensed from three research passes (October 2026): the Preference Grammar sources, open data, and
phone-recognition models. "[S]" = read in a source; "[P]" = our proposal, not in any PG source.

## 1. Preference Grammar as published

Sources actually read: Avram (2014) review of Ugorji (2010), *BWPL* XVI(1): 119–121; Jowitt (2015) "Nigerian
Received Pronunciation", REAL Studies 9: 3–13 (publisher preview); Benjamin-Ohwodede & Osewa (2023) *Marang* 36:
61–78 (Konglish, 9 tableaux); Benjamin-Ohwodede & Ugorji (2026) *JOLLS* 15(2): 239–248 (Naijá). Not accessible:
Ugorji (2010) *Nigerian English Phonology: A Preference Grammar* (Peter Lang), Ugorji (2013) in *JEIL* 8(2), the
"Ugorji 2022" title.

- [S] PG evaluates contending sounds with Optimality-Theory machinery: six parameters ranked
  I-Ac >> ContR >> FreQ >> DisaM >> Pho-S >> Ped-C, violable, the winner joins the normative inventory
  (Jowitt 2015: 8). Candidates are attested surface forms only (no underlying forms, no GEN).
- [S] Evaluation is **strict domination**, not counting marks: in Konglish Table 12, θ wins with three marks over
  s with two because s violates I-Ac. Ties are broken by rank.
- [S] No source gives an algorithm, threshold or numeric "operability" index; marks are analyst judgement
  ("descriptive and non-numerical"). Jowitt (2015: 9) asks on what basis I-Ac is assigned and how candidates
  enter the list. Ugorji (2010: 80): evaluation "need not be exhausted", so blank cells in published tables
  may mean "not evaluated".
- [S] Published evaluations by Ugorji: <th> in *think* (2010: 58): tɪŋk {DisaM}, sɪŋk {I-Ac, FreQ, DisaM},
  ⇒θɪŋk {Pho-S}, zɪŋk {I-Ac, FreQ, DisaM}. GOAT (via Jowitt 2015: 8): /o/ satisfies all six and wins; /əʊ/
  violates FreQ, Pho-S, Ped-C; /ɒ/ (phonetically [ɔ]) violates I-Ac, ContR, FreQ, DisaM.
- [S] Output classes (Benjamin-Ohwodede & Osewa 2023): formal standard (winner), allophones of the formal
  inventory, informal/outer norm, developmental/regional forms. The sources apply these inconsistently.
- [S] For Naijá, I-Ac is judged against Naijá itself, so TH-stopping wins there (B-O & Ugorji 2026): the
  reference norm is a parameter of the analysis.

## 2. The operationalisation used here [P]

Chosen because it reproduces both Ugorji evaluations exactly (`tests/test_tenets.py`); every threshold is a
setting, every mark can be overridden.

- I-Ac: accept-sets per unit (θ → θ, t, t̪, f): RP/GA plus realisations that are established norms in L1
  varieties (stopping in Irish, Caribbean, Liberian English; fronting in London) or sanctioned in ICAO
  "airspeak". The Lingua Franca Core alone cannot decide: Jenkins (2000) treats /θ ð/ as non-core and
  weighs [t d], [f v], [s z] without choosing.
- ContR: the variant neutralises a contrast the LFC treats as core (consonants except θ/ð; vowel length;
  the NURSE quality). This is the least settled tenet: the Konglish tableaux contradict every rule tried.
- FreQ: share below 20%. **The population decides results**: ICE-Nigeria word-initial /θ/ is θ 47.2%,
  t 48.8%, s 4.0%, z 0 (Oyebola, Ho & Li 2019), but among Yoruba undergraduates θ is about 16% (Akande 2005),
  where *think* flips to [t].
- DisaM: merger with another RP phoneme that loses minimal pairs among common words (Britfone: θ~t 52,
  θ~s 36, θ~z 25, əʊ~ɒ 56 pairs).
- Pho-S: absent from at least 2 of Hausa, Igbo, Yoruba (PHOIBLE), or under 15% of the world's languages
  (θ 3.4%, ð 4.8%, t 76%, s 70%, z 29%, ɜ 0.9%).
- Ped-C: substrate-absent and used by under 20% of the speakers analysed.

## 3. Nigerian English facts used in the knowledge base

- /θ/: [t]/[t̪] (south, Igbo most), [θ] (acrolect; Yoruba 60%), [s] (Hausa 14%); [z] unattested.
  /ð/: [d] (south), [z] (Hausa, reading). Udofot; Muhammad-Gombe (2019); Oyebola et al. (2019).
- NURSE (9 Igbo men, ICE-Nigeria): [ɛ] 40%, [a] 31%, [ɔ] 16%, [ɜ] 8%, [e] 5%, spelling-led
  (Jamakovic & Fuchs 2019). GOAT [o] 50%, FACE [e] 51%; KIT and FLEECE both [i].
- MFA's english_nigeria dictionary (CC BY 4.0) gives learned variant probabilities: *think* t̪ 0.99 / θ 0.59,
  *bird* b aː d, *work* w ɔ k.

## 4. Data

- Speech Accent Archive (OSF, CC BY-NC-SA 4.0): 22 Nigerian-L1 speakers with narrow IPA as text, same paragraph;
  the only Nigerian gold with realised phones we found. `eval/saa_gold.py` uses it.
- SLR70 (CC BY-SA 4.0): 3,359 read utterances, 31 speakers, 5.77 h. No phone labels.
- speechocean762 (CC BY 4.0): Mandarin-L1 learners (many children); realised-phone labels only in the GitHub
  `scores.json`, few on TH/DH.
- Not used yet: L2-ARCTIC (request form, CC BY-NC 4.0), AfriSpeech-200 (gated, CC BY-NC-SA, 142 h Nigerian),
  ICE-Nigeria (CC BY-NC-SA, 18 GB audio, ethnicity metadata), SautiDB (restricted). Licences matter for podcasts too.

## 5. Models and platform

- Phone model `facebook/wav2vec2-xlsr-53-espeak-cv-ft` (Apache-2.0). Forced-choice CTC scoring is the GOP-SF / PP-AF
  method (Parikh et al. 2025 used this model; Cao et al. CTC-based GOP); mispronunciation-detection F1 on
  L2-ARCTIC is about 60–70 in the literature. Known weakness here: dental stops [t̪ d̪] are heard as [ð]/[θ].
- Intel Mac: torch 2.2.2 is the last wheel, needs numpy<2; transformers ≥4.52 refuses `.bin` weights under
  torch<2.6; faster-whisper and torch crash in one process (use transformers' Whisper). MFA installs only via conda.

## 6. Questions only the PG experts can answer

1. Which norms count for I-Ac (RP, GA, LFC, L1-variety attestation)? Why is [t] spared I-Ac in *think* but not [s]?
2. What separates ContR from DisaM?
3. DisaM scope: systemic merger (thin/tin) or homophony of the word itself (think/sink)?
4. FreQ: token or speaker frequency, over which population (all lects or the acrolect), what threshold, per word
   or per phoneme class?
5. Pho-S: universal complexity or relative to the substrate languages? How are diphthongs treated?
6. Ped-C: what evidence counts (teachers' production, acquisition, spelling, curriculum)?
7. Candidate admission: minimum attestation? Who defines the phonological space? Should zɪŋk be a candidate?
8. Binary or graded marks? Ties: free variation or expert decision? Does a blank cell mean satisfied?
9. Rules for allophone vs outer vs developmental tiers; which reference norm for Naijá.
10. Prosody (stress, rhythm, syllable structure): no published tableau found.
