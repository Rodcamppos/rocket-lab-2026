from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


class ConfigError(RuntimeError):
    """Problema de configuração (chave de API ausente, banco não encontrado...)."""


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "sim", "on"}


def _list_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name, "")
    items = tuple(item.strip() for item in raw.split(",") if item.strip())
    return items or default


def _path_env(name: str, default: Path) -> Path:
    path = Path(os.getenv(name) or default)
    return path if path.is_absolute() else PROJECT_ROOT / path


# --- OpenRouter / modelos -------------------------------------------------
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Ordem de tentativa: se o primeiro modelo falhar (ex.: 429), o próximo é usado.
# Atenção: cada tentativa que falha também conta na cota diária do OpenRouter.
DEFAULT_MODELS: tuple[str, ...] = (
    "openrouter/free",
    "nvidia/nemotron-3.5-lightning:free",
    "z-ai/glm-5.2:free",
    "google/gemma-4-26b-a4b-it:free",
)
MODEL_NAMES: tuple[str, ...] = _list_env("OPENROUTER_MODELS", DEFAULT_MODELS)

# --- Banco de dados (camada Gold) ---------------------------------------------
DB_PATH: Path = _path_env("CINEROCKET_DB_PATH", PROJECT_ROOT / "data" / "cinerocket.db")
MAX_ROWS: int = _int_env("MAX_ROWS", 50)
QUERY_TIMEOUT_S: int = _int_env("QUERY_TIMEOUT_S", 30)

# --- Agente -----------------------------------------------------------------------
# Teto de chamadas ao modelo por pergunta (protege a cota de 50 req/dia).
REQUEST_LIMIT_PER_QUESTION: int = _int_env("REQUEST_LIMIT_PER_QUESTION", 6)
TOOL_RETRIES: int = _int_env("TOOL_RETRIES", 2)
HISTORY_TURNS: int = _int_env("HISTORY_TURNS", 5)

# --- Guardrails de entrada -------------------------------------------------------
MAX_QUESTION_CHARS: int = _int_env("MAX_QUESTION_CHARS", 500)

# --- Cache de respostas ----------------------------------------------------------------
CACHE_ENABLED: bool = _bool_env("CACHE_ENABLED", True)
CACHE_PATH: Path = _path_env("CACHE_PATH", PROJECT_ROOT / "data" / "answer_cache.json")
