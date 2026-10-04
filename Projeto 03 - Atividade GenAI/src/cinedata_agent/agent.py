from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pydantic_ai import Agent
from pydantic_ai import exceptions as pai_exceptions
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits
from . import config
from .db import execute_query
from .guardrails import GuardrailError, validate_question, validate_sql
from .prompts import build_system_prompt
from .tools import AgentDeps, ExecutedQuery, executar_sql

class AgentError(RuntimeError):
    """Falha ao obter resposta do modelo (cota, rede, modelos indisponíveis...).

    ``queries`` guarda as consultas SQL que o agente chegou a tentar (útil para depurar).
    """

    def __init__(self, message: str, queries: list[ExecutedQuery] | None = None) -> None:
        super().__init__(message)
        self.queries = queries or []


@dataclass
class AgentAnswer:
    """Resposta final + metadados úteis para a CLI e para a avaliação."""

    text: str
    queries: list[ExecutedQuery] = field(default_factory=list)
    history: list[ModelMessage] = field(default_factory=list)
    from_cache: bool = False
    requests_used: int | None = None


# --------------------------------------------------------------------------- modelo
def _build_model() -> OpenAIChatModel | FallbackModel:
    """Cria o modelo no OpenRouter; com vários modelos, encadeia fallback automático."""
    if not config.OPENROUTER_API_KEY:
        raise config.ConfigError(
            "OPENROUTER_API_KEY não definida. Copie .env.example para .env e preencha a chave "
            "(https://openrouter.ai/keys)."
        )
    if "SUA_CHAVE" in config.OPENROUTER_API_KEY:
        raise config.ConfigError(
            "O .env ainda tem a chave de exemplo. Gere a sua em https://openrouter.ai/keys "
            "e substitua o valor de OPENROUTER_API_KEY."
        )
    provider = OpenAIProvider(
        base_url=config.OPENROUTER_BASE_URL, api_key=config.OPENROUTER_API_KEY
    )
    models = [OpenAIChatModel(name, provider=provider) for name in config.MODEL_NAMES]
    if len(models) == 1:
        return models[0]
    return _fallback_model(models)


def _fallback_model(models: list[OpenAIChatModel]) -> FallbackModel:
    """Fallback também para respostas inválidas do provedor.

    Modelos gratuitos às vezes devolvem finish_reason='error' no meio da resposta; o
    PydanticAI trata isso como UnexpectedModelBehavior, que por padrão NÃO aciona o fallback.
    """
    names = ("ModelAPIError", "ModelHTTPError", "UnexpectedModelBehavior")
    fallback_on = tuple(
        exc_type for exc_type in (getattr(pai_exceptions, n, None) for n in names) if exc_type
    )
    try:
        return FallbackModel(*models, fallback_on=fallback_on)
    except TypeError:  # versão sem o parâmetro fallback_on: usa o comportamento padrão
        return FallbackModel(*models)


_agent: Agent[AgentDeps, str] | None = None


def get_agent() -> Agent[AgentDeps, str]:
    """Instancia o agente sob demanda (permite importar o módulo sem chave de API)."""
    global _agent
    if _agent is None:
        _agent = Agent(
            _build_model(),
            deps_type=AgentDeps,
            output_type=str,
            instructions=build_system_prompt(),
            tools=[executar_sql],
            retries=config.TOOL_RETRIES,
            model_settings={"temperature": 0.0},
        )
    return _agent


def _describe_error(exc: BaseException) -> str:
    """Resume a causa real: o FallbackExceptionGroup esconde o erro de cada modelo."""
    sub_errors = getattr(exc, "exceptions", None)
    if sub_errors:
        return "; ".join(_describe_error(sub) for sub in sub_errors)
    return f"{type(exc).__name__}: {exc}"


# --------------------------------------------------------------------------- memória
def _extend_history(
    history: list[ModelMessage], question: str, answer: str
) -> list[ModelMessage]:
    """Memória de conversa enxuta: só pergunta e resposta final de cada turno.

    Descartar as chamadas de ferramenta antigas economiza tokens e evita histórico
    inconsistente (tool call sem retorno) ao cortar as mensagens mais antigas.
    """
    turn: list[ModelMessage] = [
        ModelRequest(parts=[UserPromptPart(content=question)]),
        ModelResponse(parts=[TextPart(content=answer)]),
    ]
    return (list(history) + turn)[-2 * config.HISTORY_TURNS :]


# --------------------------------------------------------------------------- cache
def _cache_key(question: str) -> str:
    return re.sub(r"\s+", " ", question.strip().lower())


def _load_cache() -> dict[str, dict]:
    try:
        return json.loads(config.CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_cache(cache: dict[str, dict]) -> None:
    try:
        config.CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        config.CACHE_PATH.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass  # cache é só otimização: falhar ao gravar não deve quebrar a resposta


def _from_cache(question: str, deps: AgentDeps) -> AgentAnswer | None:
    entry = _load_cache().get(_cache_key(question))
    if not entry:
        return None
    queries: list[ExecutedQuery] = []
    try:
        # Reexecuta o SQL salvo (gratuito) para ter as linhas disponíveis na CLI/avaliação.
        for sql in entry.get("sql", []):
            result = execute_query(validate_sql(sql), deps.db_path, deps.max_rows)
            queries.append(ExecutedQuery(sql=sql, result=result))
    except Exception:  # noqa: BLE001 - cache inválido/desatualizado: ignora e consulta o modelo
        return None
    return AgentAnswer(text=entry["answer"], queries=queries, from_cache=True)


def _store_cache(question: str, answer: str, queries: list[ExecutedQuery]) -> None:
    cache = _load_cache()
    cache[_cache_key(question)] = {
        "answer": answer,
        "sql": [q.sql for q in queries if q.result is not None],
        "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    _save_cache(cache)


# --------------------------------------------------------------------------- API pública
def ask(
    question: str,
    history: list[ModelMessage] | None = None,
    use_cache: bool | None = None,
) -> AgentAnswer:
    """Responde uma pergunta em linguagem natural.

    Args:
        question: pergunta do usuário.
        history: memória devolvida pela chamada anterior (``AgentAnswer.history``).
        use_cache: força/desliga o cache; ``None`` usa ``CACHE_ENABLED``.

    Raises:
        GuardrailError: pergunta inválida/bloqueada (nenhuma chamada ao modelo é feita).
        ConfigError: chave de API ou banco ausentes.
        AgentError: o modelo não conseguiu responder.
    """
    question = validate_question(question)
    history = list(history or [])
    cache_on = config.CACHE_ENABLED if use_cache is None else use_cache
    deps = AgentDeps()

    # Só usa cache em perguntas sem contexto: com memória, a resposta depende do histórico.
    if cache_on and not history:
        cached = _from_cache(question, deps)
        if cached:
            cached.history = _extend_history([], question, cached.text)
            return cached

    try:
        result = get_agent().run_sync(
            question,
            deps=deps,
            message_history=history or None,
            usage_limits=UsageLimits(request_limit=config.REQUEST_LIMIT_PER_QUESTION),
        )
    except UsageLimitExceeded as exc:
        raise AgentError(
            "O modelo precisou de chamadas demais para esta pergunta. Tente reformulá-la.",
            queries=deps.executed,
        ) from exc
    except config.ConfigError:
        raise
    except Exception as exc:  # noqa: BLE001 - rede, 429 em todos os modelos, resposta inválida...
        raise AgentError(
            f"Não consegui obter resposta do modelo. Detalhes: {_describe_error(exc)}\n"
            "Dicas: 401 = chave inválida/ausente no .env; 429 = modelo lotado ou cota diária "
            "(confira em openrouter.ai/activity); 'finish_reason error' = falha temporária do "
            "modelo gratuito (tente de novo em instantes).",
            queries=deps.executed,
        ) from exc

    answer_text = result.output
    if cache_on and not history and deps.last_successful() is not None:
        _store_cache(question, answer_text, deps.executed)

    # PydanticAI 1.x: result.usage() é método; 2.x: result.usage é propriedade.
    usage = result.usage
    if callable(usage):
        usage = usage()
    return AgentAnswer(
        text=answer_text,
        queries=deps.executed,
        history=_extend_history(history, question, answer_text),
        requests_used=getattr(usage, "requests", None),
    )


__all__ = ["AgentAnswer", "AgentError", "GuardrailError", "ask", "get_agent"]