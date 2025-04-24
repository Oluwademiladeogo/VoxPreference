import os
import pandas as pd
import numpy as np
import tensorflow as tf
from model.preprocessing.data_loader import load_dataset, create_char_mapping
from model.training.seq2seq_asr import create_model

def get_paths():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    tsv_path = os.path.join(base_dir, "../../data/line_index_male.tsv")
    speech_files_dir = os.path.join(base_dir, "../../data/SpeechFiles/")
    return tsv_path, speech_files_dir

tsv_path, speech_files_dir = get_paths()

df = pd.read_csv(tsv_path, sep='\t', header=None, names=['id', 'text'])

# Get the first 10 entries
train_data = []
for index, row in df.iterrows():
    audio_path = os.path.join(speech_files_dir, f"{row['id']}.wav")
    train_data.append((audio_path, row['text']))

X_train, y_train = load_dataset(train_data)

char_to_idx = create_char_mapping(y_train)
print(f"Character mapping: {char_to_idx}")
print(f"Vocabulary size: {len(char_to_idx)}")

# Convert text labels to integer sequences
y_train_int = [[char_to_idx[char] for char in label] for label in y_train]

# Calculate sequence lengths
input_lengths = np.array([len(features) for features in X_train]).reshape(-1, 1)
label_lengths = np.array([len(label) for label in y_train_int]).reshape(-1, 1)

# Update vocabulary size based on actual number of unique characters
vocab_size = len(char_to_idx) - 1  # Subtract 1 for the blank symbol
print(f"Training Vocabulary Size: {vocab_size + 1}")

# Create the model
input_shape = (None, X_train[0].shape[1])  # Dynamic time dimension, fixed feature dimension
model = create_model(input_shape, vocab_size)

# Pad sequences to same length for batch processing
max_length = max(len(x) for x in X_train)
X_train_padded = tf.keras.preprocessing.sequence.pad_sequences(
    X_train, maxlen=max_length, dtype='float32', padding='post'
)

# Pad label sequences
max_label_length = max(len(label) for label in y_train_int)
y_train_padded = tf.keras.preprocessing.sequence.pad_sequences(
    y_train_int, maxlen=max_label_length, padding='post'
)

decoder_inputs = np.zeros_like(y_train_padded)
decoder_inputs[:, 1:] = y_train_padded[:, :-1]

model.fit(
    [X_train_padded, decoder_inputs],
    y_train_padded,
    batch_size=16,
    epochs=20,
    validation_split=0.1
)

# Save the model weights
model.save_weights("seq2seq_asr_model.weights.h5")
print("Training complete and model saved!")