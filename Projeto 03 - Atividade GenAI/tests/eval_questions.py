"""Avaliação do agente: as 14 perguntas do enunciado com o SQL esperado de cada uma.

Dois modos:

    python -m tests.eval_questions
        Roda apenas o SQL esperado no banco (guardrails + banco). NÃO usa o LLM,
        não gasta a cota do OpenRouter. Serve para validar o ambiente e os dados.

    python -m tests.eval_questions --llm --only 1,4,9
        Pergunta ao agente e compara o resultado com o esperado.
        Cada pergunta usa ~2-3 das 50 requisições diárias: prefira --only.
        Use --all para rodar as 14 (cerca de 30-40 requisições!).

A comparação é heurística (empates e escolhas de métrica podem gerar falso FAIL):
confira manualmente os casos que falharem com `python main.py -q "..." --show-sql`.
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # permite rodar como script

from src.cinedata_agent.config import DB_PATH  # noqa: E402
from src.cinedata_agent.db import QueryResult, execute_query  # noqa: E402
from src.cinedata_agent.guardrails import validate_sql  # noqa: E402
from src.cinedata_agent.schema import GENEROS_PT_EN  # noqa: E402


@dataclass(frozen=True)
class EvalCase:
    id: int
    categoria: str
    pergunta: str
    sql: str
    # ordered: as chaves do topo devem coincidir, na ordem
    # set:     as chaves esperadas devem estar contidas no resultado do agente
    # value:   o valor da métrica da 1ª linha deve aparecer na 1ª linha do agente
    #          (para rankings com empates, onde os nomes podem variar legitimamente)
    mode: str = "ordered"
    key_cols: int = 1
    value_col: int = 0


CASES: list[EvalCase] = [
    # ------------------------------------------------ Bilheteria e Finanças
    EvalCase(
        1, "Bilheteria e Finanças", "Top 10 filmes com maior receita em R$",
        """
        SELECT m.titulo, m.ano_lancamento, f.receita_brl
        FROM fact_movies_performance f
        JOIN dim_movies m ON m.sk_movie_id = f.sk_movie_id
        WHERE f.receita_brl IS NOT NULL
        ORDER BY f.receita_brl DESC
        LIMIT 10
        """,
        mode="ordered",
    ),
    EvalCase(
        2, "Bilheteria e Finanças",
        "Lucro médio por gênero, considerando apenas filmes com receita informada",
        """
        SELECT g.nome_genero, ROUND(AVG(f.lucro_brl), 2) AS lucro_medio_brl
        FROM fact_movies_performance f
        JOIN bridge_movie_genre bg ON bg.sk_movie_id = f.sk_movie_id
        JOIN dim_genres g ON g.sk_genre_id = bg.sk_genre_id
        WHERE f.receita_brl IS NOT NULL
        GROUP BY g.sk_genre_id, g.nome_genero
        ORDER BY lucro_medio_brl DESC
        """,
        mode="set",
    ),
    EvalCase(
        3, "Bilheteria e Finanças",
        "Filmes com maior margem de lucro, entre os que possuem receita e orçamento informados",
        """
        SELECT m.titulo, m.ano_lancamento,
               ROUND(f.lucro_brl * 100.0 / f.receita_brl, 2) AS margem_pct
        FROM fact_movies_performance f
        JOIN dim_movies m ON m.sk_movie_id = f.sk_movie_id
        WHERE f.receita_brl IS NOT NULL AND f.orcamento_brl IS NOT NULL
        ORDER BY f.lucro_brl * 1.0 / f.receita_brl DESC
        LIMIT 10
        """,
        mode="value", value_col=2,
    ),
    # ------------------------------------------------ Popularidade e Engajamento
    EvalCase(
        4, "Popularidade e Engajamento", "Os 5 filmes mais populares",
        """
        SELECT m.titulo, m.ano_lancamento, f.popularidade
        FROM fact_movies_performance f
        JOIN dim_movies m ON m.sk_movie_id = f.sk_movie_id
        ORDER BY f.popularidade DESC
        LIMIT 5
        """,
        mode="ordered",
    ),
    EvalCase(
        5, "Popularidade e Engajamento",
        "Filmes com maior divergência entre a nota TMDB e a nota IMDb",
        """
        SELECT m.titulo, m.ano_lancamento, f.nota_tmdb, f.nota_imdb,
               ROUND(ABS(f.nota_tmdb - f.nota_imdb), 2) AS divergencia
        FROM fact_movies_performance f
        JOIN dim_movies m ON m.sk_movie_id = f.sk_movie_id
        WHERE f.nota_tmdb > 0 AND f.nota_imdb > 0
        ORDER BY ABS(f.nota_tmdb - f.nota_imdb) DESC
        LIMIT 10
        """,
        mode="value", value_col=4,
    ),
    EvalCase(
        6, "Popularidade e Engajamento", "Nota média IMDb por ano de lançamento",
        """
        SELECT m.ano_lancamento, ROUND(AVG(f.nota_imdb), 2) AS nota_media_imdb
        FROM fact_movies_performance f
        JOIN dim_movies m ON m.sk_movie_id = f.sk_movie_id
        WHERE f.nota_imdb > 0 AND m.status_filme = 'Lançado'
        GROUP BY m.ano_lancamento
        ORDER BY m.ano_lancamento
        """,
        mode="set",
    ),
    # ------------------------------------------------ Elenco e Equipe
    EvalCase(
        7, "Elenco e Equipe", "Ator com mais participações em filmes lançados nos últimos 5 anos",
        """
        SELECT p.nome_pessoa, COUNT(DISTINCT m.sk_movie_id) AS qtd_filmes
        FROM dim_movies m
        JOIN bridge_movie_person bp ON bp.sk_movie_id = m.sk_movie_id
        JOIN dim_people p ON p.sk_person_id = bp.sk_person_id
        WHERE p.tipo_pessoa = 'Ator'
          AND m.status_filme = 'Lançado'
          AND m.data_lancamento >= date('now', '-5 years')
          AND m.data_lancamento <= date('now')
        GROUP BY p.sk_person_id, p.nome_pessoa
        ORDER BY qtd_filmes DESC
        LIMIT 5
        """,
        mode="value", value_col=1,
    ),
    EvalCase(
        8, "Elenco e Equipe", "Diretores com maior nota média (mínimo de 5 filmes)",
        """
        SELECT p.nome_pessoa, COUNT(DISTINCT f.sk_movie_id) AS qtd_filmes,
               ROUND(AVG(f.nota_imdb), 2) AS nota_media_imdb
        FROM dim_people p
        JOIN bridge_movie_person bp ON bp.sk_person_id = p.sk_person_id
        JOIN fact_movies_performance f ON f.sk_movie_id = bp.sk_movie_id
        WHERE p.tipo_pessoa = 'Diretor' AND f.nota_imdb > 0
        GROUP BY p.sk_person_id, p.nome_pessoa
        HAVING COUNT(DISTINCT f.sk_movie_id) >= 5
        ORDER BY nota_media_imdb DESC, qtd_filmes DESC
        LIMIT 10
        """,
        mode="value", value_col=2,
    ),
    EvalCase(
        9, "Elenco e Equipe", "Dupla ator–diretor que mais trabalhou junta",
        """
        SELECT a.nome_pessoa AS ator, d.nome_pessoa AS diretor,
               COUNT(DISTINCT pa.sk_movie_id) AS qtd_filmes
        FROM bridge_movie_person pa
        JOIN dim_people a ON a.sk_person_id = pa.sk_person_id AND a.tipo_pessoa = 'Ator'
        JOIN bridge_movie_person pd ON pd.sk_movie_id = pa.sk_movie_id
        JOIN dim_people d ON d.sk_person_id = pd.sk_person_id AND d.tipo_pessoa = 'Diretor'
        GROUP BY a.sk_person_id, d.sk_person_id, a.nome_pessoa, d.nome_pessoa
        ORDER BY qtd_filmes DESC
        LIMIT 5
        """,
        mode="value", value_col=2,
    ),
    # ------------------------------------------------ Gêneros e Produtoras
    EvalCase(
        10, "Gêneros e Produtoras", "Quantidade de filmes por gênero",
        """
        SELECT g.nome_genero, COUNT(DISTINCT bg.sk_movie_id) AS qtd_filmes
        FROM bridge_movie_genre bg
        JOIN dim_genres g ON g.sk_genre_id = bg.sk_genre_id
        GROUP BY g.sk_genre_id, g.nome_genero
        ORDER BY qtd_filmes DESC
        """,
        mode="set",
    ),
    EvalCase(
        11, "Gêneros e Produtoras", "Produtora com maior lucro total",
        """
        SELECT c.nome_produtora, ROUND(SUM(f.lucro_brl), 2) AS lucro_total_brl
        FROM fact_movies_performance f
        JOIN bridge_movie_company bc ON bc.sk_movie_id = f.sk_movie_id
        JOIN dim_companies c ON c.sk_company_id = bc.sk_company_id
        WHERE f.receita_brl IS NOT NULL
        GROUP BY c.sk_company_id, c.nome_produtora
        ORDER BY SUM(f.lucro_brl) DESC
        LIMIT 5
        """,
        mode="ordered",
    ),
    EvalCase(
        12, "Gêneros e Produtoras", "Gênero com maior margem de lucro média",
        """
        SELECT g.nome_genero,
               ROUND(AVG(f.lucro_brl * 100.0 / f.receita_brl), 2) AS margem_media_pct,
               ROUND(SUM(f.lucro_brl) * 100.0 / SUM(f.receita_brl), 2) AS margem_agregada_pct,
               COUNT(DISTINCT f.sk_movie_id) AS qtd_filmes
        FROM fact_movies_performance f
        JOIN bridge_movie_genre bg ON bg.sk_movie_id = f.sk_movie_id
        JOIN dim_genres g ON g.sk_genre_id = bg.sk_genre_id
        WHERE f.receita_brl IS NOT NULL AND f.orcamento_brl IS NOT NULL
        GROUP BY g.sk_genre_id, g.nome_genero
        ORDER BY margem_media_pct DESC
        LIMIT 5
        """,
        mode="ordered",
    ),
    # ------------------------------------------------ Avaliações dos Usuários
    EvalCase(
        13, "Avaliações dos Usuários", "Filmes mais avaliados pelos usuários",
        """
        SELECT m.titulo, m.ano_lancamento, r.qtd_avaliacoes_usuarios
        FROM dim_reviews r
        JOIN dim_movies m ON m.sk_movie_id = r.sk_movie_id
        ORDER BY r.qtd_avaliacoes_usuarios DESC
        LIMIT 10
        """,
        mode="value", value_col=2,
    ),
    EvalCase(
        14, "Avaliações dos Usuários",
        "Filmes em que a nota média dos usuários mais diverge da nota IMDb",
        """
        SELECT m.titulo, m.ano_lancamento, r.nota_media_usuarios, f.nota_imdb,
               ROUND(ABS(r.nota_media_usuarios - f.nota_imdb), 2) AS divergencia
        FROM dim_reviews r
        JOIN dim_movies m ON m.sk_movie_id = r.sk_movie_id
        JOIN fact_movies_performance f ON f.sk_movie_id = r.sk_movie_id
        WHERE f.nota_imdb > 0
        ORDER BY ABS(r.nota_media_usuarios - f.nota_imdb) DESC
        LIMIT 10
        """,
        mode="value", value_col=4,
    ),
]


# ----------------------------------------------------------------------------- execução
def run_expected(case: EvalCase) -> QueryResult:
    """Roda o SQL esperado passando pelos mesmos guardrails do agente."""
    return execute_query(validate_sql(case.sql), max_rows=200)


# O agente pode devolver gêneros em português; normaliza para inglês antes de comparar.
_PT_TO_EN = {pt.lower(): en.lower() for pt, en in GENEROS_PT_EN.items()}


def _norm(values) -> tuple[str, ...]:
    texts = (str(v).strip().lower() for v in values)
    return tuple(_PT_TO_EN.get(text, text) for text in texts)


def evaluate(case: EvalCase, expected: QueryResult, actual: QueryResult) -> tuple[bool, str]:
    """Compara o resultado do agente com o esperado. Devolve (passou, detalhe)."""
    if not actual.rows:
        return False, "o agente não retornou linhas"

    if case.mode == "value":
        target = expected.rows[0][case.value_col]
        for cell in actual.rows[0]:
            if isinstance(cell, (int, float)) and math.isclose(
                float(cell), float(target), rel_tol=1e-4, abs_tol=0.01
            ):
                return True, f"métrica do topo = {target}"
        return False, f"esperava métrica {target} na 1ª linha; veio {actual.rows[0]}"

    expected_keys = [_norm(row[: case.key_cols]) for row in expected.rows]
    actual_keys = [_norm(row[: case.key_cols]) for row in actual.rows]
    if case.mode == "ordered":
        ok = actual_keys[: len(expected_keys)] == expected_keys
        return ok, "" if ok else f"esperado {expected_keys[:3]}...; veio {actual_keys[:3]}..."
    missing = [k for k in expected_keys if k not in set(actual_keys)]
    return (not missing), "" if not missing else f"faltaram {len(missing)} chaves, ex.: {missing[:3]}"


def _select(cases: list[EvalCase], only: str | None, run_all: bool) -> list[EvalCase]:
    if only:
        wanted = {int(x) for x in only.split(",") if x.strip()}
        return [c for c in cases if c.id in wanted]
    return cases if run_all else []


def run_sql_only() -> int:
    print("Modo SQL (sem LLM): validando o SQL esperado no banco...\n")
    failures = 0
    for case in CASES:
        start = time.perf_counter()
        try:
            result = run_expected(case)
            status, info = "OK  ", f"{len(result.rows)} linha(s); topo: {result.rows[0] if result.rows else '-'}"
        except Exception as exc:  # noqa: BLE001
            failures += 1
            status, info = "ERRO", f"{type(exc).__name__}: {exc}"
        print(f"[{status}] #{case.id:>2} {time.perf_counter() - start:5.1f}s  {case.pergunta}\n         {info}")
    print(f"\n{len(CASES) - failures}/{len(CASES)} consultas executaram com sucesso.")
    return 1 if failures else 0


def run_llm(selected: list[EvalCase], use_cache: bool) -> int:
    from src.cinedata_agent.agent import AgentError, ask
    from src.cinedata_agent.config import ConfigError
    from src.cinedata_agent.guardrails import GuardrailError

    print(f"Modo LLM: {len(selected)} pergunta(s) (~2-3 requisições cada).\n")
    passed = 0
    for index, case in enumerate(selected):
        expected = run_expected(case)
        try:
            answer = ask(case.pergunta, use_cache=use_cache)
        except (ConfigError, AgentError, GuardrailError) as exc:
            print(f"[ERRO] #{case.id:>2} {case.pergunta}\n         {exc}")
            for query in getattr(exc, "queries", []):
                status = f"erro: {query.error}" if query.error else "ok"
                print(f"         - SQL ({status}): {' '.join(query.sql.split())[:400]}")
            continue
        last = next((q for q in reversed(answer.queries) if q.result is not None), None)
        if last is None:
            print(f"[FAIL] #{case.id:>2} {case.pergunta}\n         nenhuma consulta bem-sucedida")
            continue
        ok, detail = evaluate(case, expected, last.result)
        passed += ok
        origem = "cache" if answer.from_cache else f"{answer.requests_used} req"
        print(f"[{'PASS' if ok else 'FAIL'}] #{case.id:>2} ({origem}) {case.pergunta}")
        if detail:
            print(f"         {detail}")
        if not ok:
            print(f"         SQL do agente: {' '.join(last.sql.split())[:500]}")
        if not answer.from_cache and index < len(selected) - 1:
            time.sleep(3)  # respeita o limite de 20 requisições/minuto
    print(f"\n{passed}/{len(selected)} aprovadas.")
    return 0 if passed == len(selected) else 1


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if not DB_PATH.exists():
        print(f"[erro] Banco não encontrado em '{DB_PATH}'. Coloque o cinerocket.db em data/.")
        return 1
    parser = argparse.ArgumentParser(description="Avaliação do CineData Agent.")
    parser.add_argument("--llm", action="store_true", help="usa o agente (gasta cota do OpenRouter)")
    parser.add_argument("--only", help="ids separados por vírgula (ex.: 1,4,9)")
    parser.add_argument("--all", action="store_true", help="roda todas as perguntas com o LLM")
    parser.add_argument("--no-cache", action="store_true", help="ignora o cache de respostas")
    args = parser.parse_args()

    if not args.llm:
        return run_sql_only()
    selected = _select(CASES, args.only, args.all)
    if not selected:
        parser.error("com --llm informe --only 1,4,9 ou --all")
    return run_llm(selected, use_cache=not args.no_cache)


if __name__ == "__main__":
    raise SystemExit(main())