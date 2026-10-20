import numpy as np
import torch

from pg.align import WordAligner, words_of


class FakeOut:
    def __init__(self, logits):
        self.logits = logits


class FakeAligner(WordAligner):
    """No model: frame t of the k-th window (which starts at sample k * hop) 'hears' its global frame
    index, and, like wav2vec2, a window of n samples yields n // 320 - 1 frames."""

    def __init__(self, hop_s: float = 19.0):
        hop = int(hop_s * 16000)

        class Proc:
            def __call__(self, chunk, sampling_rate, return_tensors):
                class X:
                    input_values = torch.tensor(chunk).unsqueeze(0)
                return X()

        class Model:
            calls = 0

            def __call__(self, x):
                n = x.shape[1] // 320 - 1
                logits = torch.zeros(1, n, 2)
                logits[0, :, 0] = torch.arange(n) + (Model.calls * hop) // 320
                Model.calls += 1
                return FakeOut(logits)

        self.processor, self.model = Proc(), Model()


def test_long_audio_frames_stay_in_place():
    audio = np.zeros(16000 * 125, dtype=np.float32)  # just over 2 minutes: 7 windows
    lp = FakeAligner().emissions(audio)
    # log_softmax subtracts the same constant from both columns, so their difference is the stamp
    stamps = np.round((lp[:, 0] - lp[:, 1]).numpy()).astype(int)
    assert abs(len(lp) - len(audio) // 320) <= 2
    assert (stamps == np.arange(len(stamps))).all()  # output frame g is global frame g: no drift


def test_words_of_normalises_transcripts():
    assert words_of("Ask her: ‘Bring THESE things!’ 123") == ["ask", "her", "bring", "these", "things"]
