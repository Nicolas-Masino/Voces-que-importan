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
    university_name: str = "Tu universidad"
    convivencia_url: str = ""
    wellbeing_url: str = ""
    emergency_phone: str = ""

    # Configura Pydantic para leer automáticamente un archivo .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
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
    def load(cls, json_path: str = "config.json") -> "RAGSettings":
        raw_data = Path(json_path).read_text(encoding="utf-8")
        data = json.loads(raw_data)
        return cls(**data.get('rag', {}))

# Subclase de configuración para el análisis de NLP
class NLPSettings(Settings):
    sentiment: list
    emotion: list
    intent: list
    topic: list

    @classmethod
    def load(cls, json_path: str = "config.json") -> "NLPSettings":
        raw_data = Path(json_path).read_text(encoding="utf-8")
        data = json.loads(raw_data)
        return cls(**data.get('nlp', {}))


AGENT_SETTINGS = AgentSettings.load()
RAG_SETTINGS = RAGSettings.load()
NLP_SETTINGS = NLPSettings.load()