import { Routes, Route } from 'react-router-dom';
import CatalogPage from './pages/CatalogPage';
import MovieDetailPage from './pages/MovieDetailPage';
import CreateMoviePage from './pages/CreateMoviePage';
import EditMoviePage from './pages/EditMoviePage';

function App() {
  return (
    <Routes>
      <Route path="/" element={<CatalogPage />} />
      <Route path="/movies/new" element={<CreateMoviePage />} />
      <Route path="/movies/:id/edit" element={<EditMoviePage />} />
      <Route path="/movies/:id" element={<MovieDetailPage />} />
    </Routes>
  );
}

export default App;