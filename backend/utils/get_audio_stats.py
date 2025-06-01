import os
import soundfile as sf
from tqdm import tqdm

# Paths
AUDIO_DIR = "data/SpeechFiles"
MALE_PREFIX = "ngm"
FEMALE_PREFIX = "ngf"

def get_audio_stats(prefix):
    total_duration = 0.0  # in seconds
    total_size = 0        # in bytes
    count = 0

    for fname in tqdm(os.listdir(AUDIO_DIR)):
        if fname.startswith(prefix) and fname.endswith('.wav'):
            fpath = os.path.join(AUDIO_DIR, fname)
            try:
                f = sf.SoundFile(fpath)
                duration = len(f) / f.samplerate
                size = os.path.getsize(fpath)
                total_duration += duration
                total_size += size
                count += 1
            except Exception as e:
                print(f"Error reading {fpath}: {e}")

    return count, total_duration, total_size

male_count, male_duration, male_size = get_audio_stats(MALE_PREFIX)
female_count, female_duration, female_size = get_audio_stats(FEMALE_PREFIX)

print(f"Male files: {male_count}")
print(f"  Total duration: {male_duration/3600:.2f} hours")
print(f"  Total size: {male_size/1024/1024:.2f} MB")

print(f"Female files: {female_count}")
print(f"  Total duration: {female_duration/3600:.2f} hours")
print(f"  Total size: {female_size/1024/1024:.2f} MB")