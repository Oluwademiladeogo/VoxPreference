import librosa
import numpy as np

def extract_features(audio_path, sr=16000, n_mfcc=40):
    """Extract MFCC features from an audio file."""
    y, sr = librosa.load(audio_path, sr=sr)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
    return np.transpose(mfcc)  # Shape (time, features)
