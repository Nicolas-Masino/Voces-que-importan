from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.agent import ConversationalAgent
from src.config import AgentSettings

from evaluacion.scripts.common import read_csv, summary, write_json, write_run_config


async def evaluate(repetitions: int) -> dict:
    inputs = [
        {"id": row["id"], "texto": row["consulta"], "tipo": "rag"}
        for row in read_csv("rag_consultas.csv")
    ]
    scenario_path = Path(__file__).resolve().parents[1] / "datos" / "escenarios.md"
    scenario_inputs = [
        {"id": "caso1", "texto": "En el grupo de la materia comparten capturas para burlarse de mí. Me da vergüenza ir a clase. ¿Qué puedo hacer?", "tipo": "escenario"},
        {"id": "caso2", "texto": "Soy estudiante extranjera y se burlan de mi acento. Me están dejando fuera del grupo. ¿Qué puedo hacer para hablarlo sin que empeore?", "tipo": "escenario"},
        {"id": "caso3", "texto": "Estudio en la Universidad de Navarra y recibo comentarios humillantes de forma repetida. Quiero conocer el protocolo y saber a qué canal puedo acudir.", "tipo": "escenario"},
    ]
    inputs.extend(scenario_inputs)

    records = []
    for repetition in range(1, repetitions + 1):
        for item in inputs:
            agent = ConversationalAgent(AgentSettings.load())
            started = time.perf_counter()
            error = None
            try:
                await agent.respond(item["texto"])
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
            total_ms = (time.perf_counter() - started) * 1000
            records.append({
                "repeticion": repetition,
                "id": item["id"],
                "tipo": item["tipo"],
                "total_ms": total_ms,
                "nlp_ms": agent.metrics.nlp_latency_ms,
                "rag_ms": agent.metrics.rag_latency_ms,
                "resources_ms": agent.metrics.resources_latency_ms,
                "llm_ms": agent.metrics.llm_latency_ms,
                "traza": dict(agent.metrics.trace_state),
                "error": error,
            })

    successful = [item for item in records if item["error"] is None]
    return {
        "n_corridas": len(records),
        "n_exitosas": len(successful),
        "n_fallos": len(records) - len(successful),
        "resumen_ms": {
            key: summary([item[key] for item in successful])
            for key in ("nlp_ms", "rag_ms", "resources_ms", "llm_ms", "total_ms")
        },
        "corridas": records,
        "escenarios_archivo": str(scenario_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeticiones", type=int, default=3)
    args = parser.parse_args()
    if args.repeticiones < 1:
        parser.error("--repeticiones debe ser mayor que cero")
    write_run_config()
    payload = asyncio.run(evaluate(args.repeticiones))
    path = write_json("latencia_resultados.json", payload)
    print(f"Resultados de latencia guardados en {path}")


if __name__ == "__main__":
    main()
