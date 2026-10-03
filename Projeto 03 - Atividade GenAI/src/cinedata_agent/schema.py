from __future__ import annotations

GENEROS_PT_EN: dict[str, str] = {
    "Ação": "Action",
    "Aventura": "Adventure",
    "Animação": "Animation",
    "Comédia": "Comedy",
    "Crime": "Crime",
    "Documentário": "Documentary",
    "Drama": "Drama",
    "Família": "Family",
    "Fantasia": "Fantasy",
    "História": "History",
    "Terror": "Horror",
    "Música": "Music",
    "Mistério": "Mystery",
    "Romance": "Romance",
    "Ficção Científica": "Science Fiction",
    "Suspense": "Thriller",
    "Cinema TV": "Tv Movie",
    "Guerra": "War",
    "Faroeste": "Western",
}

SCHEMA_DESCRIPTION = """\
Banco SQLite (camada Gold do CineData, modelo dimensional). Datas são texto 'YYYY-MM-DD'.
Todas as junções usam sk_movie_id / sk_person_id / sk_genre_id / sk_company_id.

dim_movies (95.645 filmes) - PK sk_movie_id
  id_filme, titulo, data_lancamento, ano_lancamento, duracao_minutos,
  idioma_original (SEMPRE NULL - não usar),
  status_filme ('Lançado','Pós-Produção','Em Produção','Planejado'),
  sinopse, url_poster, url_backdrop

fact_movies_performance (1 linha por filme) - PK/FK sk_movie_id -> dim_movies
  orcamento_usd, receita_usd, lucro_usd, orcamento_brl, receita_brl, lucro_brl,
  popularidade (maior = mais popular), nota_tmdb, qtd_tmdb, nota_imdb, qtd_imdb
  (notas na escala 0-10)

dim_genres (19) - sk_genre_id, nome_genero (em inglês)
bridge_movie_genre - (sk_movie_id, sk_genre_id): N:N filme <-> gênero

dim_people (424.656) - sk_person_id, nome_pessoa, tipo_pessoa IN ('Ator','Diretor','Roteirista')
bridge_movie_person (745.450) - (sk_movie_id, sk_person_id): N:N filme <-> pessoa

dim_companies (45.941) - sk_company_id, nome_produtora
bridge_movie_company - (sk_movie_id, sk_company_id): N:N filme <-> produtora

dim_reviews (40.267; 1 linha por filme avaliado por usuários)
  sk_review_id, sk_movie_id, qtd_avaliacoes_usuarios, nota_media_usuarios (0-10)
movie_reviews (43.666) - avaliações individuais:
  id, sk_movie_review_id, sk_movie_id, name, rating (0-10), text, created_at

(Ignore a tabela alembic_version: é só controle de migração.)
"""
