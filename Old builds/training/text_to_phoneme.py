import epitran

epi = epitran.Epitran('eng-Latn')

def text_to_phonemes(text):
    """Convert text to phonemes using Epitran."""
    words = text.split()
    all_phonemes = []
    
    for word in words:
        try:
            # Convert word to phonemes
            word_phonemes = epi.transliterate(word)
            all_phonemes.append(word_phonemes)
        except Exception as e:
            print(f"Error processing word '{word}': {e}")
            all_phonemes.append(f"[ERROR:{word}]")
    
    return all_phonemes