import tensorflow as tf
from tensorflow.keras import layers, Model, Input

# Hyperparameters (loaded from model_configs)
input_shape = (None, 40)  # Variable-length input, 40 MFCC features
vocab_size = 30  

def create_model(input_shape, vocab_size):
    # Input layers
    inputs = Input(shape=input_shape, name="speech_input")
    input_length = Input(name='input_length', shape=[1], dtype='int64')
    labels = Input(name='labels', shape=[None], dtype='int64')
    label_length = Input(name='label_length', shape=[1], dtype='int64')
    
    # CNN layers
    x = layers.Conv1D(filters=128, kernel_size=5, activation='relu', padding='same')(inputs)
    x = layers.MaxPooling1D(pool_size=2)(x)
    x = layers.Conv1D(filters=256, kernel_size=3, activation='relu', padding='same')(x)
    x = layers.MaxPooling1D(pool_size=2)(x)

    # Bidirectional LSTM layers
    x = layers.Bidirectional(layers.LSTM(256, return_sequences=True, dropout=0.3))(x)
    x = layers.Bidirectional(layers.LSTM(256, return_sequences=True, dropout=0.3))(x)

    # Dense layer for character classification
    # Add 1 for the blank symbol used in CTC
    logits = layers.Dense(vocab_size + 1, activation='softmax', name="char_output")(x)
    
    # Define CTC loss as a Lambda layer
    def ctc_lambda_func(args):
        y_pred, labels, input_length, label_length = args
        # The CTC loss requires the input length after CNN downsampling
        # Input length is divided by 4 due to 2 pooling layers with pool_size=2
        input_length_adjusted = tf.cast(tf.math.floordiv(input_length, 4), tf.int32)
        
        # Convert sparse tensor to dense if needed
        if isinstance(labels, tf.SparseTensor):
            labels = tf.sparse.to_dense(labels)
        
        return tf.keras.backend.ctc_batch_cost(labels, y_pred, input_length_adjusted, label_length)
        
    loss_out = layers.Lambda(ctc_lambda_func, output_shape=(1,), name='ctc')([
        logits, labels, input_length, label_length])
        
    # Create training model with CTC loss included
    model = Model(inputs=[inputs, labels, input_length, label_length], outputs=loss_out)
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss={'ctc': lambda y_true, y_pred: y_pred})
    
    # Create prediction model
    pred_model = Model(inputs=inputs, outputs=logits)
    
    return model, pred_model