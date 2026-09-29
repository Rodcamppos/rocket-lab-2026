import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { addReview, deleteMovie, getMovie } from '../api';
import { apiError, Poster, StarInput, StateBox, Stars } from '../components/ui';
import type { MovieDetail } from '../types';

const STATUS: Record<string, string> = { Released: 'Lançado', 'Post Production': 'Pós-produção', 'In Production': 'Em produção', Planned: 'Planejado' };

export default function MovieDetailPage() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const [movie, setMovie] = useState<MovieDetail | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [delErr, setDelErr] = useState<string | null>(null);
  const [nome, setNome] = useState('');
  const [nota, setNota] = useState(0);
  const [comentario, setComentario] = useState('');
  const [sending, setSending] = useState(false);
  const [revErr, setRevErr] = useState<string | null>(null);
  const [revOk, setRevOk] = useState(false);

  const load = useCallback(() => {
    setLoadErr(null);
    getMovie(id).then(setMovie).catch((e) => setLoadErr(apiError(e, 'Não foi possível carregar o filme.')));
  }, [id]);
  useEffect(load, [load]);

  const remove = async () => {
    setDeleting(true);
    try { await deleteMovie(id); nav('/'); }
    catch (e) { setDelErr(apiError(e, 'Não foi possível remover o filme.')); setConfirming(false); setDeleting(false); }
  };

  const sendReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nota) { setRevErr('Escolha uma nota de 1 a 5 estrelas.'); return; }
    setSending(true); setRevErr(null); setRevOk(false);
    try {
      await addReview(id, nome.trim(), nota, comentario.trim());
      setNome(''); setNota(0); setComentario(''); setRevOk(true);
      load();
    } catch (err) { setRevErr(apiError(err, 'Não foi possível enviar a avaliação.')); }
    finally { setSending(false); }
  };

  if (loadErr) return <div className="page"><StateBox title="Filme indisponível" text={loadErr}><button className="primary" onClick={load}>Tentar de novo</button></StateBox></div>;
  if (!movie) return <div className="page"><p className="muted">Carregando...</p></div>;

  const meta = [movie.ano_lancamento, movie.duracao_minutos ? `${Math.floor(movie.duracao_minutos / 60)}h ${movie.duracao_minutos % 60}min` : null, movie.status_filme ? (STATUS[movie.status_filme] ?? movie.status_filme) : null].filter(Boolean).join('  •  ');
  const bg = movie.url_backdrop && /^https?:\/\//.test(movie.url_backdrop) ? { backgroundImage: `url(${movie.url_backdrop})` } : undefined;

  return (
    <>
      <section className="backdrop" style={bg}>
        <div className="header-in" style={{ height: 'auto', paddingTop: 20, position: 'relative' }}>
          <Link to="/" className="back">← Voltar ao catálogo</Link>
        </div>
        <div className="page hero">
          <Poster title={movie.titulo} url={movie.url_poster} />
          <div>
            <h1>{movie.titulo}</h1>
            <p className="muted" style={{ margin: '8px 0' }}>{meta || 'Sem detalhes de lançamento'}</p>
            <p className="muted" style={{ margin: 0 }}>
              Direção: <strong style={{ color: 'var(--ink)' }}>{movie.diretores.map((d) => d.nome_pessoa).join(', ') || 'Dados indisponíveis'}</strong>
            </p>
            <div className="ratebox">
              {movie.nota_media_estrelas !== null
                ? <><Stars value={movie.nota_media_estrelas} /><b>{movie.nota_media_estrelas.toFixed(1)}</b><span className="muted">({movie.qtd_avaliacoes} {movie.qtd_avaliacoes === 1 ? 'avaliação' : 'avaliações'})</span></>
                : <span className="muted">Ainda sem avaliações. Seja o primeiro a avaliar.</span>}
            </div>
            <div className="chips" style={{ marginBottom: 14 }}>{movie.generos.map((g) => <span key={g.sk_genre_id} className="chip">{g.nome_genero}</span>)}</div>
            <p>{movie.sinopse || <span className="muted">Este filme ainda não tem sinopse.</span>}</p>

            {/* Botões irmãos (não aninhados): corrige o bug de Editar acionar Remover */}
            <div className="actions">
              <Link to={`/movies/${id}/edit`} className="btn">Editar filme</Link>
              {!confirming
                ? <button className="danger" onClick={() => setConfirming(true)}>Remover filme</button>
                : <>
                    <span className="muted">Apagar este filme e suas avaliações?</span>
                    <button className="danger" onClick={remove} disabled={deleting}>{deleting ? 'Removendo...' : 'Sim, remover'}</button>
                    <button onClick={() => setConfirming(false)}>Cancelar</button>
                  </>}
            </div>
            {delErr && <div className="err" role="alert" style={{ marginTop: 12 }}>{delErr}</div>}
          </div>
        </div>
      </section>

      <div className="page" style={{ paddingTop: 12 }}>
        {movie.elenco.length > 0 && (
          <>
            <h2 className="sec">Elenco</h2>
            <div className="people">
              {movie.elenco.slice(0, 16).map((p) => <div key={p.sk_person_id} className="person"><b>{p.nome_pessoa}</b><span className="muted">Ator</span></div>)}
            </div>
          </>
        )}
        {movie.produtoras.length > 0 && (
          <>
            <h2 className="sec">Produtoras</h2>
            <div className="chips" style={{ marginBottom: 40 }}>{movie.produtoras.map((c) => <span key={c.sk_company_id} className="chip">{c.nome_produtora}</span>)}</div>
          </>
        )}

        <div className="cols">
          <div>
            <h2 className="sec">Avaliações</h2>
            {movie.reviews.length === 0 && <p className="muted">Nenhuma avaliação ainda.</p>}
            {movie.reviews.slice(0, 50).map((r) => (
              <article key={r.sk_movie_review_id} className="review">
                <div className="rhead">
                  <span className="avatar">{(r.nome.trim()[0] ?? '?').toUpperCase()}</span>
                  <strong>{r.nome}</strong>
                  <Stars value={r.nota_estrelas} />
                </div>
                <p>{r.comentario}</p>
                <span className="muted">{new Date(r.created_at).toLocaleDateString('pt-BR')}</span>
              </article>
            ))}
            {movie.reviews.length > 50 && <p className="muted">Mostrando as 50 avaliações mais recentes de {movie.reviews.length}.</p>}
          </div>

          <form className="form" onSubmit={sendReview}>
            <h2 className="sec" style={{ margin: 0 }}>Deixe sua avaliação</h2>
            {revErr && <div className="err" role="alert">{revErr}</div>}
            {revOk && <div className="ok" role="status">Avaliação enviada.</div>}
            <label className="field">Seu nome<input value={nome} onChange={(e) => setNome(e.target.value)} required maxLength={120} /></label>
            <div className="field">Nota<StarInput value={nota} onChange={setNota} /></div>
            <label className="field">Comentário<textarea rows={4} value={comentario} onChange={(e) => setComentario(e.target.value)} required maxLength={4000} /></label>
            <button className="primary" disabled={sending || !nome.trim() || !comentario.trim()}>{sending ? 'Enviando...' : 'Enviar avaliação'}</button>
          </form>
        </div>
      </div>
    </>
  );
}