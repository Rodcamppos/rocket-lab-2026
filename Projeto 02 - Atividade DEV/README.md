# K.A. Filmes (Visaflix) — Sistema de Avaliação de Filmes

Aplicação full stack para catalogar filmes, consultar detalhes e registrar avaliações, inspirada em plataformas como o Letterboxd. Desenvolvida para a **Atividade DEV do Rocket Lab 2026.2 (Visagio)**. O usuário do sistema é o Administrador do catálogo.

## Funcionalidades

- Catálogo paginado (24 filmes por página) com barra de busca por título
- Filtros por gênero e ano, e ordenação (alfabética, melhor avaliados, mais recentes)
- Detalhes do filme: sinopse, duração, status, gêneros, diretores, elenco e produtoras
- Histórico de avaliações (resenhas e notas, as 50 mais recentes) e média geral de cada filme
- Adicionar avaliação a um filme (nota de 1 a 5 estrelas + resenha em texto)
- Cadastrar, editar e remover filmes
- Página de Insights: totais, gêneros mais bem avaliados e filmes de maior lucro
- Testes automatizados do backend (CRUD, avaliações e média, busca, paginação e filtros)

## Stack

| Camada | Tecnologias |
| --- | --- |
| Frontend | Vite, React, TypeScript, axios, react-router-dom |
| Backend | FastAPI, SQLAlchemy 2 (async), Alembic |
| Banco de dados | SQLite |

## Estrutura do projeto

```
.
├── frontend/                  # Vite + React + TypeScript
│   └── src/
│       ├── pages/             # Catálogo, Detalhes, Cadastro, Edição e Insights
│       ├── components/        # ui.tsx (componentes comuns)
│       ├── api.ts             # Chamadas à API
│       └── types.ts           # Tipos da API
└── repo-base/
    └── backend/
        ├── app/               # API FastAPI (api, core, db, movies)
        ├── data/              # CSVs de carga inicial
        ├── migrations/        # Migrações Alembic
        ├── scripts/seed.py    # Carga dos CSVs no banco
        └── tests/
```

## Pré-requisitos

- Python 3.11 ou superior
- Node.js 20.19 ou superior (com npm)

## Como executar

Use dois terminais: um para o backend e outro para o frontend. Os comandos são mostrados para **PowerShell (Windows)** e para **Linux/macOS**, sempre a partir da raiz do projeto (a pasta que contém `frontend/` e `repo-base/`).

### 1. Backend

**Windows (PowerShell):**

```powershell
cd repo-base\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
python -m alembic upgrade head
python scripts/seed.py
python -m uvicorn app.main:app --reload
```

**Linux/macOS (bash/zsh):**

```bash
cd repo-base/backend
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
python -m alembic upgrade head
python scripts/seed.py
python -m uvicorn app.main:app --reload
```

O que cada passo faz:

1. `alembic upgrade head` cria as tabelas no arquivo `rocketlab.db` (as tabelas são criadas somente pelo Alembic).
2. `scripts/seed.py` carrega os 10 CSVs de `repo-base/backend/data/` no banco. São mais de 1,7 milhão de linhas, então **essa etapa pode levar alguns minutos**.
3. `uvicorn` sobe a API.

Endereços do backend:

- API: http://localhost:8000
- Documentação interativa (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/health

### 2. Frontend

Em outro terminal, a partir da raiz do projeto:

**Windows (PowerShell):**

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

**Linux/macOS:**

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Acesse http://localhost:5173.

| Script | Descrição |
| --- | --- |
| `npm run dev` | Servidor de desenvolvimento |
| `npm run build` | Checagem de tipos + build de produção |
| `npm run lint` | Lint com Oxlint |

## Dados iniciais (CSVs)

Os 10 CSVs de carga inicial ficam versionados em `repo-base/backend/data/`. O `seed.py` os encontra mesmo dentro de subpastas.

Os arquivos somam cerca de 230 MB, e o maior deles (`bridge_movie_person.csv`) tem cerca de 97 MB. O GitHub bloqueia arquivos acima de 100 MB e exibe um aviso acima de 50 MB, então o maior CSV passa, mas com aviso. Se algum push for recusado, use o [Git LFS](https://git-lfs.com) para a pasta `data/`.

O `rocketlab.db`, a pasta `venv/`, `node_modules/` e os arquivos `.env` não são versionados (estão no `.gitignore`).

## Testes

Os testes do backend usam um SQLite **em memória** (fixture em `tests/conftest.py`), então não alteram o `rocketlab.db` e não dependem do seed. Cobrem CRUD, avaliações e média, busca, paginação e filtros; para os insights há um teste do formato da resposta.

```bash
cd repo-base/backend
python -m pytest
```

## Variáveis de ambiente

**Backend** (`repo-base/backend/.env`):

| Variável | Descrição | Valor padrão |
| --- | --- | --- |
| `ENVIRONMENT` | Ambiente de execução | `local` |
| `PROJECT_VERSION` | Versão exibida pela API | `2026.2` |
| `DATABASE_URL` | Conexão com o banco | `sqlite+aiosqlite:///./rocketlab.db` |
| `BACKEND_CORS_ORIGINS` | Origens liberadas no CORS | `["http://localhost:5173"]` |
| `LOG_LEVEL` | Nível de log | `INFO` |

**Frontend** (`frontend/.env`):

| Variável | Descrição | Valor padrão |
| --- | --- | --- |
| `VITE_API_URL` | URL base da API | `http://localhost:8000/api/v1` |

## Endpoints da API

| Método | Rota | Descrição |
| --- | --- | --- |
| GET | `/api/v1/movies` | Lista paginada (`page`, `page_size`, máximo 100) com busca por título (`search`), filtros (`genero`, `ano`) e ordenação (`ordem`: `titulo`, `ano`, `nota`) |
| GET | `/api/v1/movies/generos` | Lista os nomes dos gêneros |
| GET | `/api/v1/movies/insights` | Estatísticas gerais (totais, gêneros mais bem avaliados, filmes mais lucrativos) |
| POST | `/api/v1/movies` | Cadastra um filme |
| GET | `/api/v1/movies/{sk_movie_id}` | Detalhes do filme, avaliações e média |
| PATCH | `/api/v1/movies/{sk_movie_id}` | Atualização parcial: só os campos enviados mudam (`null` limpa campos opcionais) |
| DELETE | `/api/v1/movies/{sk_movie_id}` | Remove o filme e, em cascata, suas avaliações e vínculos |
| POST | `/api/v1/movies/{sk_movie_id}/reviews` | Adiciona avaliação (`nome`, `nota_estrelas` de 1 a 5, `comentario`) |
| GET | `/health` | Verificação de saúde da API |

## Rotas do frontend

| Rota | Tela |
| --- | --- |
| `/` | Catálogo com busca, filtros e paginação |
| `/insights` | Estatísticas gerais |
| `/movies/new` | Cadastro de filme |
| `/movies/:id` | Detalhes, avaliações e formulário de nova avaliação |
| `/movies/:id/edit` | Edição de filme |

## Decisões de projeto

- **Escala das notas:** a API expõe estrelas de 1 a 5. Internamente o banco guarda a nota na escala 0–10 (herdada dos CSVs), e a conversão é `estrelas × 2`.
- **Média de avaliações:** é calculada a partir da tabela `movie_reviews` (avaliações dos CSVs mais as criadas pelo sistema) e exibida no catálogo, nos detalhes e nos Insights.
- **Cadastro e edição:** telas separadas (`CreateMoviePage` e `EditMoviePage`). Na interface, todos os campos do formulário são obrigatórios; a API, por sua vez, exige apenas o título. Diretores e gêneros são informados separados por vírgula. Ao editar os diretores, o elenco já vinculado ao filme é preservado.
- **Status do filme:** os formulários de cadastro e edição oferecem `Planejado`, `Em produção` e `Lançado`.
- **Remoção:** as chaves estrangeiras usam `ON DELETE CASCADE`, então remover um filme apaga também suas avaliações, vínculos e métricas.
- **Títulos:** a API remove aspas duplicadas dos títulos, que vêm assim por causa do escaping dos CSVs originais.

## Limitações conhecidas

- Os formulários não oferecem o status `Pós-Produção`, que existe nos dados, e escrevem `Em produção` com "p" minúsculo (nos dados é `Em Produção`). Ao editar um filme com esses status, confira o campo antes de salvar.
- Os formulários limitam o título a 120 caracteres, embora a API aceite até 500.
- As telas de cadastro e edição mostram mensagens de erro genéricas, sem o detalhe devolvido pela API.

## Evoluções possíveis

- Autenticação do Administrador
- Testes automatizados do frontend
- Documentação de componentes com Storybook
- Cache de consultas
- Busca por diretor, elenco e gênero

## Solução de problemas

**O seed avisa que o banco já está populado.** O script não carrega os dados duas vezes. Para recomeçar do zero, apague `rocketlab.db`, rode `python -m alembic upgrade head` e depois `python scripts/seed.py`.

**Erro de banco inexistente ao rodar o seed.** Rode antes `python -m alembic upgrade head`, sempre de dentro de `repo-base/backend`.

**Erro `UnicodeDecodeError` ao criar ou ativar a venv no Windows.** Acontece quando o caminho da pasta ou do usuário tem acentos. Rode `$env:PYTHONUTF8 = "1"` no terminal e repita o comando.

**O frontend abre, mas a lista não carrega.** Confirme que o backend está rodando na porta 8000, que `VITE_API_URL` aponta para `http://localhost:8000/api/v1` e que `BACKEND_CORS_ORIGINS` inclui `http://localhost:5173`. Depois de alterar o `.env` do frontend, reinicie o `npm run dev`.