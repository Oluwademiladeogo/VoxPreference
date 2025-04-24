import numpy as np
import tensorflow as tf
from model.preprocessing.feature_extraction import extract_features

def load_dataset(file_list):
    """Loads and preprocesses dataset (MFCC features & text labels)."""
    X, y = [], []
    for audio_path, label in file_list:
        features = extract_features(audio_path)
        X.append(features)
        y.append(label)
    return X, y  # Return X as a list, not an array

def create_char_mapping(labels):
    """Create a character-to-index mapping."""
    # Include space and special characters
    chars = set()
    for text in labels:
        for char in text:
            chars.add(char)
    
    # Create mapping - reserve 0 for CTC blank
    char_to_idx = {'<blank>': 0}
    for i, char in enumerate(sorted(chars)):
        char_to_idx[char] = i + 1  # Start from 1, 0 is reserved for blank
    
    return char_to_idx