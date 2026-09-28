import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getMovie, updateMovie } from '../api';

const STATUS_OPTIONS = ['Planejado', 'Em produção', 'Lançado'];

export default function EditMoviePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [titulo, setTitulo] = useState('');
  const [anoLancamento, setAnoLancamento] = useState<number | ''>('');
  const [duracaoMinutos, setDuracaoMinutos] = useState<number | ''>('');
  const [sinopse, setSinopse] = useState('');
  const [statusFilme, setStatusFilme] = useState(STATUS_OPTIONS[2]);
  const [diretores, setDiretores] = useState('');
  const [generos, setGeneros] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getMovie(id).then((movie) => {
      setTitulo(movie.titulo);
      setAnoLancamento(movie.ano_lancamento);
      setDuracaoMinutos(movie.duracao_minutos);
      setSinopse(movie.sinopse);
      setStatusFilme(movie.status_filme);
      setDiretores(movie.diretores.map((d) => d.nome_pessoa).join(', '));
      setGeneros(movie.generos.map((g) => g.nome_genero).join(', '));
      setLoading(false);
    });
  }, [id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;
    setError(null);
    setSubmitting(true);

    try {
      await updateMovie(id, {
        titulo,
        ano_lancamento: Number(anoLancamento),
        duracao_minutos: Number(duracaoMinutos),
        sinopse,
        status_filme: statusFilme,
        diretores: diretores.split(',').map((d) => d.trim()).filter(Boolean),
        generos: generos.split(',').map((g) => g.trim()).filter(Boolean),
      });
      navigate(`/movies/${id}`);
    } catch {
      setError('Não foi possível salvar as alterações. Confira os campos.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <p style={{ padding: 24 }}>Carregando...</p>;

  return (
    <div style={{ maxWidth: 500, margin: '0 auto', padding: 24 }}>
      <button onClick={() => navigate(`/movies/${id}`)}>← Voltar aos detalhes</button>

      <h1>Editar filme</h1>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <label>
          Título *
          <input type="text" value={titulo} onChange={(e) => setTitulo(e.target.value)} required maxLength={120} style={{ width: '100%' }} />
        </label>

        <label>
          Ano de lançamento *
          <input type="number" value={anoLancamento} onChange={(e) => setAnoLancamento(e.target.value ? Number(e.target.value) : '')} required style={{ width: '100%' }} />
        </label>

        <label>
          Duração (minutos) *
          <input type="number" value={duracaoMinutos} onChange={(e) => setDuracaoMinutos(e.target.value ? Number(e.target.value) : '')} required style={{ width: '100%' }} />
        </label>

        <label>
          Status *
          <select value={statusFilme} onChange={(e) => setStatusFilme(e.target.value)} style={{ width: '100%' }}>
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </label>

        <label>
          Sinopse *
          <textarea value={sinopse} onChange={(e) => setSinopse(e.target.value)} required rows={4} style={{ width: '100%' }} />
        </label>

        <label>
          Diretores (separados por vírgula) *
          <input type="text" value={diretores} onChange={(e) => setDiretores(e.target.value)} required style={{ width: '100%' }} />
        </label>

        <label>
          Gêneros (separados por vírgula) *
          <input type="text" value={generos} onChange={(e) => setGeneros(e.target.value)} required style={{ width: '100%' }} />
        </label>

        <button type="submit" disabled={submitting}>
          {submitting ? 'Salvando...' : 'Salvar alterações'}
        </button>
      </form>
    </div>
  );
}