"""Camada de acesso a dados do domínio de filmes.

Concentra toda a lógica de negócio que envolve o banco: find-or-create de
gêneros/pessoas/produtoras, CRUD de filmes, adição de avaliações e a
consulta paginada do catálogo.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.movies.models import (
    PERSON_TYPES,
    DimCompany,
    DimGenre,
    DimMovie,
    DimPerson,
    FactMoviePerformance,
    MovieReview,
    bridge_movie_genre,
)

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
    # populate_existing: a sessão reaproveita objetos já carregados; sem isso, após
    # criar/editar/avaliar, a releitura devolveria coleções antigas (ex.: sem a nova
    # avaliação) e `created_at` (gerado pelo banco) não seria carregado.
    return (
        select(DimMovie)
        .options(
            selectinload(DimMovie.genres),
            selectinload(DimMovie.people),
            selectinload(DimMovie.companies),
            selectinload(DimMovie.reviews),
        )
        .execution_options(populate_existing=True)
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
    db: AsyncSession, *, sk_movie_id: str, changes: dict[str, Any]
) -> DimMovie:
    """Aplica uma atualização parcial.

    `changes` deve conter só os campos enviados pelo cliente
    (`MovieUpdate.model_dump(exclude_unset=True)`). Assim é possível limpar campos
    opcionais enviando `None`, sem confundir com "campo não enviado".
    """

    movie = await get_movie_or_raise(db, sk_movie_id)

    for campo in ("ano_lancamento", "duracao_minutos", "sinopse", "status_filme"):
        if campo in changes:
            setattr(movie, campo, changes[campo])

    if changes.get("titulo") is not None:
        movie.titulo = changes["titulo"]

    if changes.get("generos") is not None:
        movie.genres = [await _get_or_create_genre(db, nome) for nome in changes["generos"]]

    if changes.get("diretores") is not None:
        # Preserva atores/roteiristas já vinculados; substitui só os diretores.
        outros_papeis = [p for p in movie.people if p.tipo_pessoa != "Diretor"]
        novos_diretores = [
            await _get_or_create_person(db, nome, "Diretor") for nome in changes["diretores"]
        ]
        movie.people = outros_papeis + novos_diretores

    await db.commit()
    return await get_movie_or_raise(db, sk_movie_id)


async def delete_movie(db: AsyncSession, sk_movie_id: str) -> None:
    await get_movie_or_raise(db, sk_movie_id)
    # DELETE direto: as FKs têm ON DELETE CASCADE (e o PRAGMA foreign_keys está ligado),
    # então avaliações, vínculos e métricas do filme saem junto. Evita carregar relações
    # lazy (performance, reviews_summary), o que falharia numa sessão assíncrona.
    await db.execute(
        delete(DimMovie).where(DimMovie.sk_movie_id == sk_movie_id),
        execution_options={"synchronize_session": False},
    )
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
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    search: str | None,
    genero: str | None = None,
    ano: int | None = None,
    ordem: str = "titulo",
) -> tuple[list[DimMovie], int, dict[str, tuple[float | None, int]]]:
    """Retorna (filmes da página, total, {sk_movie_id: (média em estrelas, qtd)})."""

    filters = []
    if search:
        filters.append(DimMovie.titulo.ilike(f"%{search.strip()}%"))
    if ano:
        filters.append(DimMovie.ano_lancamento == ano)
    if genero:
        filters.append(DimMovie.genres.any(func.lower(DimGenre.nome_genero) == genero.strip().lower()))

    count_stmt = select(func.count(DimMovie.sk_movie_id))
    for f in filters:
        count_stmt = count_stmt.where(f)
    total = (await db.execute(count_stmt)).scalar_one()

    list_stmt = select(DimMovie).options(selectinload(DimMovie.genres))
    if ordem == "nota":
        avg_sq = (
            select(MovieReview.sk_movie_id.label("mid"), func.avg(MovieReview.nota).label("media"))
            .group_by(MovieReview.sk_movie_id)
            .subquery()
        )
        list_stmt = list_stmt.outerjoin(avg_sq, avg_sq.c.mid == DimMovie.sk_movie_id)
        order_by = [avg_sq.c.media.desc().nulls_last(), DimMovie.titulo]
    elif ordem == "ano":
        order_by = [DimMovie.ano_lancamento.desc().nulls_last(), DimMovie.titulo]
    else:
        order_by = [DimMovie.titulo]

    for f in filters:
        list_stmt = list_stmt.where(f)
    list_stmt = list_stmt.order_by(*order_by).offset((page - 1) * page_size).limit(page_size)

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


async def list_genres(db: AsyncSession) -> list[str]:
    rows = await db.execute(select(DimGenre.nome_genero).order_by(DimGenre.nome_genero))
    return [nome for (nome,) in rows.all()]


async def get_insights(db: AsyncSession) -> dict:
    total_filmes = (await db.execute(select(func.count(DimMovie.sk_movie_id)))).scalar_one()
    total_aval, media = (
        await db.execute(
            select(func.count(MovieReview.sk_movie_review_id), func.avg(MovieReview.nota))
        )
    ).one()

    # Gêneros com melhor nota média dos usuários (mínimo de 30 avaliações).
    gen_rows = await db.execute(
        select(
            DimGenre.nome_genero,
            func.avg(MovieReview.nota),
            func.count(MovieReview.sk_movie_review_id),
        )
        .join(bridge_movie_genre, bridge_movie_genre.c.sk_genre_id == DimGenre.sk_genre_id)
        .join(MovieReview, MovieReview.sk_movie_id == bridge_movie_genre.c.sk_movie_id)
        .group_by(DimGenre.sk_genre_id, DimGenre.nome_genero)
        .having(func.count(MovieReview.sk_movie_review_id) >= 30)
        .order_by(func.avg(MovieReview.nota).desc())
        .limit(8)
    )

    # Filmes de maior lucro (orçamento a partir de US$ 1 milhão, para evitar dados sujos).
    perf = FactMoviePerformance
    luc_rows = await db.execute(
        select(DimMovie.sk_movie_id, DimMovie.titulo, perf.orcamento_usd, perf.receita_usd, perf.lucro_usd)
        .join(perf, perf.sk_movie_id == DimMovie.sk_movie_id)
        .where(perf.orcamento_usd >= 1_000_000, perf.receita_usd.is_not(None))
        .order_by(perf.lucro_usd.desc())
        .limit(8)
    )

    def num(v: object) -> float | None:
        return float(v) if v is not None else None

    return {
        "total_filmes": total_filmes,
        "total_avaliacoes": total_aval,
        "media_geral_estrelas": nota_to_stars(media) if media is not None else None,
        "generos": [
            {"nome": n, "nota_media_estrelas": nota_to_stars(a), "qtd": q}
            for n, a, q in gen_rows.all()
        ],
        "lucrativos": [
            {
                "sk_movie_id": mid,
                "titulo": titulo,
                "orcamento_usd": num(orc),
                "receita_usd": num(rec),
                "lucro_usd": num(luc) or 0.0,
            }
            for mid, titulo, orc, rec, luc in luc_rows.all()
        ],
    }