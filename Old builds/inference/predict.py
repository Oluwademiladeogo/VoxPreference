import numpy as np
import tensorflow as tf
from transformers import TFWav2Vec2ForCTC, Wav2Vec2Processor
import librosa
import sys
from model.training.text_to_phoneme import text_to_phonemes
sys.path.append("/Users/thebickersteth/Desktop/projects/VoxPreference")

# Load pretrained wav2vec2 model and processor
processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base-960h")
model = TFWav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-base-960h", from_pt=True)

def predict(audio_path):
    audio_input, _ = librosa.load(audio_path, sr=16000)
    
    inputs = processor(audio_input, sampling_rate=16000, return_tensors="tf")
    
    logits = model(inputs.input_values).logits
    
    predicted_ids = tf.argmax(logits, axis=-1)
    
    # Decode the ids to text
    transcription = processor.batch_decode(predicted_ids.numpy())[0]
    return transcription

if __name__ == "__main__":
    audio_path = "/Users/thebickersteth/Desktop/projects/VoxPreference/data/SpeechFiles/ngf_00295_00053583157.wav"
    transcription = predict(audio_path)
    phonemes = text_to_phonemes(transcription.lower())
    print("Transcription:", transcription, "Phonemes:", phonemes)