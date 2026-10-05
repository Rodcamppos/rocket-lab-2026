from __future__ import annotations
from typing import Any
from .db import QueryResult

MAX_POINTS = 25

def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_numeric_column(rows: list[tuple[Any, ...]], index: int) -> bool:
    values = [row[index] for row in rows if row[index] is not None]
    return bool(values) and all(_is_number(v) for v in values)


def _is_sorted(values: list[Any]) -> bool:
    """Coluna ordenada (e não constante): provavelmente a métrica do ORDER BY."""
    if any(v is None for v in values) or len(set(values)) < 2:
        return False
    return values == sorted(values) or values == sorted(values, reverse=True)


def _unique(labels: list[str]) -> list[str]:
    """Rótulos repetidos (filmes homônimos) ganham sufixo para não se fundirem no gráfico."""
    seen: dict[str, int] = {}
    result = []
    for label in labels:
        seen[label] = seen.get(label, 0) + 1
        result.append(label if seen[label] == 1 else f"{label} ({seen[label]})")
    return result


def chart_spec(result: QueryResult, max_points: int = MAX_POINTS) -> dict[str, Any] | None:
    """Devolve a especificação de um gráfico de barras ou ``None`` se não fizer sentido.

    Regras: 2 a ``max_points`` linhas; rótulo = 1ª coluna de texto (ou a coluna ``ano*``
    quando todas são numéricas); valor = a coluna numérica (exceto ``ano*``) que está
    ordenada, pois costuma ser a métrica do ranking; se nenhuma estiver, a última que não
    seja uma contagem (``qtd*``).
    """
    columns, rows = result.columns, result.rows
    if len(columns) < 2 or not 2 <= len(rows) <= max_points:
        return None

    def is_year(i: int) -> bool:
        return columns[i].lower().startswith("ano")

    numeric = [i for i in range(len(columns)) if _is_numeric_column(rows, i)]
    text = [i for i in range(len(columns)) if i not in numeric]
    values = [i for i in numeric if not is_year(i)]
    if not values:
        return None

    if text:
        label_i = text[0]
    else:
        years = [i for i in numeric if is_year(i)]
        if not years:
            return None
        label_i = years[0]
    sorted_columns = [i for i in values if _is_sorted([row[i] for row in rows])]
    if sorted_columns:
        value_i = sorted_columns[0]
    else:
        not_counts = [i for i in values if not columns[i].lower().startswith(("qtd", "quantidade"))]
        value_i = (not_counts or values)[-1]
    if label_i == value_i:
        return None

    return {
        "label_column": columns[label_i],
        "value_column": columns[value_i],
        "labels": _unique([str(row[label_i]) for row in rows]),
        "values": [row[value_i] for row in rows],
    }