import epitran

# Instantiate the epitran object for English
epi = epitran.Epitran("eng-Latn")

def phoneme_to_ipa_conversion(predictions):
    """
    Convert a list of phonemes into IPA transcription using Epitran.
    
    Args:
        predictions (list[str]): List of phonemes to convert.
    
    Returns:
        str: A space-separated string of IPA symbols.
    """
    ipa_transcriptions = []
    for p in predictions:
        try:
            ipa_transcriptions.append(epi.transliterate(p))
        except Exception as e:
            ipa_transcriptions.append(f"[ERROR:{p}]")  # Handles unexpected phonemes
    return " ".join(ipa_transcriptions)

