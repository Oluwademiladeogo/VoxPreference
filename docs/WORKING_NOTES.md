# Working notes: everything that matters (written 20 Oct 2026, before context compaction)

Read this first if you are an agent picking up this work. The user is Demilade (they/them unless stated).
Talk to them the way ~/Downloads/AdminApp/AGENTS.md says: calm, plain, natural sentences, small words, no
jargon without explaining it; always say what you did, whether it worked, what they do now. Act on cheap,
reversible things without asking; ask before push, deploy, publish, send, or anything irreversible.
Do not commit unless asked. All work is uncommitted on branch `pg-pipeline`.

## The real goal
Automate Prof. C.U.C. Ugorji's Preference Grammar (PG) for Nigerian English. A user gives target word(s),
recordings (files, voice notes, or long podcasts), and their ranking of six tenets (I-Ac International
acceptance, ContR Contrastiveness, FreQ Frequency, DisaM Disambiguity, Pho-S Phonetic simplicity, Ped-C
Pedagogic convenience; default order in that sequence). The app must find the words, decide how each speaker
pronounced the sound (e.g. <th> in "think" as [θ] or [t]), count variants, and output Ugorji's "operability
table" (OT tableau) and the preferred pronunciation. Sources: user's decks/PRD in ~/Downloads/Telegram/, FYP
thesis PDF in ~/Downloads. Team: Ugorji, Dr Olamma Iheanetu (supervisor), the user.

## What was wrong with the old FYP pipeline (verified)
- wav2vec2-base-960h fine-tune never trained: transformers 4.51.3 leaves `masked_spec_embed` uninitialised
  (NaN) -> NaN loss every step, logged as 0.000000, LR stayed 0; HF model thebickersteth/wav2vec2-nigerian-english
  is byte-identical to facebook/wav2vec2-base-960h.
- Labels lowercased but vocab is uppercase: 100% <unk> (174,915 unk, 0 letters).
- Eval leakage: random split, all 31 speakers in train and val, 20% of val sentences in train. Published model
  WER on that split 36.7% (thesis says 41.10%; same deletion count 112 -> likely the same stock model).
- The design itself cannot do PG: ASR -> eSpeak gives dictionary IPA, erasing variants.
- Old HMM-GMM and Kaldi attempts were broken scaffolding.
- finetune_model.py and utils/split_shuffle_data.py are now fixed (uppercase labels, re-init vector, NaN guard,
  speaker split). Only a 30-step CPU check was run (loss 1.40 -> 0.72). NOT retrained in full.

## What exists now (all in repo)
- backend/pg/: audio, align (CTC letter alignment, wav2vec2-base-960h), asr (Whisper small via transformers for
  podcasts, + merger-neighbour aliases like tree->three), phones (core: facebook/wav2vec2-xlsr-53-espeak-cv-ft,
  forced-choice CTC scoring of candidate pronunciations; open set OFF by default), cluster (exploratory),
  tenets (rules that reproduce Ugorji's 'think' and GOAT tableaux exactly; freq_mode "threshold" default or
  "most_frequent"), ot (strict domination), pipeline (Analyzer; admission >=3 tokens/>=2 speakers; tiers;
  stability = bootstrap over speakers + redraw labels from posteriors), calibrate, report, review (listening
  tool), kb/ (units.json with validation status, typology.json from PHOIBLE, calibration.json = only TH-voiced),
  README.md, RESEARCH.md (sources + 10 open questions for PG experts).
- backend/eval/: saa_gold.py (gold test, 22 Nigerian Speech Accent Archive speakers, 753 tokens),
  fit_calibration.py (kappa-based validation + calibration), slr70.py, fetch_saa.py.
- backend/app.py: GET /pg/units, POST /pg/analyze (lock, upload limits), and serves the built frontend
  (VoxPreference-frontend/dist) from the same address. Dockerfile at repo root (NOT yet build-tested).
  backend/requirements.txt = Linux/live pins (torch 2.14, transformers 5.18; CI tests them incl. real models);
  backend/requirements-intel-mac.txt = laptop pins (torch 2.2.2, numpy<2, transformers 4.51.3); requirements-train.txt.
- Frontend PG view (default page): validation badges, ranking editor, podcast checkbox, frequency-mode choice,
  calibration toggle, PG-style table with OT toggle. Lint/build pass; checked live in Chrome.
- Tests: 39 backend tests pass: `cd backend && ~/.venvs/voxpref/bin/python -m pytest -q`.
- Env: ~/.venvs/voxpref (python), ~/.venvs/uvtool/bin/uv. Data: backend/data/ (gitignored; resources, work,
  results/slr70_v2). /private/tmp is wiped on reboot: never keep work there.

## Results (honest)
- Gold (kappa = agreement beyond chance): TH-voiceless 0.68, TH-voiced 0.64 (calibrated), KIT 0.55 = validated.
  NURSE 0.23, GOAT 0.16, FACE 0.13, FLEECE 0.06 = NOT validated (app warns).
- SLR70: TH-voiceless θ 52% t 36% (word-initial θ 48%, stops 48%; ICE-Nigeria lit θ 47% t 49%) -> [θ].
  TH-voiced d 57% ð 40% -> [ð] (d loses on DisaM). NURSE ɜː 36% ɛ 22% ɔ 17% a 15% (model biased to ɜː).
- Independent max-effort QA (report: backend/data/work/qa/QA_REPORT.md) found: fake GOAT/FACE calibrations
  (fixed), "same preferred form" is a weak test, model biased towards dictionary forms, open-set junk, stability
  ignored model error, aligner drift, ASR alias drop, memory/upload limits. All fixed or documented.

## Key thinking / gaps
- User's view of FreQ: "rank by frequency" = most frequent variant wins. Ugorji's 'think' table only works with
  the threshold reading (t 48.8% vs θ 47.2%). Both modes now exist; default = threshold. Ask Ugorji.
- Tenet marks in PG sources are expert judgement; our rules are configurable defaults fitted to two tableaux.
- No speaker separation (diarization): a podcast file counts as one speaker. Needed for per-speaker FreQ and
  stability. Next big feature.
- Vowels need better evidence: human labels on new words (150-300 tokens), maybe MFA english_mfa (trained on
  Nigerian English) or formants.

## In flight when this was written
- Subagent "podcast-test": finds a ~30-45 min Nigerian multi-speaker podcast on YouTube (user suggested
  "Honey Sponge"), downloads audio with yt-dlp into backend/data/work/podcast/, runs `python -m pg --asr` for
  TH-voiceless and TH-voiced, writes backend/data/work/podcast/PODCAST_TEST.md. Read that when it lands.
- Report for the user: docs/report/pg_pipeline_report.html -> pg_pipeline_report.pdf (rendered with headless
  Chrome). Section 9 needs the podcast results added, then re-render. The user mentioned putting it in
  "full PG main" or "full PG tool" (probably Google Drive folders; they think only they are in "full PG tool").
  Check Drive before uploading; uploading to a shared folder = ask first.
- Docker build not yet tested (needs memory; do after the podcast run).

## Added after the first notes (20 Oct, morning)
- Survey mode: `python -m pg --survey [--asr] --audio ... --out DIR` analyses EVERY sound in kb/units.json from
  the same recordings (target words chosen from the transcripts; weak function words skipped; 40 tokens per word
  cap); writes DIR/survey.md + survey.json + a folder per sound. Code: pg/pipeline.py `survey()`, pg/__main__.py.
- Whisper transcripts are cached in backend/data/cache/asr/ (keyed by audio), so a podcast is transcribed once.
- freq_mode setting: "threshold" (default, Ugorji) or "most_frequent" (user's reading). In UI advanced settings.
- Podcast under test: "Can a person love 2 people at the same time? - S2E2", The Frankly Speaking Podcast (now The Honest Bunch, Glitch Africa Studios), https://www.youtube.com/watch?v=qOk_DmEWejs, 43:11, panel of hosts; audio backend/data/work/podcast/qOk_DmEWejs.m4a (74 MB).
  The podcast-test agent was told to run survey mode twice (default ranking; FreQ-first most_frequent).
- Report HTML/PDF: docs/report/ (boxes restyled; must re-render after adding podcast + survey results).
  Re-render: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --no-pdf-header-footer
  --user-data-dir=/private/tmp/claude-501/chrome-pdf --print-to-pdf=docs/report/pg_pipeline_report.pdf file://<abs html path>
- User complaint to remember: answer every question they ask, and hand over deliverables (paths) explicitly.

## User's open questions to answer in the final reply
Did you retrain (no, why, how)? What changed in the approach? Is the whole pipeline ready end to end from the
frontend? Can everything be deployed together (yes: one process + Dockerfile, build untested)? Which models?
How do we move forward? Plus the podcast results.

## Added 20 Oct ~08:20 (after compaction; user was angry I re-derived instead of acting)
- Report published as a claude.ai artifact: https://claude.ai/artifact/51GnyXHozYMHGvNku5fFft
  (source docs/report/pg_pipeline_report_web.html = screen copy of pg_pipeline_report.html; republish same path).
  PDF also sent to the user. Update BOTH html files when adding results (web copy: regenerate or edit both).
- Speaker separation BUILT: backend/pg/diarize.py (microsoft/wavlm-base-plus-sv x-vectors on 1.5 s windows,
  0.75 s hop, speech from Whisper word times; agglomerative cosine clustering, threshold 0.6 or --num-speakers;
  small clusters folded; smoothing). Wired in pipeline.py: Recording.diarize (None = on for "auto" recordings
  without speaker id) and Recording.num_speakers; tokens get speaker "<file>:S1". Cached in data/cache/diarize/.
  CLI --no-diarize / --num-speakers; API form fields diarize, num_speakers; frontend checkbox + count.
  Capped words are now sampled evenly through the recording (pipeline._spread), not the first N.
  Tests: tests/test_diarize.py (44 total pass). Eval on synthetic SLR70 conversations: eval/diarize_eval.py
  -> data/work/diarize_eval.json/log.
- Diarization result (eval/diarize_eval.py): WavLM was weak (four women 71%); switched default to SpeechBrain ECAPA
  (speechbrain==1.0.3 added to both requirements files) + centring + 3-window context averaging + centroid
  refinement, threshold 0.9. Tuned on seed 0 (4 convs). HELD-OUT seed 1, 8 convs of 2-5 speakers, 4 min:
  100% of sampled words credited right, right speaker count 8/8 (data/work/diarize_heldout.json). Caveat:
  synthetic, each clip from separate recordings (channel differences help); same 31 SLR70 speakers pool.
- Podcast panel ground truth (from storyboard frames): 4 people, 2 men + 2 women, no guest.
- Deployment: HF account thebickersteth has NO payment method, $0 usage. Existing Space thebickersteth/voxpreference
  (public, CPU basic free 2 vCPU/16 GB, sleeps after 48 h idle) runs the OLD app, in Runtime error.
  scripts/deploy_space.sh stages to backend/data/work/space_build; `--push` uploads (needs `hf auth login`
  with a write token by the user). Dockerfile: chmod caches for uid 1000, PG_WARM=1 (app.py warms models at start),
  prefetches ECAPA + whisper-small. Local Docker daemon is not running; HF builds the image remotely.
- DEPLOYED 20 Oct ~09:10 (user asked; they logged in with a write token "Demi local" — they pasted it in chat,
  told them to rotate it). `hf upload` failed 402 (new Docker Spaces need PRO since mid-2026); uploaded with
  HfApi.upload_folder into the EXISTING Space (grandfathered free cpu-basic). Built in ~3 min, RUNNING on
  cpu-basic. Live: https://thebickersteth-voxpreference.hf.space (page + /pg/units OK; 12 SLR70 clips/6 speakers
  analysed in 18 s; 63 s 3-speaker synthetic podcast with asr+diarization in 48 s, 3 speakers found, 5/5 tokens
  credited consistently). scripts/deploy_space.sh --push still uses `hf upload` (create step) -> switch to upload_folder.
- Not done (needs user OK): daily keep-awake ping via GitHub Actions (commit + push).
- 20 Oct ~09:50: ONE REPO. PR #17 merged into main (all work). .github/workflows/ci-cd.yml: frontend lint/build +
  backend pytest on push/PR; on push to main deploys to the Space via HF Trusted Publishers (configured in Space
  settings: repo Oluwademiladeogo/VoxPreference, ref main, workflow ci-cd.yml; no HF_TOKEN secret); waits for
  RUNNING and curls /pg/units; daily keep-awake job (06:17 Lagos) that also re-enables the workflow. First auto
  deploy run 39395858170 succeeded. User refused to rotate the pasted token; respect that.
- Report is now a design review of the FULL PG tool (PRD, Prof's framework, user flow, decks; FYP = speech-to-text
  block only, outlined). No HMM-GMM/Kaldi. Black and white. 10 pages. Podcast section placeholder.
- Dependabot: many alerts from pinned torch 2.2.2 / transformers 4.51.3 (Intel-Mac pins) and python-multipart;
  the deployed image is Linux and could use newer pins (needs transformers 5 / torch 2.6+ validation in CI).

## 20 Oct afternoon: PG2 brought into THIS repo (user's direction)
- "PG2 / full PG" = github.com/ebube005/FULL_PG_TOOL (local ~/Documents/projects/FULL_PG_TOOL). The user wants
  ONE repo = this VoxPreference repo, built on PG2's frontend. Its frontend is now frontend/ here (VoxPreference-
  frontend removed); Ebube's pg_core.py + validation_import.py in backend/pg2/; templates/, scripts/, docs/pg2/.
- Scoring: user chose the new engine. /preference/analyze(-csv) run PG2's checks, then pg/pg2_bridge.py picks
  the preferred form by Ugorji's strict ranking (slider order = ranking; equal pooled; 0 deletes). Variants that
  don't line up with one sound fall back to PG2's weighted method with a warning.
- Variants page: "Find Variants in the Audio" (single-word clips or longer speech + speaker separation) fills the
  table with source "auto", unvalidated. Results page shows marks/outcome/why. Verified live end to end
  (3-speaker SLR70 mix: 2 think tokens, 3 speakers found, θɪŋk preferred, tɪŋk out at DisaM).
- Bug found live and fixed: cluster.two_level silhouette crashed with 2 tokens of 2 variants.
- 20 Oct ~15:00 DONE: podcast tested end to end on the live app with a 10-min cut (full-length reruns stopped at the
  user's request; they were annoyed by repeated long runs: prefer short cuts for end-to-end checks). Results in
  docs/PODCAST_TEST.md and report §Podcast test. Fixes found by it: windowed ASR, loop filter, M4A-from-bytes decode.
