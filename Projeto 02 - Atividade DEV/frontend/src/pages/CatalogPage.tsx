import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { getGenres, getMovies } from '../api';
import { apiError, Poster, StateBox } from '../components/ui';
import type { PaginatedMovies } from '../types';

/** Aplica mudanças nos parâmetros da URL; voltar à página 1 ao mudar filtros. */
const patch = (prev: URLSearchParams, changes: Record<string, string>, keepPage = false) => {
  const next = new URLSearchParams(prev);
  for (const [k, v] of Object.entries(changes)) {
    if (v) next.set(k, v);
    else next.delete(k);
  }
  if (!keepPage) next.delete('page');
  return next;
};

export default function CatalogPage() {
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get('page')) || 1);
  const q = params.get('q') ?? '';
  const genero = params.get('genero') ?? '';
  const ano = params.get('ano') ?? '';
  const ordem = params.get('ordem') ?? 'titulo';

  const [input, setInput] = useState(q);
  const [anoInput, setAnoInput] = useState(ano);
  const [generos, setGeneros] = useState<string[]>([]);
  const [data, setData] = useState<PaginatedMovies | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    getGenres().then(setGeneros).catch(() => setGeneros([]));
  }, []);

  useEffect(() => {
    if (input === q) return;
    const t = setTimeout(() => setParams((p) => patch(p, { q: input.trim() })), 350);
    return () => clearTimeout(t);
  }, [input, q, setParams]);

  useEffect(() => {
    if (anoInput === ano) return;
    const valid = anoInput === '' || (Number(anoInput) >= 1870 && Number(anoInput) <= 2100);
    if (!valid) return;
    const t = setTimeout(() => setParams((p) => patch(p, { ano: anoInput })), 500);
    return () => clearTimeout(t);
  }, [anoInput, ano, setParams]);

  useEffect(() => {
    let alive = true;
    setData(null);
    setError(null);
    getMovies(page, 24, q, { genero, ano, ordem })
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(apiError(e, 'Não foi possível carregar o catálogo.')));
    return () => { alive = false; };
  }, [page, q, genero, ano, ordem, tick]);

  const go = (p: number) => {
    setParams((prev) => patch(prev, { page: String(p) }, true));
    window.scrollTo({ top: 0 });
  };

  const hasFilters = !!(q || genero || ano);
  const clearAll = () => { setInput(''); setAnoInput(''); setParams({}); };

  return (
    <div className="page">
      <div className="top">
        <div>
          <h1>Catálogo de filmes</h1>
          <p className="muted" aria-live="polite">
            {data ? `${data.total.toLocaleString('pt-BR')} ${data.total === 1 ? 'filme' : 'filmes'}${hasFilters ? ' encontrados' : ' cadastrados'}` : 'Carregando...'}
          </p>
        </div>
        <Link to="/movies/new" className="btn primary">+ Adicionar filme</Link>
      </div>

      <label className="search">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
        <input type="search" aria-label="Buscar filme por título" placeholder="Buscar filme por título" value={input} onChange={(e) => setInput(e.target.value)} />
      </label>

      <div className="filters">
        <select aria-label="Filtrar por gênero" value={genero} onChange={(e) => setParams((p) => patch(p, { genero: e.target.value }))}>
          <option value="">Todos os gêneros</option>
          {generos.map((g) => <option key={g} value={g}>{g}</option>)}
        </select>
        <input type="number" aria-label="Filtrar por ano" placeholder="Ano" min={1870} max={2100} value={anoInput} onChange={(e) => setAnoInput(e.target.value)} style={{ width: 110 }} />
        <select aria-label="Ordenar por" value={ordem} onChange={(e) => setParams((p) => patch(p, { ordem: e.target.value === 'titulo' ? '' : e.target.value }))}>
          <option value="titulo">Ordem alfabética</option>
          <option value="nota">Melhor avaliados</option>
          <option value="ano">Mais recentes</option>
        </select>
        {(hasFilters || ordem !== 'titulo') && <button onClick={clearAll}>Limpar filtros</button>}
      </div>

      {error && <StateBox title="Não deu para carregar os filmes" text={error}><button className="primary" onClick={() => setTick((t) => t + 1)}>Tentar de novo</button></StateBox>}
      {!error && !data && <div className="grid">{Array.from({ length: 12 }, (_, i) => <div key={i} className="skel" />)}</div>}

      {data && data.items.length === 0 && (
        <StateBox title={hasFilters ? 'Nenhum filme encontrado' : 'Nenhum filme cadastrado'} text={hasFilters ? 'Tente outro título ou remova algum filtro.' : 'Cadastre o primeiro filme do catálogo.'}>
          {hasFilters ? <button onClick={clearAll}>Limpar filtros</button> : <Link to="/movies/new" className="btn primary">Cadastrar filme</Link>}
        </StateBox>
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="grid">
            {data.items.map((m) => (
              <Link key={m.sk_movie_id} to={`/movies/${m.sk_movie_id}`} className="card">
                <Poster title={m.titulo} url={m.url_poster}>
                  {m.nota_media_estrelas !== null && <span className="badge"><b>★</b>{m.nota_media_estrelas.toFixed(1)}</span>}
                </Poster>
                <h3>{m.titulo}</h3>
                <div className="chips">
                  {m.ano_lancamento ? <span className="chip">{m.ano_lancamento}</span> : null}
                  {m.generos.slice(0, 1).map((g) => <span key={g} className="chip">{g}</span>)}
                </div>
              </Link>
            ))}
          </div>
          <nav className="pager" aria-label="Paginação">
            <button disabled={page <= 1} onClick={() => go(page - 1)}>Anterior</button>
            <span className="muted">Página {data.page} de {data.total_pages.toLocaleString('pt-BR')}</span>
            <button disabled={page >= data.total_pages} onClick={() => go(page + 1)}>Próxima</button>
          </nav>
        </>
      )}
    </div>
  );
}