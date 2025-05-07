from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import io
import librosa
from transformers import TFWav2Vec2ForCTC, Wav2Vec2Processor
from wav2vec2.utils.text_to_ipa import convert_to_ipa
import tensorflow as tf

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base-960h")
model = TFWav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-base-960h", from_pt=True)

@app.post("/transcribe")
async def transcribe(audioFile: UploadFile = File(...)):
    try:
        audio_bytes = await audioFile.read()
        audio_input, _ = librosa.load(io.BytesIO(audio_bytes), sr=16000)
        inputs = processor(audio_input, sampling_rate=16000, return_tensors="tf")
        logits = model(inputs.input_values).logits
        predicted_ids = tf.argmax(logits, axis=-1)
        transcription = processor.batch_decode(predicted_ids.numpy())[0]
        ipa_result = convert_to_ipa(transcription)
        ipa = ipa_result["ipa"] if ipa_result["success"] else None
        ipa_error = ipa_result["error"] if not ipa_result["success"] else None
        print(transcription, ipa, ipa_error)
        return {
            "success": True,
            "transcription": transcription,
            "ipa": ipa,
            "ipa_error": ipa_error
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/health")
def health():
    return {"status": "ok"} 