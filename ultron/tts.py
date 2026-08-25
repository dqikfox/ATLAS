"""Text-to-speech helper for ATLAS.

Tries pyttsx3 first (offline, no network required), then falls back to gTTS
(requires internet).  The browser's built-in Web Speech API is the recommended
method for the web UI; this module is used for server-side audio generation
when the browser does not support the Web Speech API.
"""

from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path

import threading

_pyttsx3_engine = None
_pyttsx3_lock = threading.Lock()

def _synth_pyttsx3(text: str, rate: int = 175, volume: float = 0.9) -> bytes:
    import pyttsx3  # type: ignore
    global _pyttsx3_engine

    with _pyttsx3_lock:
        if _pyttsx3_engine is None:
            _pyttsx3_engine = pyttsx3.init()

        engine = _pyttsx3_engine
        engine.setProperty("rate", rate)
        engine.setProperty("volume", volume)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            engine.save_to_file(text, tmp_path)
            engine.runAndWait()
            return Path(tmp_path).read_bytes()
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass






def _synth_gtts(text: str) -> bytes:
    from gtts import gTTS  # type: ignore

    buf = io.BytesIO()
    tts = gTTS(text=text, lang="en")
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()


def synthesize(text: str) -> bytes:
    """Convert *text* to audio bytes (WAV or MP3 depending on backend).

    Raises RuntimeError if no TTS backend is available.
    """
    try:
        return _synth_pyttsx3(text)
    except Exception:
        pass
    try:
        return _synth_gtts(text)
    except Exception as exc:
        raise RuntimeError(
            "No TTS backend available.  Install pyttsx3 (offline) or gtts (online)."
        ) from exc
