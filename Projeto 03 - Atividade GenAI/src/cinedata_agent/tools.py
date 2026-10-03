from __future__ import annotations
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from pydantic_ai import ModelRetry, RunContext
from .config import DB_PATH, MAX_ROWS
from .db import QueryResult, execute_query
from .guardrails import GuardrailError, validate_sql

@dataclass
class ExecutedQuery:
    """Registro de uma consulta tentada pelo agente (usado por --show-sql e pela avaliação)."""

    sql: str
    result: QueryResult | None = None
    error: str | None = None


@dataclass
class AgentDeps:
    """Dependências injetadas em cada execução do agente."""

    db_path: Path = DB_PATH
    max_rows: int = MAX_ROWS
    executed: list[ExecutedQuery] = field(default_factory=list)

    def last_successful(self) -> ExecutedQuery | None:
        for query in reversed(self.executed):
            if query.result is not None:
                return query
        return None


def executar_sql(ctx: RunContext[AgentDeps], sql: str) -> dict[str, Any]:
    """Executa uma consulta SQL de LEITURA na camada Gold (SQLite) e devolve as linhas.

    Use somente SELECT (ou WITH ... SELECT), uma única instrução, no dialeto SQLite.
    Em caso de erro, a mensagem explica o problema: corrija o SQL e chame de novo.

    Args:
        sql: A consulta SQLite a executar.
    """
    deps = ctx.deps

    try:
        clean_sql = validate_sql(sql)
    except GuardrailError as exc:
        deps.executed.append(ExecutedQuery(sql=sql, error=str(exc)))
        raise ModelRetry(f"Consulta bloqueada: {exc}") from exc

    try:
        result = execute_query(clean_sql, deps.db_path, deps.max_rows)
    except sqlite3.Error as exc:
        message = str(exc)
        if "interrupted" in message.lower():
            message = "a consulta excedeu o tempo limite; simplifique (filtre mais cedo, evite joins grandes)"
        deps.executed.append(ExecutedQuery(sql=clean_sql, error=message))
        raise ModelRetry(f"Erro ao executar o SQL: {message}. Corrija e tente novamente.") from exc

    deps.executed.append(ExecutedQuery(sql=clean_sql, result=result))
    return result.to_payload()
