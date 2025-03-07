import numpy as np
from model.preprocessing.feature_extraction import extract_features

def load_dataset(file_list):
    """Loads and preprocesses dataset (MFCC features & phoneme labels)."""
    X, y = [], []
    for audio_path, label in file_list:
        features = extract_features(audio_path)
        X.append(features)
        y.append(label)
    return np.array(X), np.array(y)
