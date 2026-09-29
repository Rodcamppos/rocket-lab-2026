import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createMovie } from '../api';

const STATUS_OPTIONS = ['Planejado', 'Em produção', 'Lançado'];

export default function CreateMoviePage() {
  const navigate = useNavigate();

  const [titulo, setTitulo] = useState('');
  const [anoLancamento, setAnoLancamento] = useState<number | ''>('');
  const [duracaoMinutos, setDuracaoMinutos] = useState<number | ''>('');
  const [sinopse, setSinopse] = useState('');
  const [statusFilme, setStatusFilme] = useState(STATUS_OPTIONS[2]);
  const [diretores, setDiretores] = useState('');
  const [generos, setGeneros] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const res = await createMovie({
        titulo,
        ano_lancamento: anoLancamento === '' ? null : Number(anoLancamento),
        duracao_minutos: duracaoMinutos === '' ? null : Number(duracaoMinutos),
        sinopse,
        status_filme: statusFilme,
        diretores: diretores
          .split(',')
          .map((d) => d.trim())
          .filter(Boolean),
        generos: generos
          .split(',')
          .map((g) => g.trim())
          .filter(Boolean),
      });
      const newId = (res.data as { sk_movie_id: string }).sk_movie_id;
      navigate(`/movies/${newId}`);
    } catch {
      setError('Não foi possível cadastrar o filme. Confira os campos obrigatórios.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: 500, margin: '0 auto', padding: 24 }}>
      <button onClick={() => navigate('/')}>← Voltar ao catálogo</button>

      <h1>Cadastrar novo filme</h1>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <label>
          Título *
          <input
            type="text"
            value={titulo}
            onChange={(e) => setTitulo(e.target.value)}
            required
            maxLength={120}
            style={{ width: '100%' }}
          />
        </label>

        <label>
          Ano de lançamento *
          <input
            type="number"
            value={anoLancamento}
            onChange={(e) => setAnoLancamento(e.target.value ? Number(e.target.value) : '')}
            required
            style={{ width: '100%' }}
          />
        </label>

        <label>
          Duração (minutos) *
          <input
            type="number"
            value={duracaoMinutos}
            onChange={(e) => setDuracaoMinutos(e.target.value ? Number(e.target.value) : '')}
            required
            style={{ width: '100%' }}
          />
        </label>

        <label>
          Status *
          <select value={statusFilme} onChange={(e) => setStatusFilme(e.target.value)} style={{ width: '100%' }}>
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </label>

        <label>
          Sinopse *
          <textarea
            value={sinopse}
            onChange={(e) => setSinopse(e.target.value)}
            required
            rows={4}
            style={{ width: '100%' }}
          />
        </label>

        <label>
          Diretores (separados por vírgula) *
          <input
            type="text"
            value={diretores}
            onChange={(e) => setDiretores(e.target.value)}
            placeholder="Denis Villeneuve, Fulano de Tal"
            required
            style={{ width: '100%' }}
          />
        </label>

        <label>
          Gêneros (separados por vírgula) *
          <input
            type="text"
            value={generos}
            onChange={(e) => setGeneros(e.target.value)}
            placeholder="Ficção Científica, Aventura"
            required
            style={{ width: '100%' }}
          />
        </label>

        <button type="submit" disabled={submitting}>
          {submitting ? 'Salvando...' : 'Cadastrar filme'}
        </button>
      </form>
    </div>
  );
}