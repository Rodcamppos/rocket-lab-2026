import { Link, Route, Routes } from 'react-router-dom';
import CatalogPage from './pages/CatalogPage';
import MovieDetailPage from './pages/MovieDetailPage';
import CreateMoviePage from './pages/CreateMoviePage';
import EditMoviePage from './pages/EditMoviePage';
import InsightsPage from './pages/InsightsPage';

export default function App() {
  return (
    <>
      <header className="header">
        <div className="header-in">
          <Link to="/" className="brand">K.A. Filmes (Visaflix)</Link>
          <nav className="nav" style={{ display: 'flex', gap: 20 }}>
            <Link to="/">Catálogo</Link>
            <Link to="/insights">Insights</Link>
          </nav>
        </div>
      </header>
      <Routes>
        <Route path="/" element={<CatalogPage />} />
        <Route path="/insights" element={<InsightsPage />} />
        <Route path="/movies/new" element={<CreateMoviePage />} />
        <Route path="/movies/:id/edit" element={<EditMoviePage />} />
        <Route path="/movies/:id" element={<MovieDetailPage />} />
      </Routes>
    </>
  );
}