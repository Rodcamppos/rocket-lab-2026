"""Camada de acesso a dados do domínio de filmes.

Concentra toda a lógica de negócio que envolve o banco: find-or-create de
gêneros/pessoas/produtoras, CRUD de filmes, adição de avaliações e a
consulta paginada do catálogo.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.movies.models import PERSON_TYPES, DimCompany, DimGenre, DimMovie, DimPerson, MovieReview


class MovieNotFoundError(Exception):
    """Levantado quando um filme não é encontrado pelo sk_movie_id."""


def stars_to_nota(stars: float) -> float:
    """Converte a nota em estrelas (1-5, o que a API expõe) para a escala
    interna 0-10 já usada pela coluna `nota` (herdada da base fornecida)."""

    return round(stars * 2, 2)


def nota_to_stars(nota: float) -> float:
    """Converte a escala interna 0-10 de volta para estrelas (1-5)."""

    return round(nota / 2, 2)


async def _get_or_create_genre(db: AsyncSession, nome: str) -> DimGenre:
    nome = nome.strip()
    result = await db.execute(
        select(DimGenre).where(func.lower(DimGenre.nome_genero) == nome.lower())
    )
    genre = result.scalar_one_or_none()
    if genre is None:
        genre = DimGenre(nome_genero=nome)
        db.add(genre)
        await db.flush()
    return genre


async def _get_or_create_company(db: AsyncSession, nome: str) -> DimCompany:
    nome = nome.strip()
    result = await db.execute(
        select(DimCompany).where(func.lower(DimCompany.nome_produtora) == nome.lower())
    )
    company = result.scalar_one_or_none()
    if company is None:
        company = DimCompany(nome_produtora=nome)
        db.add(company)
        await db.flush()
    return company


async def _get_or_create_person(db: AsyncSession, nome: str, tipo: str) -> DimPerson:
    if tipo not in PERSON_TYPES:
        raise ValueError(f"tipo_pessoa inválido: {tipo!r}. Use um de {PERSON_TYPES}.")

    nome = nome.strip()
    result = await db.execute(
        select(DimPerson).where(
            func.lower(DimPerson.nome_pessoa) == nome.lower(),
            DimPerson.tipo_pessoa == tipo,
        )
    )
    person = result.scalar_one_or_none()
    if person is None:
        person = DimPerson(nome_pessoa=nome, tipo_pessoa=tipo)
        db.add(person)
        await db.flush()
    return person


def _movie_detail_query():
    return select(DimMovie).options(
        selectinload(DimMovie.genres),
        selectinload(DimMovie.people),
        selectinload(DimMovie.companies),
        selectinload(DimMovie.reviews),
    )


async def get_movie_or_raise(db: AsyncSession, sk_movie_id: str) -> DimMovie:
    result = await db.execute(_movie_detail_query().where(DimMovie.sk_movie_id == sk_movie_id))
    movie = result.scalar_one_or_none()
    if movie is None:
        raise MovieNotFoundError(sk_movie_id)
    return movie


async def create_movie(
    db: AsyncSession,
    *,
    titulo: str,
    ano_lancamento: int | None,
    duracao_minutos: int | None,
    sinopse: str | None,
    status_filme: str | None,
    diretores: list[str],
    generos: list[str],
) -> DimMovie:
    movie = DimMovie(
        id_filme=f"local-{uuid4().hex[:12]}",
        titulo=titulo,
        ano_lancamento=ano_lancamento,
        duracao_minutos=duracao_minutos,
        sinopse=sinopse,
        status_filme=status_filme,
    )

    for nome in generos:
        movie.genres.append(await _get_or_create_genre(db, nome))

    for nome in diretores:
        movie.people.append(await _get_or_create_person(db, nome, "Diretor"))

    db.add(movie)
    await db.commit()
    return await get_movie_or_raise(db, movie.sk_movie_id)


async def update_movie(
    db: AsyncSession,
    *,
    sk_movie_id: str,
    titulo: str | None,
    ano_lancamento: int | None,
    duracao_minutos: int | None,
    sinopse: str | None,
    status_filme: str | None,
    diretores: list[str] | None,
    generos: list[str] | None,
) -> DimMovie:
    movie = await get_movie_or_raise(db, sk_movie_id)

    if titulo is not None:
        movie.titulo = titulo
    if ano_lancamento is not None:
        movie.ano_lancamento = ano_lancamento
    if duracao_minutos is not None:
        movie.duracao_minutos = duracao_minutos
    if sinopse is not None:
        movie.sinopse = sinopse
    if status_filme is not None:
        movie.status_filme = status_filme

    if generos is not None:
        movie.genres = [await _get_or_create_genre(db, nome) for nome in generos]

    if diretores is not None:
        # Preserva atores/roteiristas já vinculados; substitui só os diretores.
        outros_papeis = [p for p in movie.people if p.tipo_pessoa != "Diretor"]
        novos_diretores = [await _get_or_create_person(db, nome, "Diretor") for nome in diretores]
        movie.people = outros_papeis + novos_diretores

    await db.commit()
    return await get_movie_or_raise(db, sk_movie_id)


async def delete_movie(db: AsyncSession, sk_movie_id: str) -> None:
    movie = await get_movie_or_raise(db, sk_movie_id)
    await db.delete(movie)
    await db.commit()


async def add_review(
    db: AsyncSession, *, sk_movie_id: str, nome: str, nota_estrelas: float, comentario: str
) -> DimMovie:
    # Garante que o filme existe antes de aceitar a avaliação (senão, 404).
    await get_movie_or_raise(db, sk_movie_id)

    review = MovieReview(
        sk_movie_id=sk_movie_id,
        nome=nome,
        nota=stars_to_nota(nota_estrelas),
        comentario=comentario,
    )
    db.add(review)
    await db.commit()
    return await get_movie_or_raise(db, sk_movie_id)


async def list_movies(
    db: AsyncSession, *, page: int, page_size: int, search: str | None
) -> tuple[list[DimMovie], int, dict[str, tuple[float | None, int]]]:
    """Retorna (filmes da página, total de filmes, {sk_movie_id: (média em estrelas, qtd)})."""

    filters = []
    if search:
        filters.append(DimMovie.titulo.ilike(f"%{search.strip()}%"))

    count_stmt = select(func.count(DimMovie.sk_movie_id))
    for f in filters:
        count_stmt = count_stmt.where(f)
    total = (await db.execute(count_stmt)).scalar_one()

    list_stmt = select(DimMovie).options(selectinload(DimMovie.genres))
    for f in filters:
        list_stmt = list_stmt.where(f)
    list_stmt = list_stmt.order_by(DimMovie.titulo).offset((page - 1) * page_size).limit(page_size)

    movies = list((await db.execute(list_stmt)).scalars().all())

    movie_ids = [m.sk_movie_id for m in movies]
    stats: dict[str, tuple[float | None, int]] = {}
    if movie_ids:
        stats_stmt = (
            select(
                MovieReview.sk_movie_id,
                func.avg(MovieReview.nota),
                func.count(MovieReview.sk_movie_review_id),
            )
            .where(MovieReview.sk_movie_id.in_(movie_ids))
            .group_by(MovieReview.sk_movie_id)
        )
        for sk_movie_id, avg_nota, qtd in (await db.execute(stats_stmt)).all():
            stats[sk_movie_id] = (nota_to_stars(avg_nota) if avg_nota is not None else None, qtd)

    return movies, total, stats
