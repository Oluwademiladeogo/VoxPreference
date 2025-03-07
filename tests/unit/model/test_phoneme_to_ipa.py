import pytest
from unittest.mock import MagicMock
from phoneme_to_ipa import phoneme_to_ipa_conversion

# Mocking the Epitran class and its transliterate method
@pytest.fixture
def mock_epi():
    mock_epi = MagicMock()
    mock_epi.transliterate = MagicMock(side_effect=lambda p: p.lower())  # Mocking transliteration to return lowercase phonemes
    return mock_epi

def test_phoneme_to_ipa_conversion_valid(mock_epi):
    predictions = ["AH", "D", "IH", "S", "AA", "Z"]
    
    # Use the mock_epi instance in the function
    ipa_transcription = phoneme_to_ipa_conversion(predictions)
    
    expected_ipa = "ah d ih s aa z"
    assert ipa_transcription == expected_ipa, f"Expected: {expected_ipa}, but got: {ipa_transcription}"

def test_phoneme_to_ipa_conversion_invalid(mock_epi):
    # Test with some unsupported phonemes that raise an exception
    mock_epi.transliterate.side_effect = lambda p: p.lower() if p != "Z" else Exception("Invalid phoneme")
    
    predictions = ["AH", "Z", "S", "AA"]
    ipa_transcription = phoneme_to_ipa_conversion(predictions)
    
    # Expect error handling for "Z"
    expected_ipa = "ah [ERROR:Z] s aa"
    assert ipa_transcription == expected_ipa, f"Expected: {expected_ipa}, but got: {ipa_transcription}"

def test_phoneme_to_ipa_conversion_empty(mock_epi):
    predictions = []
    ipa_transcription = phoneme_to_ipa_conversion(predictions)
    
    assert ipa_transcription == "", "Expected an empty string for empty input"

def test_phoneme_to_ipa_conversion_error_handling(mock_epi):
    # Simulate an error in transliteration
    mock_epi.transliterate.side_effect = Exception("Epitran error")
    
    predictions = ["AH", "D", "IH"]
    ipa_transcription = phoneme_to_ipa_conversion(predictions)
    
    expected_ipa = "[ERROR:AH] [ERROR:D] [ERROR:IH]"
    assert ipa_transcription == expected_ipa, f"Expected: {expected_ipa}, but got: {ipa_transcription}"
