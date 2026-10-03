from __future__ import annotations
import re
from .config import MAX_QUESTION_CHARS

class GuardrailError(ValueError):
    """Entrada ou SQL rejeitado pelos guardrails."""

_NOISE = re.compile(
    r"""
    (?P<str>'(?:[^']|'')*')        |
    (?P<ident>"(?:[^"]|"")*")      |
    (?P<line>--[^\n]*)             |
    (?P<block>/\*.*?\*/)
    """,
    re.VERBOSE | re.DOTALL,
)

_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|ATTACH|DETACH|PRAGMA|VACUUM|"
    r"REINDEX|ANALYZE|TRUNCATE|GRANT|REVOKE|LOAD_EXTENSION)\b|\bREPLACE\s+INTO\b",
    re.IGNORECASE,
)

_INJECTION_HINTS = re.compile(
    r"(ignore|esque[cç]a|desconsidere)\s+(todas\s+)?(as\s+)?(instru[cç][oõ]es|regras)"
    r"|ignore\s+(all\s+)?(previous|prior)\s+instructions"
    r"|(mostre|revele|imprima|show|reveal)\s+(o\s+|your\s+)?(system\s+prompt|prompt\s+do\s+sistema)",
    re.IGNORECASE,
)


def _mask(sql: str) -> str:
    """Troca strings/comentários por vazio para a análise não ter falsos positivos."""

    def repl(match: re.Match[str]) -> str:
        return "''" if match.lastgroup in {"str", "ident"} else " "

    return _NOISE.sub(repl, sql)


def validate_sql(sql: str) -> str:
    """Valida o SQL e o devolve limpo (sem ';' final). Levanta ``GuardrailError``."""
    if not sql or not sql.strip():
        raise GuardrailError("O SQL está vazio.")

    cleaned = sql.strip().rstrip(";").strip()
    masked = _mask(cleaned).strip()

    if ";" in masked:
        raise GuardrailError("Envie apenas UMA instrução SQL por chamada.")
    if not re.match(r"(?is)^\s*(SELECT|WITH)\b", masked):
        raise GuardrailError("Só são permitidas consultas de leitura (SELECT ou WITH ... SELECT).")

    forbidden = _FORBIDDEN.search(masked)
    if forbidden:
        raise GuardrailError(
            f"Comando não permitido ('{forbidden.group(0).upper()}'): o agente é somente leitura."
        )
    return cleaned


def validate_question(question: str) -> str:
    """Valida a pergunta do usuário. Levanta ``GuardrailError``."""
    text = (question or "").strip()
    if not text:
        raise GuardrailError("Digite uma pergunta sobre o catálogo de filmes.")
    if len(text) > MAX_QUESTION_CHARS:
        raise GuardrailError(
            f"Pergunta muito longa ({len(text)} caracteres; máximo {MAX_QUESTION_CHARS})."
        )
    if _INJECTION_HINTS.search(text):
        raise GuardrailError(
            "Não posso alterar minhas instruções. Pergunte algo sobre o catálogo de filmes."
        )
    return text
