import tensorflow as tf
import tf2onnx
from model.training.cnn_rnn_asr import asr_model

# Convert the trained TensorFlow model to ONNX format
def convert_to_onnx(model, output_path="artifacts/saved_model.onnx"):
    try:
        onnx_model = tf2onnx.convert.from_keras(model)
        with open(output_path, "wb") as f:
            f.write(onnx_model.SerializeToString())
        print(f"Model successfully converted to ONNX and saved at {output_path}")
    except Exception as e:
        print(f"Error during model conversion: {e}")

convert_to_onnx(asr_model)