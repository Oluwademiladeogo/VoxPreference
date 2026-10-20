import random

import pandas as pd

# Load both TSVs
male = pd.read_csv('data/line_index_male.tsv', sep='\t', names=['path', 'transcript'])
female = pd.read_csv('data/line_index_female.tsv', sep='\t', names=['path', 'transcript'])

# Combine
combined = pd.concat([male, female], ignore_index=True)

# File ids look like ngf_00295_00053583157: gender prefix + speaker number + utterance number
combined['speaker'] = combined['path'].str.split('_').str[:2].str.join('_')

# Add the folder path to the audio files
combined['path'] = combined['path'].apply(lambda x: f"data/SpeechFiles/{x}.wav")

# Split by speaker so validation measures performance on unseen voices (a random utterance split puts
# every speaker, and some identical sentences, on both sides). Validation speakers are drawn per gender
# until each gender has about 10% of its utterances held out.
rng = random.Random(42)
val_speakers = set()
for prefix in ('ngm', 'ngf'):
    counts = combined[combined['speaker'].str.startswith(prefix)].groupby('speaker').size()
    speakers = sorted(counts.index)
    rng.shuffle(speakers)
    held = 0
    for spk in speakers:
        if held >= 0.1 * counts.sum():
            break
        val_speakers.add(spk)
        held += counts[spk]
is_val = combined['speaker'].isin(val_speakers)
train_df, val_df = combined[~is_val], combined[is_val]

# Drop sentences from validation that also occur in training (the corpus repeats some prompts)
val_df = val_df[~val_df['transcript'].isin(set(train_df['transcript']))]

# Save as CSV
train_df.to_csv('data/train.csv', index=False)
val_df.to_csv('data/val.csv', index=False)

print(f"Train samples: {len(train_df)} ({train_df['speaker'].nunique()} speakers), "
      f"Validation samples: {len(val_df)} ({val_df['speaker'].nunique()} speakers)")
