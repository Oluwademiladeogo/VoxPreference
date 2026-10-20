# VoxPreference

Automates Prof. C.U.C. Ugorji's Preference Grammar (PG) for Nigerian English. You give target words, recordings
(single words, voice notes or whole podcasts) and a ranking of the six tenets; the tool hears how each speaker
pronounced the sound, counts the variants, and returns the operability table and the preferred pronunciation.

**Live:** https://thebickersteth-voxpreference.hf.space

## What is where

| Path | What it is |
|---|---|
| `backend/pg/` | The pipeline: finding the words, scoring pronunciations, speaker separation, the six tenets, the operability table. Details in `backend/pg/README.md`; sources and open questions in `backend/pg/RESEARCH.md`. |
| `backend/eval/` | How it was tested: phoneticians' labels (Speech Accent Archive), SLR70, the speaker-separation test. |
| `backend/tests/` | Automatic tests; `test_models.py` runs the real models on six Nigerian recordings. |
| `backend/app.py` | The API (`/preference/analyze`, `/preference/analyze-csv` for the PG2 pages; `/pg/units`, `/pg/analyze` for audio), which also serves the web page. |
| `frontend/` | The web app: the PG2 pages from FULL_PG_TOOL (Evidence → Variants → Tenets → Results). |
| `backend/pg2/`, `templates/`, `scripts/`, `docs/pg2/` | PG2's scoring of attested variants and expert-annotation CSV import (Ebube's engine from FULL_PG_TOOL), its annotation template, scripts and design notes. |
| `docs/report/` | The project report (PDF and HTML). |
| `Dockerfile`, `scripts/deploy_space.sh` | One image for the whole app, and the upload to Hugging Face. |
| `backend/finetune_model.py`, `text_to_ipa.py` | The final-year-project transcription model (still served at `/transcribe`). |

## Run it on your machine

```bash
cd backend
pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt   # Intel Mac: requirements-intel-mac.txt
python -m pg.kb.fetch
cd ../frontend && npm ci && npm run build && cd ../backend
uvicorn app:app --port 8000        # then open http://localhost:8000
```

Command line, e.g. a podcast: `python -m pg --survey --asr --audio podcast.m4a --out results/` (add `--num-speakers 4`
if you know how many people talk).

## Tests and deployment

Every push and pull request runs the web-page build, the backend tests and the real-model checks on GitHub Actions.
Every push to `main` that passes is deployed to the Hugging Face Space automatically (no stored token: the Space
trusts this repository's `ci-cd.yml` on `main`). A daily job visits the Space so the free hardware does not sleep.
