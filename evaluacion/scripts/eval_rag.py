from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.config import RAG_SETTINGS
from src.rag import buscar_evidencia

from evaluacion.scripts.common import read_csv, write_json, write_run_config


def page_hit(result: dict, expected: str) -> bool:
    if not expected:
        return True
    try:
        return abs(int(result["pagina"]) - int(expected)) <= 1
    except (KeyError, TypeError, ValueError):
        return False


def document_hit(result: dict, expected: str) -> bool:
    return Path(result.get("archivo", "")).name == expected


def evaluate(threshold: float) -> dict:
    rows = read_csv("rag_consultas.csv")
    output = []
    for row in rows:
        response = buscar_evidencia(
            row["consulta"], row["topico"] or None, k=4, threshold=threshold
        )
        results = response["results"]
        expected_document = row["archivo_esperado"]
        evidence_expected = row["tipo"] != "sin_evidencia"
        document_ok = any(document_hit(item, expected_document) for item in results)
        page_ok = any(
            document_hit(item, expected_document)
            and page_hit(item, row["paginas_esperadas"])
            for item in results
        )
        output.append({
            "id": row["id"],
            "tipo": row["tipo"],
            "threshold": threshold,
            "resultados": results,
            "documento_ok": document_ok if evidence_expected else not results,
            "documento_y_pagina_ok": page_ok if evidence_expected else not results,
            "sin_evidencia_ok": not results if not evidence_expected else None,
            "filtro_aplicado": response["filtro_aplicado"],
        })

    evidence_rows = [item for item in output if item["tipo"] != "sin_evidencia"]
    no_evidence_rows = [item for item in output if item["tipo"] == "sin_evidencia"]
    return {
        "threshold": threshold,
        "consultas": output,
        "resumen": {
            "hit_documento": sum(item["documento_ok"] for item in evidence_rows) / len(evidence_rows),
            "hit_documento_pagina": sum(item["documento_y_pagina_ok"] for item in evidence_rows) / len(evidence_rows),
            "sin_evidencia_correcto": sum(item["sin_evidencia_ok"] for item in no_evidence_rows) / len(no_evidence_rows),
            "n_evidencia": len(evidence_rows),
            "n_sin_evidencia": len(no_evidence_rows),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=None)
    args = parser.parse_args()
    write_run_config()
    production = RAG_SETTINGS.threshold
    thresholds = [args.threshold] if args.threshold is not None else [0.0, production]
    payload = {"corridas": [evaluate(value) for value in thresholds]}
    path = write_json("rag_resultados.json", payload)
    print(f"Resultados RAG guardados en {path}")


if __name__ == "__main__":
    main()
