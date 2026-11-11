import json
from pathlib import Path
from .config import CONFIG_FILE, TOPICS
from typing import Literal
from pydantic import BaseModel, Field

with Path.open(CONFIG_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)
    resources_dict = data.get("resources", {})

class Resource(BaseModel):
    name: str = Field(..., description="Nombre del recurso")
    description: str = Field(..., description="Descripción del recurso")
    url: str = Field(..., description="URL del recurso")
    scope: Literal["internacional", "nacional", "provincial", "local", "institucional"] = Field(..., description="Alcance del recurso")
    topic: list[Literal[tuple(TOPICS)]] = Field(..., description="Tópico del recurso")

RESOURCES = [Resource(**res) for res in resources_dict.values()]
SORTED_SCOPES = ["internacional", "nacional", "provincial", "local", "institucional"]

def _prioridad_scope(r: Resource, ambito: str | None) -> int:
    """
    Devuelve un número que indica la prioridad del recurso según su ámbito.
    Cuanto menor el número, mayor la prioridad.

    La prioridad esta ordenada de mayor a menor jerarquía: internacional > nacional > provincial > local > institucional.
    Si se especifica un ámbito, los recursos de ese ámbito tienen la máxima prioridad, siguiendo el orden inverso
    los de menor prioridad se eliminan de la lista.
    """
    sorted_scopes = SORTED_SCOPES.copy()
    if ambito in sorted_scopes:
        # Obtener la prioridad del ambito solicitado
        i = sorted_scopes.index(ambito)
        # eliminar los ambitos de menor pioridad que el solicitado
        sorted_scopes = sorted_scopes[:i + 1]

        # Reversar la lista para que los recursos del ambito solicitado tengan la máxima prioridad
        sorted_scopes.reverse()
    for i, scope in enumerate(sorted_scopes):
        if r.scope == scope:
            return i
    return len(SORTED_SCOPES)  # Si no se encuentra, es el últimoo


def buscar_recursos(
    topico: str | None = None,
    ambito: str | None = None,
    max_resultados: int = 4
) -> dict:
    """
    Devuelve {'recursos': [...], 'filtro_topico': bool, 'filtro_ambito': bool}.
    Lógica:
      1. Filtra por tópico (si es uno válido). Si no hay recursos para ese tópico, cae a los generales ("otro").
      2. Si se pidió ámbito, deja los que coinciden o son globales. Y se eliminan los de menor prioridad que el solicitado.
      3. Ordena por prioridad de ámbito (si se pidió) y devuelve los primeros max_resultados.
    """

    flag_topico = True
    res = [r for r in RESOURCES if topico in r.topic]
    if not res:
        # no hay recursos para este tópico, caemos a los generales ("otro")
        flag_topico = False
        res = [r for r in RESOURCES if "otro" in r.topic]
 
    flag_ambito = False
    if ambito:
        flag_ambito = True
        res = [r for r in res if _prioridad_scope(r, ambito) <= len(SORTED_SCOPES)]
 
    ordenados = sorted(res, key=lambda r: _prioridad_scope(r, ambito))
    return {
        "recursos": ordenados[:max_resultados],
        "flag_topico": flag_topico,
        "flag_ambito": flag_ambito,
    }