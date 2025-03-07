import tensorflow as tf
from tensorflow.keras import layers, Model, Input

# Hyperparameters (loaded from model_configs)
input_shape = (None, 40)  # Variable-length input, 40 MFCC features
num_phonemes = 50  # Example phoneme count

# Input layer
inputs = Input(shape=input_shape, name="speech_input")

# CNN layers
x = layers.Conv1D(filters=128, kernel_size=5, activation='relu', padding='same')(inputs)
x = layers.MaxPooling1D(pool_size=2)(x)
x = layers.Conv1D(filters=256, kernel_size=3, activation='relu', padding='same')(x)
x = layers.MaxPooling1D(pool_size=2)(x)

# Bidirectional LSTM layers
x = layers.Bidirectional(layers.LSTM(256, return_sequences=True, dropout=0.3))(x)
x = layers.Bidirectional(layers.LSTM(256, return_sequences=True, dropout=0.3))(x)

# Dense layer for phoneme classification
logits = layers.Dense(num_phonemes + 1, activation='softmax', name="phoneme_output")(x)

# Define the model
asr_model = Model(inputs=inputs, outputs=logits, name="CNN-RNN_ASR")

# Compile with CTC loss
asr_model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss=tf.keras.backend.ctc_batch_cost)

# Model summary
asr_model.summary()
