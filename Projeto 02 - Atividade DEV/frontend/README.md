# Frontend — Sistema de Avaliação de Filmes

Vite + React + TypeScript. Consome a API FastAPI do backend (`repo-base/backend`).

```bash
npm install
cp .env.example .env   # Windows: copy .env.example .env
npm run dev            # http://localhost:5173
```

| Script | Descrição |
| --- | --- |
| `npm run dev` | Servidor de desenvolvimento |
| `npm run build` | Checagem de tipos + build de produção |
| `npm run lint` | Lint com Oxlint |

`VITE_API_URL` (em `.env`) define a URL base da API; o padrão é `http://localhost:8000/api/v1`.
Instruções completas de execução estão no README da raiz do projeto.