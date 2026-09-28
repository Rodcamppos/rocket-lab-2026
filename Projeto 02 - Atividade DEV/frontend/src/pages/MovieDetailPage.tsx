import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { addReview, deleteMovie, getMovie } from '../api';
import type { MovieDetail } from '../types';

export default function MovieDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [movie, setMovie] = useState<MovieDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [nome, setNome] = useState('');
  const [nota, setNota] = useState(5);
  const [comentario, setComentario] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadMovie = () => {
    if (!id) return;
    setLoading(true);
    getMovie(id)
      .then(setMovie)
      .catch(() => setError('Filme não encontrado.'))
      .finally(() => setLoading(false));
  };

  useEffect(loadMovie, [id]);

  const handleDelete = async () => {
    if (!id || !confirm('Tem certeza que deseja remover este filme?')) return;
    await deleteMovie(id);
    navigate('/');
  };

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;
    setSubmitting(true);
    try {
      await addReview(id, nome, nota, comentario);
      setNome('');
      setNota(5);
      setComentario('');
      loadMovie();
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <p style={{ padding: 24 }}>Carregando...</p>;
  if (error || !movie) return <p style={{ padding: 24 }}>{error ?? 'Erro ao carregar filme.'}</p>;

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: 24 }}>
      <button onClick={() => navigate('/')}>← Voltar ao catálogo</button>

      <h1>
        {movie.titulo} ({movie.ano_lancamento})
      </h1>
      <p>
        <strong>Status:</strong> {movie.status_filme} · <strong>Duração:</strong>{' '}
        {movie.duracao_minutos} min
      </p>
      <p>{movie.sinopse}</p>

      <p>
        <strong>Gêneros:</strong>{' '}
        {movie.generos.map((g) => g.nome_genero).join(', ') || '—'}
      </p>
      <p>
        <strong>Diretores:</strong>{' '}
        {movie.diretores.map((d) => d.nome_pessoa).join(', ') || '—'}
      </p>
      <p>
        <strong>Elenco:</strong>{' '}
        {movie.elenco.map((p) => p.nome_pessoa).join(', ') || '—'}
      </p>
      <p>
        <strong>Produtoras:</strong>{' '}
        {movie.produtoras.map((c) => c.nome_produtora).join(', ') || '—'}
      </p>

      <p>
        <strong>Nota média:</strong>{' '}
        {movie.nota_media_estrelas !== null
          ? `⭐ ${movie.nota_media_estrelas.toFixed(1)} (${movie.qtd_avaliacoes} avaliações)`
          : 'Sem avaliações'}
      </p>

      <button onClick={handleDelete} style={{ color: 'red' }}>
        Remover filme<button onClick={() => navigate(`/movies/${id}/edit`)} style={{ marginLeft: 8 }}>
  Editar filme
</button>
      </button>

      <hr style={{ margin: '24px 0' }} />

      <h2>Avaliações</h2>
      {movie.reviews.length === 0 && <p>Nenhuma avaliação ainda.</p>}
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {movie.reviews.map((r) => (
          <li key={r.sk_movie_review_id} style={{ padding: 12, borderBottom: '1px solid #ccc' }}>
            <strong>{r.nome}</strong> — ⭐ {r.nota_estrelas}
            <p>{r.comentario}</p>
            <small>{new Date(r.created_at).toLocaleString('pt-BR')}</small>
          </li>
        ))}
      </ul>

      <h3>Adicionar avaliação</h3>
      <form onSubmit={handleReviewSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 400 }}>
        <input
          type="text"
          placeholder="Seu nome"
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          required
          maxLength={120}
        />
        <label>
          Nota (1 a 5):
          <input
            type="number"
            min={1}
            max={5}
            value={nota}
            onChange={(e) => setNota(Number(e.target.value))}
            required
          />
        </label>
        <textarea
          placeholder="Comentário"
          value={comentario}
          onChange={(e) => setComentario(e.target.value)}
          required
          maxLength={4000}
          rows={3}
        />
        <button type="submit" disabled={submitting}>
          {submitting ? 'Enviando...' : 'Enviar avaliação'}
        </button>
      </form>
    </div>
  );
}