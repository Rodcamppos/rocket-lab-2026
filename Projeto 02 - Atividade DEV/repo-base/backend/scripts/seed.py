"""script de carga (seed) dos dados iniciais no banco SQLite do projeto.

lê os 10 CSVs fornecidos (colocados em backend/data/) e insere no banco
na ordem correta de dependência (dimensões -> bridges -> fato -> reviews),
respeitando as foreign keys já criadas pela migração Alembic.

uso (a partir da pasta backend/, com o venv ativado):
    python scripts/seed.py
"""

from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
DB_PATH = BACKEND_DIR / "rocketlab.db"

# Ordem importa: dimensões primeiro, depois bridges (dependem das dims),
# depois o fato e as reviews individuais (dependem de dim_movies).
TABLES: list[tuple[str, str]] = [
    ("dim_movies.csv", "dim_movies"),
    ("dim_genres.csv", "dim_genres"),
    ("dim_people.csv", "dim_people"),
    ("dim_companies.csv", "dim_companies"),
    ("dim_reviews.csv", "dim_reviews"),
    ("bridge_movie_genre.csv", "bridge_movie_genre"),
    ("bridge_movie_company.csv", "bridge_movie_company"),
    ("bridge_movie_person.csv", "bridge_movie_person"),
    ("fact_movies_performance.csv", "fact_movies_performance"),
    ("movies_reviews.csv", "movie_reviews"),
]


def load_csv_rows(path: Path) -> list[dict[str, str | None]]:
    """Lê um CSV e converte strings vazias em None (NULL no banco)."""

    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [
            {key: (value if value != "" else None) for key, value in row.items()}
            for row in reader
        ]


def find_csv(filename: str) -> Path | None:
    """Procura o CSV direto em DATA_DIR ou em qualquer subpasta dela."""

    direct = DATA_DIR / filename
    if direct.exists():
        return direct

    matches = list(DATA_DIR.rglob(filename))
    return matches[0] if matches else None


def seed_table(cursor: sqlite3.Cursor, filename: str, table: str) -> None:
    csv_path = find_csv(filename)

    if csv_path is None:
        print(f"AVISO: {filename} não encontrado em {DATA_DIR} (nem em subpastas) — pulando '{table}'.")
        return

    rows = load_csv_rows(csv_path)

    if not rows:
        print(f"{table}: CSV vazio, nada para inserir.")
        return

    columns = list(rows[0].keys())
    column_list = ", ".join(columns)
    placeholders = ", ".join(f":{col}" for col in columns)
    sql = f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})"

    cursor.executemany(sql, rows)
    print(f"{table}: {len(rows)} linhas inseridas.")


def already_seeded(cursor: sqlite3.Cursor) -> bool:
    cursor.execute("SELECT COUNT(*) FROM dim_movies")
    return cursor.fetchone()[0] > 0


def main() -> None:
    if not DB_PATH.exists():
        print(
            f"ERRO: banco não encontrado em {DB_PATH}. "
            "Rode 'alembic upgrade head' antes de popular os dados."
        )
        sys.exit(1)

    if not DATA_DIR.exists():
        print(
            f"ERRO: pasta {DATA_DIR} não encontrada. "
            "Crie backend/data/ e coloque os 10 CSVs fornecidos lá dentro."
        )
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    if already_seeded(cursor):
        print(
            "O banco já parece estar populado (dim_movies não está vazia). "
            "Para popular de novo do zero, apague rocketlab.db, rode "
            "'alembic upgrade head' e execute este script novamente."
        )
        conn.close()
        sys.exit(0)

    for filename, table in TABLES:
        seed_table(cursor, filename, table)

    conn.commit()
    conn.close()
    print("Seed concluído com sucesso.")


if __name__ == "__main__":
    main()