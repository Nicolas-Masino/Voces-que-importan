import json
from datetime import datetime
from abc import ABC, abstractmethod
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

LOGS_DIR = Path("data/logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_DAY = datetime.now().strftime("%Y-%m-%d")
LOGFORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOGFILE = LOGS_DIR / f"{LOG_DAY}_conversation.log"

CONFIG_FILE = Path("config.json")
# Cargar los topicos de NLP desde el archivo JSON
with Path.open(CONFIG_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)
    TOPICS = data.get("topic", [])

# Clase maestra de configuraciones 
class Settings(BaseSettings, ABC):

    @classmethod
    @abstractmethod
    def load(cls):
        """Método obligatorio para cargar la configuración según la fuente."""
        pass

# Subclase de configuraciones del agente 
class AgentSettings(Settings):
    provider: str = "demo"
    model: str = ""
    api_key: str = ""
    context_window: int = 8  # Tamaño de la ventana de contexto en turnos de conversación (pares de mensajes)

    # Configura Pydantic para leer automáticamente un archivo .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="LLM_"
    )

    @classmethod
    def load(cls) -> "AgentSettings":
        return cls()

# Subclase de configuraciones para RAG (Recuperación de Información)
class RAGSettings(Settings):
    corpus_dir: str = "data/sources"
    chroma_dir:str 
    collection: str
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    threshold: float

    @classmethod
    def load(cls, json_path: str = CONFIG_FILE) -> "RAGSettings":
        raw_data = Path(json_path).read_text(encoding="utf-8")
        data = json.loads(raw_data)
        return cls(**data.get('rag', {}))

AGENT_SETTINGS = AgentSettings.load()
RAG_SETTINGS = RAGSettings.load()