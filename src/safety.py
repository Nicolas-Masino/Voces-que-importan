from dataclasses import dataclass
import re

@dataclass(frozen=True)
class SafetyResult:
    level: str
    reason: str
    response: str | None = None

_URGENT_PATTERNS = (
    # ideación propia o ajena
    r"\bse quiere matar\b",
    r"\bme quiero matar\b",
    r"\bpeligro inmediato\b",
    r"\bno quier\w* (seguir )?(viv|estar vivo|estar viva)",
    r"\bquier\w* (morir|morirme|matarme|desaparecer para siempre|terminar con (todo|mi vida)|acabar con (todo|mi vida)|suicidarme|suicidarse)\b",
    r"\b(me voy a|voy a|pienso en|pensando en|ganas de) (matarme|suicidarme|morir|quitarme la vida)",
    r"\b(quitarme|quitarse) la vida",
    r"\b(suicidarme|suicidarse)\b",
    r"\b(matarme|matarse)\b",
    r"\b(hacerme|hacerse) dano\b",
    r"\b(lastimarme|lastimarse)\b",
    r"\bautolesion\w*",
    r"\bcortarme (las venas|los brazos|las munecas)",
    r"\bmejor (estar|ser) muert[oa]",
    r"\bno (vale|tiene) (la pena|sentido) (seguir )?viv",
    # peligro inmediato por violencia de terceros
    r"\bme (va a|quiere|quieren) matar",
    r"\bvoy a matar a\b",
    r"\b(tiene|tienen) un arma",
    r"\bme (esta|estan) (pegando|golpeando|amenazando de muerte)",
)

def safety_from_llm(analysis: dict) -> SafetyResult:
    if analysis["intent"] == "emergencia":
        return SafetyResult(
            level="urgent",
            reason="llm_detected_emergency",
            response=(
                "Lo que contás puede implicar un riesgo inmediato. Si hay peligro, "
                "llamá ahora al 911 (Argentina) o a emergencias de tu localidad. "
                "No dejes sola a la persona: buscá a alguien de confianza o a un "
                "profesional y no prometas guardar el secreto. Decime en qué "
                "localidad estás para buscar un recurso oficial."
            ),
        )
    return SafetyResult(level="normal", reason="llm_no_emergency_detected")

def safety_from_re(text: str) -> SafetyResult:
    normalized = text.casefold()
    for pattern in _URGENT_PATTERNS:
        if re.search(pattern, normalized):
            return SafetyResult(
                level="urgent",
                reason=f"possible_immediate_danger: {pattern}",
                response=(
                    "Lo que contás puede implicar un riesgo inmediato. Si hay peligro, "
                    "llamá ahora al 911 (Argentina) o a emergencias de tu localidad. "
                    "No dejes sola a la persona: buscá a alguien de confianza o a un "
                    "profesional y no prometas guardar el secreto. Decime en qué "
                    "localidad estás para buscar un recurso oficial."
                ),
            )
    return SafetyResult(level="normal", reason="no_urgent_signal")

def assess_safety(from_re, from_llm) -> SafetyResult:
    if from_re.level == "urgent":
        return from_re
    if from_llm.level == "urgent":
        return from_llm
    return SafetyResult(level="normal", reason="no_urgent_signal")
