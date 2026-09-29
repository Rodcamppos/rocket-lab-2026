import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getInsights } from '../api';
import { apiError, StateBox } from '../components/ui';
import type { Insights } from '../types';

const usd = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 1 });

export default function InsightsPage() {
  const [data, setData] = useState<Insights | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let alive = true;
    setError(null);
    getInsights()
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(apiError(e, 'Não foi possível carregar os insights.')));
    return () => { alive = false; };
  }, [tick]);

  if (error) return <div className="page"><StateBox title="Insights indisponíveis" text={error}><button className="primary" onClick={() => setTick((t) => t + 1)}>Tentar de novo</button></StateBox></div>;
  if (!data) return <div className="page"><p className="muted">Carregando insights...</p></div>;

  const maxLucro = Math.max(...data.lucrativos.map((l) => l.lucro_usd), 1);

  return (
    <div className="page">
      <h1 style={{ fontSize: '2.6rem' }}>Insights</h1>
      <p className="muted">Um panorama do catálogo, calculado a partir das avaliações e do desempenho financeiro.</p>

      <div className="stats">
        <div className="stat"><b>{data.total_filmes.toLocaleString('pt-BR')}</b><span className="muted">filmes no catálogo</span></div>
        <div className="stat"><b>{data.total_avaliacoes.toLocaleString('pt-BR')}</b><span className="muted">avaliações registradas</span></div>
        <div className="stat"><b>{data.media_geral_estrelas !== null ? `★ ${data.media_geral_estrelas.toFixed(2)}` : '—'}</b><span className="muted">nota média geral</span></div>
      </div>

      <div className="cols" style={{ marginTop: 40 }}>
        <section>
          <h2 className="sec">Gêneros mais bem avaliados</h2>
          {data.generos.length === 0 && <p className="muted">Ainda não há avaliações suficientes por gênero.</p>}
          {data.generos.map((g) => (
            <div key={g.nome} className="barrow">
              <div className="barlabel"><span>{g.nome}</span><span className="muted">★ {g.nota_media_estrelas.toFixed(2)} · {g.qtd.toLocaleString('pt-BR')} avaliações</span></div>
              <div className="bar"><div style={{ width: `${(g.nota_media_estrelas / 5) * 100}%` }} /></div>
            </div>
          ))}
        </section>

        <section>
          <h2 className="sec">Maiores lucros de bilheteria</h2>
          {data.lucrativos.length === 0 && <p className="muted">Sem dados financeiros disponíveis.</p>}
          {data.lucrativos.map((f) => (
            <div key={f.sk_movie_id} className="barrow">
              <div className="barlabel">
                <Link to={`/movies/${f.sk_movie_id}`}>{f.titulo}</Link>
                <span className="muted">{usd.format(f.lucro_usd)}</span>
              </div>
              <div className="bar"><div style={{ width: `${(f.lucro_usd / maxLucro) * 100}%` }} /></div>
              <span className="muted" style={{ fontSize: '.78rem' }}>Orçamento {f.orcamento_usd ? usd.format(f.orcamento_usd) : '—'} → receita {f.receita_usd ? usd.format(f.receita_usd) : '—'}</span>
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}