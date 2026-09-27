"""Schemas Pydantic (request/response) do domínio de filmes."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class GenreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sk_genre_id: str
    nome_genero: str


class PersonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sk_person_id: str
    nome_pessoa: str
    tipo_pessoa: str


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sk_company_id: str
    nome_produtora: str


class ReviewOut(BaseModel):
    """Avaliação individual, já convertida para a escala de estrelas (1-5)."""

    sk_movie_review_id: str
    nome: str
    nota_estrelas: float
    comentario: str
    created_at: datetime


class ReviewCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    nota_estrelas: float = Field(ge=1, le=5, description="Nota de 1 a 5 estrelas")
    comentario: str = Field(min_length=1, max_length=4000)


class MovieCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=500)
    ano_lancamento: int | None = Field(default=None, ge=1870, le=2100)
    duracao_minutos: int | None = Field(default=None, ge=1)
    sinopse: str | None = Field(default=None, max_length=4000)
    status_filme: str | None = Field(default=None, max_length=50)
    diretores: list[str] = Field(default_factory=list, description="Nomes dos diretores")
    generos: list[str] = Field(default_factory=list, description="Nomes dos gêneros")


class MovieUpdate(BaseModel):
    """Todos os campos são opcionais — só o que for enviado é atualizado."""

    titulo: str | None = Field(default=None, min_length=1, max_length=500)
    ano_lancamento: int | None = Field(default=None, ge=1870, le=2100)
    duracao_minutos: int | None = Field(default=None, ge=1)
    sinopse: str | None = Field(default=None, max_length=4000)
    status_filme: str | None = Field(default=None, max_length=50)
    diretores: list[str] | None = None
    generos: list[str] | None = None


class MovieListItem(BaseModel):
    sk_movie_id: str
    titulo: str
    ano_lancamento: int | None
    status_filme: str | None
    generos: list[str]
    nota_media_estrelas: float | None
    qtd_avaliacoes: int


class MovieDetail(BaseModel):
    sk_movie_id: str
    id_filme: str
    titulo: str
    data_lancamento: date | None
    ano_lancamento: int | None
    duracao_minutos: int | None
    status_filme: str | None
    sinopse: str | None
    url_poster: str | None
    url_backdrop: str | None
    generos: list[GenreOut]
    diretores: list[PersonOut]
    elenco: list[PersonOut]
    produtoras: list[CompanyOut]
    nota_media_estrelas: float | None
    qtd_avaliacoes: int
    reviews: list[ReviewOut]


class PaginatedMovies(BaseModel):
    items: list[MovieListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
