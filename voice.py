import re
import subprocess
import tempfile
import time
import warnings
import wave

import numpy as np
import sounddevice as sd
import mlx_whisper

from menu import menu_item_names

SAMPLE_RATE = 16000
CHUNK_DURATION = 0.3        # seconds per recorded chunk
SILENCE_THRESHOLD = 0.01    # RMS below this is considered silence
SILENCE_CUTOFF = 1.5        # seconds of silence before stopping

_MLX_MODEL = "mlx-community/whisper-large-v3-turbo"

# Bias transcription toward the menu vocabulary so item names come through cleanly.
_WHISPER_PROMPT = "The user is ordering food. Menu: " + ", ".join(menu_item_names()) + "."


def listen() -> str:
    """Record from mic until silence, transcribe with Whisper, return text."""
    print("Listening... (speak now)")

    chunk_size = int(SAMPLE_RATE * CHUNK_DURATION)
    chunks: list[np.ndarray] = []
    silent_seconds = 0.0
    speech_started = False

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
        while True:
            chunk, _ = stream.read(chunk_size)
            rms = float(np.sqrt(np.mean(chunk ** 2)))

            if rms > SILENCE_THRESHOLD:
                speech_started = True
                silent_seconds = 0.0
                chunks.append(chunk.copy())
            elif speech_started:
                chunks.append(chunk.copy())
                silent_seconds += CHUNK_DURATION
                if silent_seconds >= SILENCE_CUTOFF:
                    break

    audio = np.concatenate(chunks, axis=0).flatten()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        with wave.open(tmp.name, "w") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes((audio * 32767).astype(np.int16).tobytes())
        tmp_path = tmp.name

    result = mlx_whisper.transcribe(tmp_path, path_or_hf_repo=_MLX_MODEL, language="en", initial_prompt=_WHISPER_PROMPT)
    text = result["text"].strip()
    print(f"You said: {text}")
    return text


def speak(text: str) -> None:
    """Speak text via macOS say, stopping immediately if user starts speaking."""
    cleaned = re.sub(r"[*#`]", "", text)
    cleaned = cleaned.encode("ascii", "ignore").decode("ascii")
    cleaned = " ".join(cleaned.split())

    proc = subprocess.Popen(["say", cleaned])
    time.sleep(0.5)  # let say start before monitoring mic for barge-in

    chunk_size = int(SAMPLE_RATE * CHUNK_DURATION)
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
        while proc.poll() is None:
            chunk, _ = stream.read(chunk_size)
            rms = float(np.sqrt(np.mean(chunk ** 2)))
            if rms > SILENCE_THRESHOLD:
                proc.kill()
                break

    proc.wait()
