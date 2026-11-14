"""Emoción detectada -> reacción del avatar Strobi.

Utiliza la emoción detectada en el análisis de la situación para determinar cómo debe 
reaccionar el avatar Strobi. La reacción incluye un estado, 
una expresión facial y un tiempo de duración.
"""
import time

import chainlit as cl
from .agent import ConversationalAgent

# etiqueta -> (state del avatar, face, ms que se sostiene)
# Strobi acompaña en vez de imitar: ante enojo o ansiedad escucha con calma.
_REACTIONS: dict[str, tuple[str, str | None, int]] = {
    "alegria": ("happy", None, 8000),
    "tristeza": ("sad", None, 12000),
    "enojo": ("listening", "calm", 12000),
    "neutral": ("idle", None, 6000),
    "miedo": ("listening", "calm", 12000),
    "sorpresa": ("surprised", None, 6000),
    "disgusto": ("listening", "squinted", 8000),
    "greeting": ("excited", None, 8000),
    "celebrate": ("celebrate", None, 8000),
    "achievement": ("finished", None, 8000),
    "sleeping": ("sleeping", None, 8000),
}


def avatar_signal(agent: ConversationalAgent | None, emotion: str | None = None) -> cl.CustomElement:
    """Elemento invisible que le indica al avatar cómo reaccionar."""
    if emotion is None and agent is not None:
        emotion = agent.last_analysis.get("emotion") 
    state, face, hold_ms = _REACTIONS.get(emotion, _REACTIONS["neutral"])
    return cl.CustomElement(
        name="AvatarSignal",
        props={"state": state, "face": face, "hold_ms": hold_ms, "ts": int(time.time() * 1000)},
        display="inline",
    )
