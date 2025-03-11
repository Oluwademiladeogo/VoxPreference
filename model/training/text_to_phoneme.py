import epitran

epi = epitran.Epitran("eng-Latn")

def text_to_phonemes(text):
    """Convert text to phonemes using Epitran."""
    phonemes = []
    for char in text:
        try:
            phonemes.append(epi.transliterate(char))
        except Exception as e:
            phonemes.append(f"[ERROR:{char}]")
    return phonemes