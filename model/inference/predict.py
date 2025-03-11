import numpy as np
from model.preprocessing.feature_extraction import extract_features
from model.training.cnn_rnn_asr import asr_model
from model.training.phoneme_to_ipa import phoneme_to_ipa_conversion

def predict(audio_path):
    """Predict phonemes from an audio file and convert to IPA."""
    features = extract_features(audio_path)
    features = np.expand_dims(features, axis=0)  # Add batch dimension
    predictions = asr_model.predict(features)
    phoneme_sequence = np.argmax(predictions, axis=-1)[0]
    ipa_transcription = phoneme_to_ipa_conversion(phoneme_sequence)
    return ipa_transcription

