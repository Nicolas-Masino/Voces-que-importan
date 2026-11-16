from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.agent import ConversationalAgent
from src.config import AgentSettings

from evaluacion.scripts.common import read_csv, write_json, write_run_config


_CITATION_PATTERNS = (
    # Formato recomendado: [Fuente (2023), p. 4]
    re.compile(
        r"\[?\s*(?P<fuente>[^\[\]\n,;]+?)\s*"
        r"(?:\((?P<anio>19\d{2}|20\d{2})\)|[,;]\s*(?P<anio_alt>19\d{2}|20\d{2}))"
        r"\s*,?\s*p(?:á?g(?:ina)?)?\.?\s*(?P<pagina>\d+)\s*\]?",
        re.IGNORECASE,
    ),
)


def extract_citations(text: str) -> list[dict[str, str]]:
    citations = []
    for pattern in _CITATION_PATTERNS:
        for match in pattern.finditer(text):
            values = match.groupdict()
            citations.append({
                "texto": match.group(0),
                "fuente": values["fuente"].strip(),
                "anio": values["anio"] or values["anio_alt"],
                "pagina": values["pagina"],
            })
    return citations


def citation_matches_result(citation: dict[str, str], result: dict) -> bool:
    source = citation["fuente"].casefold()
    expected_source = result.get("fuente", "").casefold()
    source_words = [
        word for word in re.findall(r"\w+", expected_source)
        if len(word) >= 4
    ]
    source_match = source in expected_source or all(word in source for word in source_words[:2])
    return (
        source_match
        and citation["anio"] == str(result.get("anio"))
        and citation["pagina"] == str(result.get("pagina"))
    )


async def evaluate() -> dict:
    rows = [
        row for row in read_csv("rag_consultas.csv")
        if row["tipo"] != "sin_evidencia"
    ]
    output = []
    for row in rows:
        agent = ConversationalAgent(AgentSettings.load())
        error = None
        response = ""
        try:
            response = await agent.respond(row["consulta"])
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

        citations = extract_citations(response)
        supported = any(
            citation_matches_result(citation, result)
            for citation in citations
            for result in agent.last_evidence
        )
        output.append({
            "id": row["id"],
            "consulta": row["consulta"],
            "respuesta": response,
            "error": error,
            "citas_detectadas": citations,
            "cita_corresponde_a_resultado_recuperado": supported,
            "resultados_recuperados": [
                {
                    "fuente": result.get("fuente"),
                    "anio": result.get("anio"),
                    "pagina": result.get("pagina"),
                    "archivo": result.get("archivo"),
                }
                for result in agent.last_evidence
            ],
        })

    successful = [item for item in output if item["error"] is None]
    return {
        "criterio": (
            "Una respuesta cuenta como cubierta si contiene fuente, año de cuatro "
            "dígitos y página, y la cita coincide con un resultado recuperado."
        ),
        "consultas": output,
        "resumen": {
            "total": len(output),
            "exitosas": len(successful),
            "fallos": len(output) - len(successful),
            "cobertura": (
                sum(item["cita_corresponde_a_resultado_recuperado"] for item in successful)
                / len(successful)
                if successful else None
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    write_run_config()
    payload = asyncio.run(evaluate())
    path = write_json("citas_resultados.json", payload)
    print(f"Resultados de citas guardados en {path}")


if __name__ == "__main__":
    main()
