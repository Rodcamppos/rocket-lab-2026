""" Uso:
    python main.py                         # modo interativo (com memória de conversa)
    python main.py -q "Top 10 filmes com maior receita em R$"
    python main.py -q "..." --show-sql     # mostra também o SQL executado
"""

from __future__ import annotations

import argparse
import sys

from src.cinedata_agent.agent import AgentAnswer, AgentError, ask
from src.cinedata_agent.config import ConfigError
from src.cinedata_agent.guardrails import GuardrailError

EXIT_WORDS = {"sair", "exit", "quit", "q"}
BANNER = (
    "CineData Agent - pergunte sobre o catálogo de filmes.\n"
    "Comandos: 'sair' encerra | '/limpar' zera a memória da conversa.\n"
)


def _print_answer(answer: AgentAnswer, show_sql: bool) -> None:
    print(f"\n{answer.text}\n")
    if show_sql:
        for query in answer.queries:
            status = f"erro: {query.error}" if query.error else "ok"
            print(f"--- SQL ({status}) ---\n{query.sql}\n")
    meta = []
    if answer.from_cache:
        meta.append("resposta do cache (0 requisições)")
    elif answer.requests_used is not None:
        meta.append(f"{answer.requests_used} requisição(ões) ao modelo")
    if meta:
        print(f"[{' | '.join(meta)}]\n")


def _ask_safely(
    question: str, history: list | None, use_cache: bool | None, show_sql: bool
) -> tuple[bool, list | None]:
    """Executa uma pergunta tratando os erros esperados. Devolve (sucesso, histórico)."""
    try:
        answer = ask(question, history=history, use_cache=use_cache)
    except GuardrailError as exc:
        print(f"\n[bloqueado] {exc}\n")
        return False, history
    except (ConfigError, AgentError) as exc:
        print(f"\n[erro] {exc}\n")
        return False, history
    _print_answer(answer, show_sql)
    return True, answer.history


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):  # acentos corretos no terminal do Windows
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Agente Text-to-SQL do CineData Analytics.")
    parser.add_argument("-q", "--question", help="pergunta única (sem modo interativo)")
    parser.add_argument("--show-sql", action="store_true", help="exibe o SQL executado")
    parser.add_argument("--no-cache", action="store_true", help="ignora o cache de respostas")
    args = parser.parse_args(argv)
    use_cache = False if args.no_cache else None

    if args.question:
        ok, _ = _ask_safely(args.question, None, use_cache, args.show_sql)
        return 0 if ok else 1

    print(BANNER)
    history: list = []
    while True:
        try:
            question = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            continue
        if question.lower() in EXIT_WORDS:
            break
        if question.lower() == "/limpar":
            history = []
            print("Memória da conversa zerada.\n")
            continue
        _, history = _ask_safely(question, history, use_cache, args.show_sql)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
