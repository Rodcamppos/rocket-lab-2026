"""Endpoints REST do domínio de filmes."""

from __future__ import annotations

import math
import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.movies import repository
from app.movies.models import DimMovie
from app.movies.repository import MovieNotFoundError, nota_to_stars
from app.movies.schemas import (
    MovieCreate,
    MovieDetail,
    MovieListItem,
    MovieUpdate,
    PaginatedMovies,
    ReviewCreate,
    ReviewOut,
)

router = APIRouter()


def _clean_titulo(titulo: str) -> str:
    """Colapsa sequências de 2+ aspas duplas (sujeira de escaping malformado
    na base original, ex: '""Blessed""' ou 'Floyd ""Money"" Mayweather')
    em uma única aspas, e remove sobras nas pontas."""

    colapsado = re.sub(r'"{2,}', '"', titulo)
    return colapsado.strip().strip('"').strip()


def _movie_to_detail(movie: DimMovie) -> MovieDetail:
    diretores = [p for p in movie.people if p.tipo_pessoa == "Diretor"]
    elenco = [p for p in movie.people if p.tipo_pessoa == "Ator"]

    reviews = sorted(movie.reviews, key=lambda r: r.created_at, reverse=True)
    qtd = len(reviews)
    media = round(sum(r.nota for r in reviews) / qtd / 2, 2) if qtd else None

    return MovieDetail(
        sk_movie_id=movie.sk_movie_id,
        id_filme=movie.id_filme,
        titulo=_clean_titulo(movie.titulo),
        data_lancamento=movie.data_lancamento,
        ano_lancamento=movie.ano_lancamento,
        duracao_minutos=movie.duracao_minutos,
        status_filme=movie.status_filme,
        sinopse=movie.sinopse,
        url_poster=movie.url_poster,
        url_backdrop=movie.url_backdrop,
        generos=list(movie.genres),
        diretores=diretores,
        elenco=elenco,
        produtoras=list(movie.companies),
        nota_media_estrelas=media,
        qtd_avaliacoes=qtd,
        reviews=[
            ReviewOut(
                sk_movie_review_id=r.sk_movie_review_id,
                nome=r.nome,
                nota_estrelas=nota_to_stars(r.nota),
                comentario=r.comentario,
                created_at=r.created_at,
            )
            for r in reviews
        ],
    )


@router.get("", response_model=PaginatedMovies)
async def get_movies(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, description="Busca por título (case-insensitive)"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedMovies:
    movies, total, stats = await repository.list_movies(
        db, page=page, page_size=page_size, search=search
    )

    items = [
        MovieListItem(
            sk_movie_id=m.sk_movie_id,
            titulo=_clean_titulo(m.titulo),
            ano_lancamento=m.ano_lancamento,
            status_filme=m.status_filme,
            generos=[g.nome_genero for g in m.genres],
            nota_media_estrelas=stats.get(m.sk_movie_id, (None, 0))[0],
            qtd_avaliacoes=stats.get(m.sk_movie_id, (None, 0))[1],
        )
        for m in movies
    ]

    total_pages = math.ceil(total / page_size) if total else 0

    return PaginatedMovies(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


@router.get("/{sk_movie_id}", response_model=MovieDetail)
async def get_movie(sk_movie_id: str, db: AsyncSession = Depends(get_db)) -> MovieDetail:
    try:
        movie = await repository.get_movie_or_raise(db, sk_movie_id)
    except MovieNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Filme não encontrado."
        ) from exc
    return _movie_to_detail(movie)


@router.post("", response_model=MovieDetail, status_code=status.HTTP_201_CREATED)
async def create_movie(payload: MovieCreate, db: AsyncSession = Depends(get_db)) -> MovieDetail:
    movie = await repository.create_movie(
        db,
        titulo=payload.titulo,
        ano_lancamento=payload.ano_lancamento,
        duracao_minutos=payload.duracao_minutos,
        sinopse=payload.sinopse,
        status_filme=payload.status_filme,
        diretores=payload.diretores,
        generos=payload.generos,
    )
    return _movie_to_detail(movie)


@router.patch("/{sk_movie_id}", response_model=MovieDetail)
async def update_movie(
    sk_movie_id: str, payload: MovieUpdate, db: AsyncSession = Depends(get_db)
) -> MovieDetail:
    try:
        movie = await repository.update_movie(
            db,
            sk_movie_id=sk_movie_id,
            titulo=payload.titulo,
            ano_lancamento=payload.ano_lancamento,
            duracao_minutos=payload.duracao_minutos,
            sinopse=payload.sinopse,
            status_filme=payload.status_filme,
            diretores=payload.diretores,
            generos=payload.generos,
        )
    except MovieNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Filme não encontrado."
        ) from exc
    return _movie_to_detail(movie)


@router.delete("/{sk_movie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(sk_movie_id: str, db: AsyncSession = Depends(get_db)) -> None:
    try:
        await repository.delete_movie(db, sk_movie_id)
    except MovieNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Filme não encontrado."
        ) from exc


@router.post(
    "/{sk_movie_id}/reviews", response_model=MovieDetail, status_code=status.HTTP_201_CREATED
)
async def add_review(
    sk_movie_id: str, payload: ReviewCreate, db: AsyncSession = Depends(get_db)
) -> MovieDetail:
    try:
        movie = await repository.add_review(
            db,
            sk_movie_id=sk_movie_id,
            nome=payload.nome,
            nota_estrelas=payload.nota_estrelas,
            comentario=payload.comentario,
        )
    except MovieNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Filme não encontrado."
        ) from exc
    return _movie_to_detail(movie)