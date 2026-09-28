import { useState } from 'react';
import axios from 'axios';

export function apiError(e: unknown, fallback: string): string {
  if (axios.isAxiosError(e)) {
    if (!e.response) return 'Não foi possível conectar à API. Confira se o backend está rodando.';
    const d = e.response.data?.detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d)) return d.map((x: { msg: string }) => x.msg).join('; ');
  }
  return fallback;
}

export function Poster({ title, url, children }: { title: string; url?: string | null; children?: React.ReactNode }) {
  const hue = [...title].reduce((a, c) => a + c.charCodeAt(0), 0) % 360;
  const img = !!url && /^https?:\/\//.test(url);
  const style = img
    ? { backgroundImage: `url(${url})` }
    : { backgroundImage: `linear-gradient(150deg,hsl(${hue} 40% 30%),hsl(${(hue + 60) % 360} 45% 16%))` };
  return (
    <div className="poster" style={style} role="img" aria-label={`Pôster de ${title}`}>
      {!img && (title.trim()[0] ?? '?').toUpperCase()}
      {children}
    </div>
  );
}

export function Stars({ value }: { value: number }) {
  return (
    <span className="stars" role="img" aria-label={`${value.toFixed(1)} de 5 estrelas`}>
      ★★★★★<span style={{ width: `${(value / 5) * 100}%` }}>★★★★★</span>
    </span>
  );
}

export function StarInput({ value, onChange }: { value: number; onChange: (n: number) => void }) {
  const [hover, setHover] = useState(0);
  return (
    <div className="starin" onMouseLeave={() => setHover(0)} role="radiogroup" aria-label="Nota de 1 a 5">
      {[1, 2, 3, 4, 5].map((n) => (
        <button key={n} type="button" role="radio" aria-checked={value === n} aria-label={`${n} estrelas`}
          className={n <= (hover || value) ? 'on' : ''} onMouseEnter={() => setHover(n)} onClick={() => onChange(n)}>★</button>
      ))}
    </div>
  );
}

export function StateBox({ title, text, children }: { title: string; text?: string; children?: React.ReactNode }) {
  return (
    <div className="state">
      <h2>{title}</h2>
      {text && <p className="muted">{text}</p>}
      {children}
    </div>
  );
}