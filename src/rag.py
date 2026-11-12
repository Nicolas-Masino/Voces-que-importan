"""
rag.py - RAG para la herramienta consultar_evidencia

Estructura esperada:
    corpus/
        manifest.json    <- metadatos de cada documento (ver MANIFEST_EJEMPLO)
        oms_comunicacion.pdf
        oit_violencia_educacion.pdf
        ...

Uso:
    python rag.py ingest       # construye el índice (con internet la 1ra vez)
    python rag.py query "qué hacer ante burlas por mi acento" --topico "xenofobia y discriminación"
"""
import argparse
import logging
import json
import re
import unicodedata
from pathlib import Path
from .config import RAG_SETTINGS, LOGFILE, LOGFORMAT, TOPICS, configure_logging
from typing import Literal, Dict
from pydantic import BaseModel, RootModel, Field

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Crear logger para el sistema de recuperación de evidencia (RAG)
configure_logging()
logger = logging.getLogger("RAG")

Path(RAG_SETTINGS.corpus_dir).mkdir(parents=True, exist_ok=True)

MANIFEST_EJEMPLO = {
    "oit_violencia_educacion.pdf": {
        "fuente": "OIT - Violencia y acoso en educación",
        "anio": 2023,
        "pais": "Internacional",
        "region": "Global",
        "url": "https://...",
        "topicos": ["bullying y acoso", "bienestar docente", "convivencia universitaria"],
    }
}

class MetadataSchema(BaseModel):
    """Esquema para validar los metadatos de cada documento del corpus."""
    fuente: str = Field(..., description="Nombre de la fuente del documento")
    anio: int = Field(..., description="Año de publicación")
    pais: str = Field(..., description="País de origen del documento")
    region: str = Field(..., description="Región geográfica del documento")
    url: str = Field(..., description="URL de referencia del documento")
    topicos: list[Literal[tuple(TOPICS)]] = Field(..., description="Lista de tópicos asociados al documento")

class ManifestSchema(RootModel[Dict[str, MetadataSchema]]):
    """Esquema para validar el manifest.json del corpus de documentos."""
    pass

def slug(topico: str) -> str:
    """'xenofobia y discriminación' -> 'xenofobia_y_discriminacion'"""
    s = unicodedata.normalize("NFKD", topico).encode("ascii", "ignore").decode()
    return re.sub(r"\W+", "_", s.lower()).strip("_")

def flag(topico: str) -> str:
    return f"t_{slug(topico)}"

_embeddings = None

def get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name=RAG_SETTINGS.embedding_model,
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings

def get_store() -> Chroma:
    return Chroma(
        collection_name=RAG_SETTINGS.collection,
        embedding_function=get_embeddings(),
        persist_directory=RAG_SETTINGS.chroma_dir,
        collection_metadata={"hnsw:space": "cosine"},
    )


def ingestar() -> None:
    manifest_path = RAG_SETTINGS.corpus_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=RAG_SETTINGS.chunk_size,
        chunk_overlap=RAG_SETTINGS.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    # Validar el manifest.json contra el esquema definido
    try:
        ManifestSchema.model_validate(manifest)
    except Exception as e:
        logger.error(f"Error de validación del manifest.json: {e}")
        raise

    chunks = []
    for nombre, meta in manifest.items():
        ruta = RAG_SETTINGS.corpus_dir / nombre
        if not ruta.exists():
            logger.warning(f"No existe {ruta}, se omite.")
            continue

        # Si todos los topicos del documento están fuera de la lista, se omite su ingesta
        if not any(t in TOPICS for t in meta["topicos"]):
            logger.warning(f"{nombre} no tiene tópicos válidos, se omite.")
            continue

        paginas = PyPDFLoader(str(ruta)).load()
        for i, ch in enumerate(splitter.split_documents(paginas)):
            ch.metadata = {
                "fuente": meta["fuente"],
                "archivo": nombre,
                "pagina": int(ch.metadata.get("page", 0)) + 1,  # PyPDF cuenta desde 0
                "anio": int(meta.get("anio", 0)),
                "pais": meta.get("pais", ""),
                "region": meta.get("region", ""),
                "url": meta.get("url", ""),
                "topicos": " | ".join(meta["topicos"]),  # para mostrar
                "chunk_id": f"{nombre}-{i}",
                # Chroma no admite listas en metadatos: un booleano por tópico
                **{flag(t): (t in meta["topicos"]) for t in TOPICS},
            }
            chunks.append(ch)

    # Descartar chunks casi vacíos (encabezados, números de página)
    chunks = [c for c in chunks if len(c.page_content.strip()) > 80]

    # Reconstruir desde cero para no duplicar al reingestar
    store = get_store()
    store.delete_collection()
    store = get_store()
    store.add_documents(chunks)
    logger.info(f"Ingestados {len(chunks)} fragmentos de {len(manifest)} documentos.")


# ----------------------------------------------------------------- recuperación
def buscar_evidencia(consulta: str, topico: str | None = None, k: int = 4) -> dict:
    """
    Devuelve {'resultados': [...], 'filtro_aplicado': bool}.
    Si el filtro por tópico no da resultados suficientes, reintenta sin filtro
    (y lo informa), para no quedarse sin respuesta por un tópico mal asignado.
    """
    store = get_store()

    def _buscar(filtro):
        pares = store.similarity_search_with_score(consulta, k=k, filter=filtro)
        salida = []
        for doc, distancia in pares:
            relevancia = round(1 - distancia, 3)
            if relevancia >= RAG_SETTINGS.threshold: # documentos por debajo del umbral no se citan
                salida.append({"texto": doc.page_content, "relevancia": relevancia, **doc.metadata})
        return salida

    filtro_aplicado = False
    resultados = []
    if topico and topico in TOPICS:
        resultados = _buscar({flag(topico): True})
        filtro_aplicado = True
    if len(resultados) < 1:  # filtro vacío o muy escaso
        resultados = _buscar(None)
        filtro_aplicado = False

    logger.info(f"Consulta: {consulta} | Tópico: {topico} | Resultados: {len(resultados)} | Filtro aplicado: {filtro_aplicado}")
    return {"results": resultados, "filtro_aplicado": filtro_aplicado}


def formatear_cita(r: dict) -> str:
    return f"{r['fuente']} ({r['anio']}), p. {r['pagina']}"


# ------------------------------------------------------------------------- CLI
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest")
    q = sub.add_parser("query")
    q.add_argument("texto")
    q.add_argument("--topico", default=None)
    args = ap.parse_args()

    if args.cmd == "ingest":
        ingestar()
    else:
        res = buscar_evidencia(args.texto, args.topico)
        print(f"Filtro por tópico aplicado: {res['filtro_aplicado']}\n")
        for r in res["results"]:
            print(f"[{r['relevancia']}] {formatear_cita(r)}\n{r['texto'][:300]}...\n")