import pandas as pd
from sklearn.model_selection import train_test_split

# Load both TSVs
male = pd.read_csv('data/line_index_male.tsv', sep='\t', names=['path', 'transcript'])
female = pd.read_csv('data/line_index_female.tsv', sep='\t', names=['path', 'transcript'])

# Combine
combined = pd.concat([male, female], ignore_index=True)

# Add the folder path to the audio files
combined['path'] = combined['path'].apply(lambda x: f"data/SpeechFiles/{x}.wav")

# Shuffle
combined = combined.sample(frac=1, random_state=42).reset_index(drop=True)

# Split (90% train, 10% validation)
train_df, val_df = train_test_split(combined, test_size=0.1, random_state=42)

# Save as CSV
train_df.to_csv('data/train.csv', index=False)
val_df.to_csv('data/val.csv', index=False)

print(f"Train samples: {len(train_df)}, Validation samples: {len(val_df)}")