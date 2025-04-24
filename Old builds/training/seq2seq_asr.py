import tensorflow as tf
from tensorflow.keras import layers, Model, Input

def create_model(input_shape, vocab_size):
    # Encoder
    inputs = Input(shape=input_shape, name="speech_input")
    
    # CNN feature extraction
    x = layers.Conv1D(filters=128, kernel_size=5, activation='relu', padding='same')(inputs)
    x = layers.MaxPooling1D(pool_size=2)(x)
    x = layers.Conv1D(filters=256, kernel_size=3, activation='relu', padding='same')(x)
    x = layers.MaxPooling1D(pool_size=2)(x)
    
    # Encoder RNN
    encoder_outputs, forward_h, forward_c, backward_h, backward_c = layers.Bidirectional(
        layers.LSTM(256, return_sequences=True, return_state=True))(x)
    state_h = layers.Concatenate()([forward_h, backward_h])
    state_c = layers.Concatenate()([forward_c, backward_c])
    
    # Decoder setup
    decoder_inputs = Input(shape=(None,), name="decoder_inputs")
    embed = layers.Embedding(input_dim=vocab_size+1, output_dim=512)(decoder_inputs)
    
    # Attention mechanism
    attention = layers.AdditiveAttention()([embed, encoder_outputs])
    
    # Decoder RNN with attention context
    decoder_lstm = layers.LSTM(512, return_sequences=True, return_state=True)
    decoder_outputs, _, _ = decoder_lstm(attention, initial_state=[state_h, state_c])
    
    # Output layer
    outputs = layers.Dense(vocab_size+1, activation='softmax')(decoder_outputs)
    
    # Create the model
    model = Model([inputs, decoder_inputs], outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss='sparse_categorical_crossentropy'
    )
    
    return model