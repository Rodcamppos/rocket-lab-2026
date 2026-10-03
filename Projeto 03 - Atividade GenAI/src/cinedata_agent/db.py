from __future__ import annotations
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from .config import DB_PATH, MAX_ROWS, QUERY_TIMEOUT_S, ConfigError

@dataclass(frozen=True)
class QueryResult:
    """Resultado de uma consulta (já limitado a ``max_rows`` linhas)."""

    columns: list[str]
    rows: list[tuple[Any, ...]]
    truncated: bool = False

    def to_payload(self) -> dict[str, Any]:
        """Formato devolvido ao modelo pela ferramenta."""
        payload: dict[str, Any] = {
            "colunas": self.columns,
            "linhas": [list(row) for row in self.rows],
            "qtd_linhas": len(self.rows),
            "truncado": self.truncated,
        }
        if self.truncated:
            payload["aviso"] = (
                "Resultado cortado no limite de linhas; refine a consulta "
                "(agregue ou use LIMIT) se precisar de menos dados."
            )
        return payload


def connect_readonly(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Abre o banco em modo somente leitura (mode=ro + query_only)."""
    db_path = Path(db_path)
    if not db_path.exists():
        raise ConfigError(
            f"Banco de dados não encontrado em '{db_path}'. Baixe o cinerocket.db da "
            "pasta compartilhada da atividade e coloque-o em data/ (veja o README)."
        )
    uri = db_path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.execute("PRAGMA query_only = ON")
    return conn


def _clean(value: Any) -> Any:
    return round(value, 4) if isinstance(value, float) else value


def execute_query(
    sql: str,
    db_path: Path = DB_PATH,
    max_rows: int = MAX_ROWS,
    timeout_s: int = QUERY_TIMEOUT_S,
) -> QueryResult:
    """Executa ``sql`` e devolve no máximo ``max_rows`` linhas.

    Levanta ``sqlite3.Error`` em caso de SQL inválido ou de estouro de tempo.
    """
    conn = connect_readonly(db_path)
    deadline = time.monotonic() + timeout_s
    # Aborta consultas pesadas: o handler é chamado a cada 10 mil instruções da VM.
    conn.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 10_000)
    try:
        cursor = conn.execute(sql)
        columns = [col[0] for col in cursor.description] if cursor.description else []
        fetched = cursor.fetchmany(max_rows + 1)
    finally:
        conn.close()

    truncated = len(fetched) > max_rows
    rows = [tuple(_clean(v) for v in row) for row in fetched[:max_rows]]
    return QueryResult(columns=columns, rows=rows, truncated=truncated)
