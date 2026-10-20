from dataclasses import asdict
import threading
from typing import List, Optional
import json
import os
from pathlib import Path
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import io
import librosa
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
from text_to_ipa import convert_to_ipa
import torch
from pg import audio as pg_audio
from pg.ot import DEFAULT_RANKING, TENET_NAMES, TENETS, parse_ranking
from pg.report import contrast_csv, html_report, subclusters_csv, tokens_csv
from pg.tenets import load_units, settings_from

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_asr = None


def get_asr():
    global _asr
    if _asr is None:
        processor = Wav2Vec2Processor.from_pretrained("thebickersteth/wav2vec2-nigerian-english")
        model = Wav2Vec2ForCTC.from_pretrained("thebickersteth/wav2vec2-nigerian-english").eval()
        _asr = (processor, model)
    return _asr

FRONTEND_DIST = Path(os.environ.get("FRONTEND_DIST", Path(__file__).resolve().parents[1] / "VoxPreference-frontend" / "dist"))


if not FRONTEND_DIST.is_dir():
    @app.get("/")
    def root():
        return {"message": "Welcome! This API is for transcription. Try /health or /transcribe."}


@app.get("/health")
def health():
    return {"status": "ok"} 

@app.post("/transcribe")
async def transcribe(audioFile: UploadFile = File(...)):
    try:
        audio_bytes = await audioFile.read()
        audio_input, _ = librosa.load(io.BytesIO(audio_bytes), sr=16000)
        processor, model = get_asr()
        inputs = processor(audio_input, sampling_rate=16000, return_tensors="pt")
        with torch.no_grad():
            logits = model(inputs.input_values).logits
            predicted_ids = torch.argmax(logits, dim=-1)
        transcription = processor.batch_decode(predicted_ids.numpy())[0]
        ipa_result = convert_to_ipa(transcription)
        ipa = ipa_result["ipa"] if ipa_result["success"] else None
        ipa_error = ipa_result["error"] if not ipa_result["success"] else None
        print(transcription, ipa, ipa_error)
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "transcription": transcription,
                "ipa": ipa,
                "ipa_error": ipa_error
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


_analyzer = None
# one analysis at a time: the models take ~2 GB and every analysis uses all CPU cores
_analysis_lock = threading.Lock()
MAX_FILES = 300
MAX_FILE_BYTES = 50 * 1024 * 1024


_analyzer_lock = threading.Lock()


def get_analyzer():
    # the phone model is large, so it loads on the first PG request, or in the background at start-up
    # when PG_WARM=1 (the Docker image sets it, so a woken Space is ready sooner)
    global _analyzer
    with _analyzer_lock:
        if _analyzer is None:
            from pg.pipeline import Analyzer
            _analyzer = Analyzer()
    return _analyzer


@app.on_event("startup")
def _warm_up():
    if os.environ.get("PG_WARM") == "1":
        threading.Thread(target=lambda: get_analyzer().aligner, daemon=True).start()


@app.get("/pg/units")
def pg_units():
    return {
        "units": {k: asdict(u) for k, u in load_units().items()},
        "tenets": [{"key": t, "name": TENET_NAMES[t]} for t in TENETS],
        "default_ranking": DEFAULT_RANKING,
    }


@app.post("/pg/analyze")
def pg_analyze(
    files: List[UploadFile] = File(...),
    words: str = Form(...),
    unit: Optional[str] = Form(None),
    ranking: str = Form(DEFAULT_RANKING),
    transcripts: Optional[str] = Form(None),
    speakers: Optional[str] = Form(None),
    settings: Optional[str] = Form(None),
    asr: bool = Form(False),
    diarize: bool = Form(True),
    num_speakers: Optional[int] = Form(None),
):
    """files: recordings; words: comma-separated target words; transcripts/speakers: JSON objects
    keyed by file name (omit transcripts for single-word recordings; "auto" or asr=true finds the
    words in unscripted audio by speech recognition); diarize: separate the speakers inside unscripted
    recordings that have no speaker id; num_speakers: how many talk in each, if known; settings: JSON
    tenet thresholds."""
    from pg.pipeline import Recording
    try:
        config = settings_from(json.loads(settings) if settings else None)
        parse_ranking(ranking)
        if len(files) > MAX_FILES:
            raise ValueError(f"at most {MAX_FILES} recordings per analysis")
        transcript_of = json.loads(transcripts) if transcripts else {}
        speaker_of = json.loads(speakers) if speakers else {}
        if num_speakers is not None and not 1 <= num_speakers <= 20:
            raise ValueError("num_speakers must be between 1 and 20")
        recordings = []
        for f in files:
            data = f.file.read(MAX_FILE_BYTES + 1)
            if len(data) > MAX_FILE_BYTES:
                raise ValueError(f"{f.filename} is larger than {MAX_FILE_BYTES // 2**20} MB")
            try:
                audio = pg_audio.load(data)
            except RuntimeError as e:
                raise ValueError(f"{f.filename}: {e}") from e
            recordings.append(Recording(f.filename, audio, speaker=speaker_of.get(f.filename, ""),
                                        transcript=transcript_of.get(f.filename, "auto" if asr else ""),
                                        diarize=None if diarize else False, num_speakers=num_speakers))
        with _analysis_lock:
            result = get_analyzer().analyse(recordings, words.split(","), unit or None, ranking, config)
    except (ValueError, KeyError) as e:
        return JSONResponse(status_code=400, content={"success": False, "error": str(e).strip("'\"")})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
    body = result.to_dict()
    body["success"] = True
    body["files"] = {
        "tokens.csv": tokens_csv(result),
        "subclusters.csv": subclusters_csv(result),
        "contrast_matrix.csv": contrast_csv(result),
        "operability_table.csv": result.tableau.to_csv() if result.tableau else "",
        "report.html": html_report(result),
    }
    return body


# the built frontend (npm run build) is served from the same address as the API, so one process is the whole app
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
