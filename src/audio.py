from faster_whisper import WhisperModel
import torch
import numpy as np
import chainlit as cl

from .config import AUDIO_SETTINGS

# 1. Detectar dispositivo 
device = "cuda" if torch.cuda.is_available() else "cpu"

# Carga ligera y optimizada en CPU
model = WhisperModel(AUDIO_SETTINGS.model, device=AUDIO_SETTINGS.device or device, compute_type="int8")

def _transcriber(audio):
    segments, _ = model.transcribe(audio, beam_size=5, language="es", task="transcribe", vad_filter=True)
    text = " ".join(segment.text for segment in segments).strip()
    return text

async def speech_to_text(bytes):
    audio_np = np.frombuffer(bytes, dtype=np.int16).astype(np.float32) / 32768.0

    segments, _ = await cl.make_async(model.transcribe)(audio_np, beam_size=5, language="es", task="transcribe", vad_filter=True)
    text = " ".join(segment.text for segment in segments).strip()
    #text = await cl.make_async(_transcriber)(audio_np)
    
    return text
