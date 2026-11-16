from __future__ import annotations

import argparse
import asyncio
from collections import Counter
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sklearn.metrics import classification_report, confusion_matrix, f1_score

from src.nlp import analyze

from evaluacion.scripts.common import read_csv, write_json, write_run_config


async def run(repetitions: int) -> dict:
    rows = read_csv("nlp_test.csv")
    predictions: list[dict] = []
    for repetition in range(1, repetitions + 1):
        for row in rows:
            result = await analyze(row["texto"])
            predictions.append({
                "repeticion": repetition,
                "id": row["id"],
                "tema_real": row["tema"],
                "intencion_real": row["intencion"],
                "sentimiento_real": row["sentimiento"],
                "ambiguo": row["ambiguo"] == "1",
                "tema_pred": result["topic"],
                "intencion_pred": result["intent"],
                "sentimiento_pred": result["sentiment"],
                "emocion_pred": result["emotion"],
                "latencia_ms": result["latency_ms"],
            })

    metrics = {}
    for axis, actual_key, predicted_key in (
        ("tema", "tema_real", "tema_pred"),
        ("intencion", "intencion_real", "intencion_pred"),
        ("sentimiento", "sentimiento_real", "sentimiento_pred"),
    ):
        actual = [item[actual_key] for item in predictions]
        predicted = [item[predicted_key] for item in predictions]
        labels = sorted(set(actual) | set(predicted))
        metrics[axis] = {
            "macro_f1": f1_score(actual, predicted, average="macro", zero_division=0),
            "reporte": classification_report(
                actual, predicted, labels=labels, output_dict=True, zero_division=0
            ),
            "matriz_confusion": confusion_matrix(actual, predicted, labels=labels).tolist(),
            "labels": labels,
        }

    ambiguous = [item for item in predictions if item["ambiguo"]]
    metrics["casos"] = {
        "total": len(predictions),
        "por_repeticion": len(rows),
        "ambiguos": len(ambiguous),
        "distribucion_real": {
            axis: dict(Counter(item[key] for item in rows))
            for axis, key in (
                ("tema", "tema"),
                ("intencion", "intencion"),
                ("sentimiento", "sentimiento"),
            )
        },
    }
    return {"metricas": metrics, "predicciones": predictions}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeticiones", type=int, default=3)
    args = parser.parse_args()
    if args.repeticiones < 1:
        parser.error("--repeticiones debe ser mayor que cero")
    write_run_config()
    payload = asyncio.run(run(args.repeticiones))
    path = write_json("nlp_resultados.json", payload)
    print(f"Resultados NLP guardados en {path}")


if __name__ == "__main__":
    main()
