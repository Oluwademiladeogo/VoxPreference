import sys
import json
from phonemizer import phonemize

def convert_to_ipa(text):
    try:
        ipa = phonemize(
            text,
            language="en-us",
            backend="espeak",
            strip=True,
            preserve_punctuation=True,
            punctuation_marks=';:,.!?¡¿—…"«»"()',
            with_stress=True,
            njobs=1
        )
        return {
            "success": True,
            "ipa": ipa
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    text = sys.stdin.read()
    result = convert_to_ipa(text)
    print(json.dumps(result)) 