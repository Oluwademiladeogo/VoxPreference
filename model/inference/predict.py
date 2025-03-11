import torch
import numpy as np
from model.preprocessing.feature_extraction import extract_features
from model.training.cnn_rnn_asr import CNNRNNASR
from model.training.phoneme_to_ipa import phoneme_to_ipa_conversion

# Load the trained model
input_dim = 40
num_phonemes = 50
asr_model = CNNRNNASR(input_dim, num_phonemes)
asr_model.load_state_dict(torch.load("asr_model.pth"))
asr_model.eval()

def predict(audio_path):
    """Predict phonemes from an audio file and convert to IPA."""
    features = extract_features(audio_path)
    features = torch.tensor(features, dtype=torch.float32).unsqueeze(0)  # Add batch dimension
    with torch.no_grad():
        predictions = asr_model(features)
    phoneme_sequence = torch.argmax(predictions, dim=-1).squeeze(0).tolist()
    ipa_transcription = phoneme_to_ipa_conversion(phoneme_sequence)
    return ipa_transcription