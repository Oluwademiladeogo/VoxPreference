"""Load any common audio format as 16 kHz mono float32 and trim leading/trailing silence."""
from __future__ import annotations

import io
import shutil
import subprocess

import numpy as np

SR = 16000


def load(source, sr: int = SR) -> np.ndarray:
    """source: a path, raw bytes, or a file-like object."""
    data = source
    if hasattr(source, "read"):
        data = source.read()
    try:
        import soundfile as sf

        audio, rate = sf.read(io.BytesIO(data) if isinstance(data, (bytes, bytearray)) else data, dtype="float32", always_2d=True)
        audio = audio.mean(1)
    except Exception:
        audio, rate = _ffmpeg(data, sr), sr
    if rate != sr:
        from scipy.signal import resample_poly

        g = np.gcd(rate, sr)
        audio = resample_poly(audio, sr // g, rate // g).astype("float32")
    return np.ascontiguousarray(audio, dtype=np.float32)


def _ffmpeg(data, sr: int) -> np.ndarray:
    """Decode formats libsndfile cannot read (mp3, m4a, webm/opus from browsers)."""
    exe = shutil.which("ffmpeg")
    if exe is None:
        raise RuntimeError("this audio format needs ffmpeg, which is not installed")
    cmd = [exe, "-nostdin", "-loglevel", "error", "-i", "pipe:0" if isinstance(data, (bytes, bytearray)) else str(data),
           "-f", "f32le", "-ac", "1", "-ar", str(sr), "pipe:1"]
    proc = subprocess.run(cmd, input=data if isinstance(data, (bytes, bytearray)) else None, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"could not decode audio: {proc.stderr.decode(errors='replace').strip()[:300]}")
    return np.frombuffer(proc.stdout, dtype=np.float32).copy()


def trim(audio: np.ndarray, sr: int = SR, threshold_db: float = 35.0, pad_s: float = 0.15) -> tuple[np.ndarray, float]:
    """Cut silence before the first and after the last frame within threshold_db of the peak level.
    Returns the trimmed audio and its start offset in seconds."""
    hop = int(0.01 * sr)
    if len(audio) < hop * 3:
        return audio, 0.0
    frames = audio[: len(audio) // hop * hop].reshape(-1, hop)
    rms = np.sqrt((frames ** 2).mean(1) + 1e-12)
    db = 20 * np.log10(rms / rms.max())
    voiced = np.where(db > -threshold_db)[0]
    if len(voiced) == 0:
        return audio, 0.0
    pad = int(pad_s * sr)
    start = max(0, voiced[0] * hop - pad)
    end = min(len(audio), (voiced[-1] + 1) * hop + pad)
    return audio[start:end], start / sr
