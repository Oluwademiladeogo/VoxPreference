import tensorflow as tf
from model.preprocessing.data_loader import load_dataset
from model.training.cnn_rnn_asr import asr_model

train_data = []

X_train, y_train = load_dataset(train_data)

# Convert text labels to sparse tensors for CTC loss
def sparse_labels(y):
    return tf.keras.backend.ctc_label_dense_to_sparse(y, tf.fill(tf.shape(y), tf.shape(y)[1]))

# Train model
asr_model.fit(X_train, sparse_labels(y_train), batch_size=32, epochs=20, validation_split=0.1)

asr_model.save_weights("asr_model_weights.h5")
print("Training complete and model saved!")