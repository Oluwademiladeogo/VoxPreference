import pytest
import numpy as np
import librosa
from model.preprocessing.feature_extraction import extract_features
from unittest.mock import patch

@pytest.fixture
def mock_audio():
    return np.random.rand(32000)  # Simulate 2-second audio at 16kHz

@patch("librosa.load")
def test_extract_features(mock_load, mock_audio):
    mock_load.return_value = (mock_audio, 16000)  # Mock librosa.load output
    features = extract_features("dummy/path.wav")

    assert isinstance(features, np.ndarray), "Output should be a NumPy array"
    assert features.shape[1] == 40, "Number of MFCC features should be 40"
    assert features.shape[0] > 0, "Time dimension should be > 0"

@patch("librosa.load")
def test_extract_features_invalid_audio(mock_load):
    mock_load.side_effect = FileNotFoundError

    with pytest.raises(FileNotFoundError):
        extract_features("invalid/path.wav")