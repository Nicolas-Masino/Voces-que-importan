import json
import logging
from datetime import datetime
from abc import ABC, abstractmethod
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

LOGS_DIR = Path("data/logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_DAY = datetime.now().strftime("%Y-%m-%d")
LOGFORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOGFILE = LOGS_DIR / f"{LOG_DAY}_conversation.log"


def configure_logging() -> None:
    """Agrega el archivo diario al root logger sin reemplazar handlers existentes."""
    root_logger = logging.getLogger()
    if any(
        getattr(handler, "_chatbot_file_handler", False)
        and getattr(handler, "baseFilename", None) == str(LOGFILE.resolve())
        for handler in root_logger.handlers
    ):
        return

    file_handler = logging.FileHandler(LOGFILE, encoding="utf-8")
    file_handler._chatbot_file_handler = True
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(LOGFORMAT))
    root_logger.addHandler(file_handler)
    if root_logger.level == logging.NOTSET or root_logger.level > logging.INFO:
        root_logger.setLevel(logging.INFO)


configure_logging()

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
    corpus_dir: Path = Path("data/sources")
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

class EmpathyLabSettings(Settings):
    weights: dict

    @classmethod
    def load(cls, json_path: str = CONFIG_FILE) -> "EmpathyLabSettings":
        raw_data = Path(json_path).read_text(encoding="utf-8")
        data = json.loads(raw_data)
        return cls(**data.get('empathy_lab', {}))

    # weights debe cumplir con una estructura específica, por lo que podemos agregar validaciones adicionales si es necesario.
    def __init__(self, **data):
        super().__init__(**data)
        required_keys = {"validation", "reflection", "open_questions", "non_judgment", "guidance"}
        if not required_keys.issubset(self.weights.keys()):
            missing = required_keys - self.weights.keys() # chequea que no falten claves requeridas
            raise ValueError(f"Faltan claves requeridas en weights: {missing}")
        # chequear que todos los valores sean números entre 0 y 1
        if not all(isinstance(self.weights[k], (int, float)) and 0 <= self.weights[k] <= 1 for k in required_keys):
            raise ValueError("Todos los valores en weights deben ser números entre 0 y 1.") 
        # chequear que la suma de los pesos sea 1
        total_weight = sum(self.weights[k] for k in required_keys)
        if not (0.99 <= total_weight <= 1.01):  # Permitir un pequeño margen de error por redondeo
            raise ValueError(f"La suma de los pesos debe ser 1. Suma actual: {total_weight}")

AGENT_SETTINGS = AgentSettings.load()
RAG_SETTINGS = RAGSettings.load()
EMPATHY_LAB_SETTINGS = EmpathyLabSettings.load()