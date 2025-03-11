import numpy as np
from model.preprocessing.feature_extraction import extract_features
from model.training.cnn_rnn_asr import asr_model
from model.training.text_to_phoneme import text_to_phonemes

def predict(audio_path):
    """Predict text from an audio file and convert to phonemes and IPA."""
    features = extract_features(audio_path)
    features = np.expand_dims(features, axis=0)  # Add batch dimension
    predictions = asr_model.predict(features)
    text_sequence = np.argmax(predictions, axis=-1)[0]
    text = ''.join([chr(c) for c in text_sequence if c != 0])  # Convert to string
    phoneme_sequence = text_to_phonemes(text)
    ipa_transcription = ' '.join(phoneme_sequence)
    return ipa_transcription