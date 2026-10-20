# Podcast test: PG pipeline on a real Nigerian panel podcast (20 Oct 2026)

## Bottom line

No full-podcast PG result was produced. Running the pipeline on the full 43 minutes showed problems instead: two crashes in Whisper, about 15% of the transcript invented by Whisper repetition loops, and runs too slow to repeat on this 8 GB Intel Mac. The crash and the loops are now fixed in `pg/asr.py`. The full-length reruns were then stopped at the user's request in favour of a 10-minute cut through the live app (`podcast_10min.m4a`, results added separately).

## The podcast

| | |
|---|---|
| Title | Can a person love 2 people at the same time? - Season 2, Episode 2 |
| Show / channel | The Frankly Speaking Podcast (now "The Honest Bunch"), Glitch Africa Studios |
| URL | https://www.youtube.com/watch?v=qOk_DmEWejs |
| Duration | 43:11 (uploaded 2022-06-20, about 93k views) |
| File | `qOk_DmEWejs.m4a`, 74 MB, AAC 48 kHz stereo (audio only) |
| Speakers (ground truth) | 4 panellists for the whole episode, 2 men and 2 women, no guest (checked on the YouTube storyboard frames) |

Why this one: searching "honey sponge podcast" found nothing by that name. The closest match was Glitch Africa's *Honest Bunch*, probably the show the user meant. Its recent episodes run 2–4 hours. The older *Frankly Speaking* episodes are 30–55 minutes, hosts only, mostly English with some Pidgin and Yoruba. This one fits the brief: 43 minutes, four speakers, and a conversational topic.

Download: `yt-dlp --js-runtimes node:<path> -f bestaudio -x --audio-format m4a` took 1.5 minutes. yt-dlp now needs a JavaScript runtime for YouTube; deno is the default, and node works when given with `--js-runtimes`.

## Runs and timings

| Run | Started | Code | Outcome | Time |
|---|---|---|---|---|
| TH-voiceless `--asr` (26 words) | 07:29 | before transcript cache | **crashed** at the end of transcription (crash 1) | 95.6 min wall, peak memory 5.1 GB |
| survey `--survey --asr` | 09:05 | cache, old diarization (Whisper word times) | **crashed** in the same place (crash 1) | 77.4 min, peak 5.1 GB |
| survey freq-first | 10:22 | same | killed at about 10:56: it would have hit crash 1 again | – |
| survey `--survey --asr` | 11:08 | crash-safe `asr.py` (own 30 s windows) | transcription **finished**, 0 failed windows; diarization finished; killed during analysis because its counts included Whisper loops | transcription 86 min (11:08–12:34), diarization 12 min (to 12:46), analysis more than 34 min before it was stopped |
| survey `--survey --asr` | 13:22 | commit 009fb6e (loop filter, clustering fix) | killed at the user's request (switch to the 10-minute test) | – |

The separate TH-voiced run was dropped, because the survey covers it. freq-first and the known-4-speakers run (`--num-speakers 4`) never started. Swap use peaked at 6.8 GB during these runs, so the machine was under heavy memory pressure the whole time.

## Problems found

**Crash 1: Whisper long-form merge (fixed).** With `chunk_length_s=30` and `return_timestamps="word"`, the transformers pipeline crashes when it merges overlapping chunks, after the whole file has been transcribed:
`tokenization_whisper.py:1215 _find_longest_common_sequence -> TypeError: '<=' not supported between instances of 'NoneType' and 'float'`.
This is deterministic for this audio, so 95 minutes and then 77 minutes of work were lost, with nothing cached. *Fix (now in `pg/asr.py`):* the pipeline uses its own 30 s windows with 2 s overlap and no pipeline merging. Each window is appended to a `.partial.jsonl` file so a rerun resumes, and a failing window is skipped with a warning instead of killing the run. On the rerun, no window failed (0 "speech recognition failed" warnings). Whisper printed "did not predict an ending timestamp" 88 times, which is harmless.

**Crash 2: clustering with very few tokens (fixed, reported by the main session; I did not see it myself).** `silhouette_samples` raised an error when a sound had, for example, 2 tokens of 2 variants, and that killed the whole survey. It is fixed in `pg/cluster.py` (commit 4c1bbd6).

**Whisper repetition loops (fixed).** On this conversational audio, whisper-small gets stuck repeating a phrase. The cached transcript had:

| Loop | Repeats | At |
|---|---|---|
| "no" | 94 | 3:09 |
| "i like this" | 103 | 16:55 |
| "he buys" | 119 | 27:55 |
| "she's saying" | 144 | 37:32 |
| "i'm not sure" | 68 | 39:32 |
| "not reliable it's" | 32 | 38:50 |
| "here are you guys" | 20 | 20:33 |
| "why do you think so" (stacked at one timestamp) | many | 34:02 |

2,124 words had zero length, mostly loops stacked on one timestamp (155 at 34:02, 149 at 39:38, 134 at 23:15). `drop_loops()` (commit 009fb6e) removes any 1–8-word phrase repeated more than 3 times in a row, and drops zero-length words. The loops would have produced fake target-word tokens:

| | Before | After |
|---|---|---|
| All words | 8,602 | 6,392 |
| TH-voiceless target hits | 163 | 110 |
| "think" | 68 | 25 (43 came from the "why do you think so" loop) |
| "thank" | 14 | 6 |
| TH-voiced target hits | 499 | 404 |
| "this" | 183 | 101 (most of the rest came from "i like this" x103) |

**Gaps with no words.** There are 13 stretches over 20 s with no transcribed words, about 7 minutes in total: 7:49–8:24, 8:24–8:46, 10:13–10:44, 13:33–14:01, 16:20–16:49, 19:54–20:33, 30:21–30:48, 31:45–32:13, 32:41–33:08, 35:01–35:57, 39:41–40:08, 40:55–41:33 and 42:00–42:28. Some are probably the loops' own windows (the loop replaced real speech), some may be Pidgin or Yoruba stretches, and some may be crosstalk. None of the target words in them can be found.

**Code-switching.** Yoruba and Pidgin are forced into English words ("ejo watra", "tibbaba", "paceful"). Target words inside those stretches are lost or mislocated.

**Speakers.** The panel is 4 people. The speaker count the pipeline found is not reported here, because no survey reached its output. The 11:08 run did cache speaker turns (speechbrain ECAPA, automatic count, loudness-based speech), but they were not inspected. Before diarization was added, the whole file counted as one speaker, so the minimum-speaker rule (a variant needs at least 2 speakers) and the stability resampling (needs at least 3 speakers) could not work.

**Code changing under running jobs.** Files were edited while runs were in progress. Python had already loaded the modules, so each run used the code from its start time, but tracebacks printed the new source lines. That is confusing when reading the logs, so record each run's start time and commit.

## What should change

1. Make a long podcast affordable on this machine. Transcription alone is about 2x real time (86 min for 43 min of audio), and 5 GB peak memory plus swapping slows everything else. Options: whisper-base or distil-whisper for the search pass, or transcribe only once and cache it (now done). Print progress per stage, because a run currently gives no sign of life for an hour or more.
2. Keep `drop_loops()`, and also stop loops at the source when transcribing next time: `condition_on_prev_tokens=False`, `compression_ratio_threshold=2.4`, `no_repeat_ngram_size`.
3. Report gaps and loop removals in the analysis warnings, so the user knows how much of the audio was actually searched.
4. For code-switched speech, consider dropping target hits whose neighbours are not English words, or using a Nigerian-English ASR model.
5. Save the transcript next to the results (for example `transcript.txt` with times), so hits can be checked against what Whisper heard.

The live app now fills PG2's variants page from audio, so the same path can be tried from the browser on short clips such as the 10-minute cut.

Logs: `attempt1/` (crashed TH-voiceless and survey runs), `attempt2/` (11:08 run), `attempt3/` (13:22 run), `mem_samples.log`. Transcript cache: `backend/data/cache/asr/openai_whisper-small_0be9f71498f7c7248760.json`.

## 10-minute cut through the live app (added by the main session, 20 Oct 2026)

First 600 s of the episode, uploaded as M4A to https://thebickersteth-voxpreference.hf.space (`/pg/analyze`, asr, diarize,
num_speakers=4). Needed three fixes first, all now in `main` with tests: windowed transcription, the repetition-loop
filter (only words stacked on one timestamp are dropped), and decoding uploaded M4A through a temporary file (it had
decoded to 0 s of audio without an error).

| Sound | Words found | Variants | Preferred (strict ranking) | Stable |
|---|---|---|---|---|
| TH-voiceless | 19 | θ 7, t 7, d 4, s 1 | [θ] | 97% |
| TH-voiced | 73 | d 57, ð 7, z 4, t 2, θ 2, v 1 | [d] | 99% |

Tokens per speaker label: voiceless S1 6, S2 3, S4 4, unknown 6; voiced S1 28, S2 19, S3 1, S4 13, unknown 12.
18 of 92 tokens had no speaker (outside the separated turns). Transcribing 10 minutes on the free CPU took 22 minutes.
