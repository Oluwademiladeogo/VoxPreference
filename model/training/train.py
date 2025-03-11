import os
import pandas as pd
import tensorflow as tf
from model.preprocessing.data_loader import load_dataset, sparse_labels
from model.training.cnn_rnn_asr import asr_model

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
    if index >= 10:
        break
    audio_path = os.path.join(speech_files_dir, f"{row['id']}.wav")
    train_data.append((audio_path, row['text']))

X_train, y_train = load_dataset(train_data)

# Convert text labels to sparse tensors for CTC loss
y_train_sparse = sparse_labels(y_train)

asr_model.fit(X_train, y_train_sparse, batch_size=32, epochs=20, validation_split=0.1)

asr_model.save_weights("asr_model_weights.h5")
print("Training complete and model saved!")