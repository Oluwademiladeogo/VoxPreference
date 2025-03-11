import os
import pandas as pd
import tensorflow as tf
from model.preprocessing.data_loader import load_dataset
from model.training.cnn_rnn_asr import asr_model

def get_paths():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    tsv_path = os.path.join(base_dir, "../../data/line_index_male.tsv")
    speech_files_dir = os.path.join(base_dir, "../../data/SpeechFiles/")
    return tsv_path, speech_files_dir

tsv_path, speech_files_dir = get_paths()

# Load the TSV file
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
def sparse_labels(y):
    return tf.keras.backend.ctc_label_dense_to_sparse(y, tf.fill(tf.shape(y), tf.shape(y)[1]))

asr_model.fit(X_train, sparse_labels(y_train), batch_size=32, epochs=20, validation_split=0.1)

asr_model.save_weights("asr_model_weights.h5")
print("Training complete and model saved!")