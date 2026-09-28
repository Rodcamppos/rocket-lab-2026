export interface MovieSummary {
  sk_movie_id: string;
  titulo: string;
  ano_lancamento: number;
  status_filme: string;
  generos: string[];
  nota_media_estrelas: number | null;
  qtd_avaliacoes: number;
}

export interface PaginatedMovies {
  items: MovieSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Review {
  sk_movie_review_id: string;
  nome: string;
  nota_estrelas: number;
  comentario: string;
  created_at: string;
}

export interface MovieDetail extends Omit<MovieSummary, 'generos'> {
  id_filme: string;
  data_lancamento: string | null;
  duracao_minutos: number;
  sinopse: string;
  url_poster: string | null;
  url_backdrop: string | null;
  generos: { sk_genre_id: string; nome_genero: string }[];
  diretores: { sk_person_id: string; nome_pessoa: string; tipo_pessoa: string }[];
  elenco: { sk_person_id: string; nome_pessoa: string; tipo_pessoa: string }[];
  produtoras: { sk_company_id: string; nome_produtora: string }[];
  reviews: Review[];
}