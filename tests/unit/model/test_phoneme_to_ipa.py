import pytest
from unittest.mock import MagicMock
from model.inference.predict import text_to_phonemes

# Mocking the Epitran class and its transliterate method
@pytest.fixture
def mock_epi():
    mock_epi = MagicMock()
    mock_epi.transliterate = MagicMock(side_effect=lambda p: p.lower())  # Mocking transliteration to return lowercase phonemes
    return mock_epi

def test_text_to_phonemes_valid(mock_epi):
    text = "hello"
    
    # Use the mock_epi instance in the function
    phoneme_sequence = text_to_phonemes(text)
    
    expected_phonemes = ["h", "e", "l", "l", "o"]
    assert phoneme_sequence == expected_phonemes, f"Expected: {expected_phonemes}, but got: {phoneme_sequence}"

def test_text_to_phonemes_invalid(mock_epi):
    # Test with some unsupported characters that raise an exception
    mock_epi.transliterate.side_effect = lambda p: p.lower() if p != "!" else Exception("Invalid character")
    
    text = "hello!"
    phoneme_sequence = text_to_phonemes(text)
    
    # Expect error handling for "!"
    expected_phonemes = ["h", "e", "l", "l", "o", "[ERROR:!]"]
    assert phoneme_sequence == expected_phonemes, f"Expected: {expected_phonemes}, but got: {phoneme_sequence}"

def test_text_to_phonemes_empty(mock_epi):
    text = ""
    phoneme_sequence = text_to_phonemes(text)
    
    assert phoneme_sequence == [], "Expected an empty list for empty input"

def test_text_to_phonemes_error_handling(mock_epi):
    # Simulate an error in transliteration
    mock_epi.transliterate.side_effect = Exception("Epitran error")
    
    text = "hello"
    phoneme_sequence = text_to_phonemes(text)
    
    expected_phonemes = ["[ERROR:h]", "[ERROR:e]", "[ERROR:l]", "[ERROR:l]", "[ERROR:o]"]
    assert phoneme_sequence == expected_phonemes, f"Expected: {expected_phonemes}, but got: {phoneme_sequence}"