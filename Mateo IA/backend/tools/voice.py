"""Voz local: transcripción (STT) con faster-whisper y síntesis (TTS) con Piper.

Las dependencias se instalan desde requirements-voice.txt. El instalador también
descarga una voz española Piper y configura MATEO_PIPER_VOICE_MODEL; si falta
cualquier componente, las funciones devuelven un error claro.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

AUDIO_DIR = Path(__file__).resolve().parents[1] / "data" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

_whisper_model = None  # se carga una sola vez (singleton perezoso)
_piper_voice = None


class VoiceError(Exception):
    """Error controlado de transcripción o síntesis de voz."""


# ==========================================
# SPEECH-TO-TEXT (faster-whisper)
# ==========================================
def _whisper_runtime_options() -> Dict[str, str]:
    """Devuelve una configuración portable para CPU o CUDA."""
    device = os.getenv("MATEO_WHISPER_DEVICE", "cpu").strip().lower() or "cpu"
    default_compute_type = "int8" if device == "cpu" else "float16"
    compute_type = os.getenv("MATEO_WHISPER_COMPUTE_TYPE", default_compute_type).strip()
    return {"device": device, "compute_type": compute_type or default_compute_type}


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise VoiceError(
                "Falta 'faster-whisper'. Instalá con: pip install -r requirements-voice.txt"
            ) from e
        model_size = os.getenv("MATEO_WHISPER_MODEL", "base")
        options = _whisper_runtime_options()
        _whisper_model = WhisperModel(model_size, **options)
    return _whisper_model


def transcribe_audio(path: str | Path) -> Dict[str, Any]:
    """Transcribe un archivo de audio (wav/mp3/webm/ogg) a texto."""
    try:
        model = _get_whisper_model()
        segments, info = model.transcribe(str(path), language=os.getenv("MATEO_WHISPER_LANG") or None)
    except (RuntimeError, OSError) as e:
        raise VoiceError(
            "No se pudo iniciar la transcripción. Se intentó usar el dispositivo "
            "configurado para faster-whisper. Para equipos sin CUDA, configura "
            "MATEO_WHISPER_DEVICE=cpu en .env y reinicia Mateo."
        ) from e
    text = " ".join(segment.text.strip() for segment in segments).strip()
    if not text:
        return {"text": "", "language": getattr(info, "language", None)}
    return {"text": text, "language": getattr(info, "language", None)}


# ==========================================
# TEXT-TO-SPEECH (Piper)
# ==========================================
def _get_piper_voice():
    global _piper_voice
    if _piper_voice is None:
        try:
            from piper import PiperVoice
        except ImportError as e:
            raise VoiceError(
                "Falta 'piper-tts'. Instalá con: pip install -r requirements-voice.txt "
                "y ejecutá el instalador para descargar la voz configurada."
            ) from e
        model_path = os.getenv("MATEO_PIPER_VOICE_MODEL")
        if not model_path or not Path(model_path).exists():
            raise VoiceError(
                "Configurá MATEO_PIPER_VOICE_MODEL en .env apuntando a un modelo .onnx de Piper."
            )
        _piper_voice = PiperVoice.load(model_path)
    return _piper_voice


def synthesize_speech(text: str) -> Path:
    """Genera un WAV a partir de texto y devuelve la ruta del archivo."""
    if not text or not text.strip():
        raise VoiceError("No hay texto para sintetizar.")
    voice = _get_piper_voice()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    target = AUDIO_DIR / f"tts_{timestamp}.wav"
    import wave

    with wave.open(str(target), "wb") as wav_file:
        voice.synthesize(text.strip()[:2000], wav_file)
    return target


def voice_status() -> Dict[str, bool]:
    """Indica si STT/TTS están realmente disponibles, sin cargar los modelos."""
    try:
        import faster_whisper  # noqa: F401
        stt_available = True
    except ImportError:
        stt_available = False
    try:
        import piper  # noqa: F401
        model_path = os.getenv("MATEO_PIPER_VOICE_MODEL", "").strip()
        tts_available = bool(model_path and Path(model_path).is_file())
    except ImportError:
        tts_available = False
    return {"stt_available": stt_available, "tts_available": tts_available}
