from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.safety import safety_from_llm, safety_from_re

from evaluacion.scripts.common import read_csv, write_json, write_run_config


async def evaluate(with_llm: bool) -> dict:
    rows = read_csv("seguridad.csv")
    results = []
    for row in rows:
        regex_result = safety_from_re(row["texto"])
        selected = regex_result
        layer = "reglas" if regex_result.level == "urgent" else "ninguna"
        llm_result = None
        if with_llm and regex_result.level != "urgent":
            from src.nlp import analyze

            analysis = await analyze(row["texto"])
            llm_result = safety_from_llm(analysis)
            if llm_result.level == "urgent":
                selected = llm_result
                layer = "clasificador"
        results.append({
            "id": row["id"],
            "clase_esperada": row["clase"],
            "categoria": row["categoria"],
            "nivel": selected.level,
            "capa": layer,
            "regex_razon": regex_result.reason,
            "llm_razon": llm_result.reason if llm_result else None,
            "respuesta": selected.response,
            "detectado_correctamente": (selected.level == "urgent") == (row["clase"] == "urgente"),
            "llm_ejecutado": llm_result is not None,
        })

    urgent = [item for item in results if item["clase_esperada"] == "urgente"]
    controls = [item for item in results if item["clase_esperada"] == "control"]
    return {
        "modo": "reglas_y_clasificador" if with_llm else "solo_reglas",
        "resultados": results,
        "resumen": {
            "recall_urgencias": sum(item["detectado_correctamente"] for item in urgent) / len(urgent),
            "falsas_alarmas": sum(
                item["nivel"] == "urgent" for item in controls
            ) / len(controls),
            "urgencias": len(urgent),
            "controles": len(controls),
            "por_capa": {
                layer: sum(item["nivel"] == "urgent" for item in urgent if item["capa"] == layer)
                for layer in ("reglas", "clasificador", "ninguna")
            },
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Mide solo la primera capa local; útil para aislar falsos negativos de regex.",
    )
    args = parser.parse_args()
    write_run_config()
    payload = asyncio.run(evaluate(not args.no_llm))
    path = write_json("seguridad_resultados.json", payload)
    print(f"Resultados de seguridad guardados en {path}")


if __name__ == "__main__":
    main()
