import axios from 'axios';
import type { PaginatedMovies, MovieDetail, Insights } from './types';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

export interface MovieFilters {
  genero?: string;
  ano?: string;
  ordem?: string;
}

export const getMovies = (page = 1, pageSize = 20, search = '', filters: MovieFilters = {}) =>
  client
    .get<PaginatedMovies>('/movies', {
      params: {
        page,
        page_size: pageSize,
        search: search || undefined,
        genero: filters.genero || undefined,
        ano: filters.ano || undefined,
        ordem: filters.ordem && filters.ordem !== 'titulo' ? filters.ordem : undefined,
      },
    })
    .then((res) => res.data);

export const getGenres = () => client.get<string[]>('/movies/generos').then((res) => res.data);

export const getInsights = () => client.get<Insights>('/movies/insights').then((res) => res.data);

export const getMovie = (id: string) =>
  client.get<MovieDetail>(`/movies/${id}`).then((res) => res.data);

export const deleteMovie = (id: string) => client.delete(`/movies/${id}`);

export const addReview = (id: string, nome: string, nota_estrelas: number, comentario: string) =>
  client.post(`/movies/${id}/reviews`, { nome, nota_estrelas, comentario });

export interface MovieCreatePayload {
  titulo: string;
  ano_lancamento: number | null;
  duracao_minutos: number | null;
  sinopse: string;
  status_filme: string;
  diretores: string[];
  generos: string[];
}

export const createMovie = (payload: MovieCreatePayload) =>
  client.post('/movies', payload);

export const updateMovie = (id: string, payload: Partial<MovieCreatePayload>) =>
  client.patch(`/movies/${id}`, payload);