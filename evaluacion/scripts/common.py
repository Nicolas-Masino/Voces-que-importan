from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "evaluacion" / "datos"
RESULTS_DIR = ROOT / "evaluacion" / "resultados"


def read_csv(name: str) -> list[dict[str, str]]:
    with (DATA_DIR / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_json(name: str, payload: Any) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    target = RESULTS_DIR / name
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def percentile(values: list[float], percentage: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentage / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_value(args: list[str]) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), *args], text=True, stderr=subprocess.STDOUT
        ).strip()
    except subprocess.CalledProcessError:
        return None


def write_run_config() -> Path:
    from src.config import RAG_SETTINGS, AGENT_SETTINGS

    corpus = [
        f"{path.name}: sha256 {sha256(path)}"
        for path in sorted((ROOT / "data" / "sources").glob("*.pdf"))
    ]
    payload = {
        "fecha": datetime.now(timezone.utc).isoformat(),
        "modelo_llm": AGENT_SETTINGS.model,
        "temperatura": {"analisis": 0, "generacion": 0.3},
        "modelo_embeddings": RAG_SETTINGS.embedding_model,
        "corpus": corpus,
        "indice_chroma": {
            "chunk_size": RAG_SETTINGS.chunk_size,
            "overlap": RAG_SETTINGS.chunk_overlap,
            "umbral": RAG_SETTINGS.threshold,
        },
        "versiones": "requirements.txt",
        "equipo": f"{platform.system()} {platform.release()} / Python {platform.python_version()}",
        "red": "no registrada",
        "commit": git_value(["rev-parse", "HEAD"]),
        "comando": "evaluacion/scripts",
        "interpretacion": {
            "mediana": "percentil 50",
            "p95": "percentil 95 lineal interpolado",
        },
    }
    return write_json("../config_corrida.json", payload)


def summary(values: list[float]) -> dict[str, float | int | None]:
    return {
        "n": len(values),
        "mediana_ms": median(values) if values else None,
        "p95_ms": percentile(values, 95),
    }
