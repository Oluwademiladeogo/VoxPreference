import shutil
import subprocess
from pathlib import Path

import pytest

from pg.audio import load

CLIP = Path(__file__).parent / "fixtures" / "slr70" / "ngf_05223_00109235066.wav"


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_m4a_uploaded_as_bytes_decodes_fully(tmp_path):
    # an M4A with its index at the end, as phones and ffmpeg write it by default
    m4a = tmp_path / "clip.m4a"
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(CLIP), "-c:a", "aac", str(m4a)], check=True)
    from_path, from_bytes = load(m4a), load(m4a.read_bytes())
    assert abs(len(from_bytes) - len(from_path)) < 1600 and len(from_bytes) > 16000


def test_wav_bytes_decode():
    assert len(load(CLIP.read_bytes())) > 16000
