import axios from 'axios';
import type { PaginatedMovies, MovieDetail } from './types';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

export const getMovies = (page = 1, pageSize = 20, search = '') =>
  client
    .get<PaginatedMovies>('/movies', { params: { page, page_size: pageSize, search: search || undefined } })
    .then((res) => res.data);

export const getMovie = (id: string) =>
  client.get<MovieDetail>(`/movies/${id}`).then((res) => res.data);

export const deleteMovie = (id: string) => client.delete(`/movies/${id}`);

export const addReview = (id: string, nome: string, nota_estrelas: number, comentario: string) =>
  client.post(`/movies/${id}/reviews`, { nome, nota_estrelas, comentario });

export interface MovieCreatePayload {
  titulo: string;
  ano_lancamento: number;
  duracao_minutos: number;
  sinopse: string;
  status_filme: string;
  diretores: string[];
  generos: string[];
}

export const createMovie = (payload: MovieCreatePayload) =>
  client.post('/movies', payload);

export const updateMovie = (id: string, payload: Partial<MovieCreatePayload>) =>
  client.patch(`/movies/${id}`, payload);