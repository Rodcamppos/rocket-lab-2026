"""Schemas Pydantic (request/response) do domínio de filmes."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _clean_names(values: list[str] | None) -> list[str] | None:
    """Remove espaços, descarta nomes vazios e duplicados (sem diferenciar maiúsculas)."""

    if values is None:
        return None
    vistos: set[str] = set()
    limpos: list[str] = []
    for valor in values:
        nome = valor.strip()
        if nome and nome.lower() not in vistos:
            vistos.add(nome.lower())
            limpos.append(nome)
    return limpos


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

    @field_validator("titulo")
    @classmethod
    def _titulo_sem_espacos(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("O título não pode ser vazio")
        return v

    @field_validator("diretores", "generos")
    @classmethod
    def _limpar_nomes(cls, v: list[str]) -> list[str]:
        return _clean_names(v) or []


class MovieUpdate(BaseModel):
    """Atualização parcial (PATCH).

    Só os campos enviados são alterados. Campos opcionais (`ano_lancamento`,
    `duracao_minutos`, `sinopse`, `status_filme`) aceitam `null` para serem limpos;
    `titulo` não pode ser nulo. Use `model_dump(exclude_unset=True)` ao aplicar.
    """

    titulo: str | None = Field(default=None, min_length=1, max_length=500)
    ano_lancamento: int | None = Field(default=None, ge=1870, le=2100)
    duracao_minutos: int | None = Field(default=None, ge=1)
    sinopse: str | None = Field(default=None, max_length=4000)
    status_filme: str | None = Field(default=None, max_length=50)
    diretores: list[str] | None = None
    generos: list[str] | None = None

    @field_validator("titulo")
    @classmethod
    def _titulo_valido(cls, v: str | None) -> str:
        if v is None or not v.strip():
            raise ValueError("O título não pode ser vazio nem nulo")
        return v.strip()

    @field_validator("diretores", "generos")
    @classmethod
    def _limpar_nomes(cls, v: list[str] | None) -> list[str] | None:
        return _clean_names(v)


class MovieListItem(BaseModel):
    sk_movie_id: str
    titulo: str
    url_poster: str | None = None  # NOVO
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


class GenreInsight(BaseModel):
    nome: str
    nota_media_estrelas: float
    qtd: int


class ProfitableMovie(BaseModel):
    sk_movie_id: str
    titulo: str
    orcamento_usd: float | None
    receita_usd: float | None
    lucro_usd: float


class InsightsOut(BaseModel):
    total_filmes: int
    total_avaliacoes: int
    media_geral_estrelas: float | None
    generos: list[GenreInsight]
    lucrativos: list[ProfitableMovie]