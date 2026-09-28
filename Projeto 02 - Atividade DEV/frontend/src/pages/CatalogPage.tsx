import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getMovies } from '../api';
import type { PaginatedMovies } from '../types';

export default function CatalogPage() {
  const [data, setData] = useState<PaginatedMovies | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getMovies(page, 20, search)
      .then(setData)
      .finally(() => setLoading(false));
  }, [page, search]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setSearch(inputValue);
  };

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: 24 }}>
      <h1>Catálogo de Filmes</h1>
      <Link to="/movies/new">
      <button style={{ marginBottom: 16 }}>+ Cadastrar novo filme</button>
      </Link>

      <form onSubmit={handleSearchSubmit} style={{ marginBottom: 16 }}>
        <input
          type="text"
          placeholder="Buscar por título..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          style={{ padding: 8, width: 300 }}
        />
        <button type="submit" style={{ padding: 8, marginLeft: 8 }}>
          Buscar
        </button>
      </form>

      {loading && <p>Carregando...</p>}

      {!loading && data && (
        <>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {data.items.map((movie) => (
              <li
                key={movie.sk_movie_id}
                style={{ padding: 12, borderBottom: '1px solid #ccc' }}
              >
                <Link to={`/movies/${movie.sk_movie_id}`}>
                  <strong>{movie.titulo}</strong> ({movie.ano_lancamento})
                </Link>
                <div>{movie.generos.join(', ')}</div>
                <div>
                  {movie.nota_media_estrelas !== null
                    ? `⭐ ${movie.nota_media_estrelas.toFixed(1)} (${movie.qtd_avaliacoes} avaliações)`
                    : 'Sem avaliações'}
                </div>
              </li>
            ))}
          </ul>

          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 16 }}>
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Anterior
            </button>
            <span>
              Página {data.page} de {data.total_pages} ({data.total} filmes)
            </span>
            <button
              disabled={page >= data.total_pages}
              onClick={() => setPage((p) => p + 1)}
            >
              Próxima
            </button>
          </div>
        </>
      )}
    </div>
  );
}