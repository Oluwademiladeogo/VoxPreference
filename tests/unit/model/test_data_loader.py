import pytest
import numpy as np
from unittest.mock import patch
from model.preprocessing.data_loader import load_dataset

@patch("model.preprocessing.feature_extraction.extract_features")
def test_load_dataset(mock_extract_features):
    mock_extract_features.return_value = np.random.rand(50, 40)  # (time, features)

    file_list = [("audio1.wav", "hello"), ("audio2.wav", "world")]
    X, y = load_dataset(file_list)

    assert isinstance(X, np.ndarray) and isinstance(y, np.ndarray), "X and y should be NumPy arrays"
    assert X.shape[0] == len(file_list), "X should have as many samples as the file list"
    assert y.shape == (len(file_list),), "y should be a 1D NumPy array of labels"

@patch("model.preprocessing.feature_extraction.extract_features")
def test_load_dataset_empty(mock_extract_features):
    X, y = load_dataset([])
    assert X.size == 0 and y.size == 0, "Should return empty arrays for empty dataset"
