import numpy as np
from model.preprocessing.feature_extraction import extract_features
import tensorflow as tf

def load_dataset(file_list):
    """Loads and preprocesses dataset (MFCC features & text labels)."""
    X, y = [], []
    for audio_path, label in file_list:
        features = extract_features(audio_path)
        X.append(features)
        y.append(label)
    
    # Pad sequences to the same length
    X = tf.keras.preprocessing.sequence.pad_sequences(X, padding='post', dtype='float32')
    
    return np.array(X), y

def sparse_labels(y):
    """Convert text labels to sparse tensors for CTC loss."""
    indices = []
    values = []
    max_len = max(len(label) for label in y)
    for i, label in enumerate(y):
        for j, char in enumerate(label):
            indices.append([i, j])
            values.append(ord(char))  # Convert char to int
    shape = [len(y), max_len]
    return tf.SparseTensor(indices, values, shape)