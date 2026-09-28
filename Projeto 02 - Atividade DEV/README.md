# Sistema de Avaliação de Filmes

Aplicação full stack para catalogar filmes, consultar detalhes e registrar avaliações, inspirada em plataformas como o Letterboxd. Desenvolvida para a **Atividade DEV do Rocket Lab 2026.2 (Visagio)**. O usuário é o Administrador do catálogo.

## Funcionalidades

- Catálogo paginado (20 filmes por página) com barra de busca por título
- Detalhes do filme: sinopse, duração, status, gêneros, diretores, elenco e produtoras
- Histórico de avaliações (resenhas e notas) e média geral de cada filme
- Adicionar avaliação a um filme (nota de 1 a 5 estrelas + resenha em texto)
- Cadastrar, editar e remover filmes

## Stack

| Camada | Tecnologias |
| --- | --- |
| Frontend | Vite, React, TypeScript, axios, react-router-dom |
| Backend | FastAPI, SQLAlchemy 2 (async), Alembic |
| Banco de dados | SQLite |

## Estrutura do projeto

```
Projeto 02 - Atividade DEV/
├── frontend/                  # Vite + React + TypeScript
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

Use dois terminais: um para o backend e outro para o frontend. Os comandos abaixo são para PowerShell (Windows); logo abaixo de cada bloco há a versão para Linux/macOS.

### 1. Backend

A partir da pasta `Projeto 02 - Atividade DEV`:

```powershell
cd repo-base\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
python -m alembic upgrade head
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

Os 10 CSVs de carga inicial já estão em `repo-base/backend/data/` (o script os encontra mesmo dentro de subpastas). Popule o banco e suba a API:

```powershell
python scripts/seed.py
python -m uvicorn app.main:app --reload
```

- API: http://localhost:8000
- Documentação interativa (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/health

### 2. Frontend

Em outro terminal, a partir da pasta `Projeto 02 - Atividade DEV`:

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Acesse http://localhost:5173.

**Linux/macOS:** `cd frontend && npm install && cp .env.example .env && npm run dev`.

## Testes

Os testes do backend usam um SQLite **em memória** (fixture em `tests/conftest.py`), então não alteram o `rocketlab.db` nem precisam do seed. Cobrem CRUD, avaliações e média, busca, paginação, filtros e insights.

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
| GET | `/api/v1/movies` | Lista paginada (`page`, `page_size`) com busca por título (`search`), filtros (`genero`, `ano`) e ordenação (`ordem`: `titulo`, `ano`, `nota`) |
| GET | `/api/v1/movies/generos` | Lista os nomes dos gêneros |
| GET | `/api/v1/movies/insights` | Estatísticas gerais (totais, gêneros mais bem avaliados, filmes mais lucrativos) |
| POST | `/api/v1/movies` | Cadastra um filme |
| GET | `/api/v1/movies/{sk_movie_id}` | Detalhes do filme, avaliações e média |
| PATCH | `/api/v1/movies/{sk_movie_id}` | Atualização parcial: só os campos enviados mudam (`null` limpa campos opcionais) |
| DELETE | `/api/v1/movies/{sk_movie_id}` | Remove um filme |
| POST | `/api/v1/movies/{sk_movie_id}/reviews` | Adiciona avaliação (`nome`, `nota_estrelas` de 1 a 5, `comentario`) |
| GET | `/health` | Verificação de saúde da API |

## Rotas do frontend

| Rota | Tela |
| --- | --- |
| `/` | Catálogo com busca e paginação |
| `/insights` | Estatísticas gerais |
| `/movies/new` | Cadastro de filme |
| `/movies/:id` | Detalhes, avaliações e formulário de nova avaliação |
| `/movies/:id/edit` | Edição de filme |

## Observação sobre os CSVs

Os CSVs de carga somam mais de 400 MB, e o `bridge_movie_person.csv` tem ~97 MB (o GitHub bloqueia arquivos acima de 100 MB e avisa acima de 50 MB). Se o push falhar, use [Git LFS](https://git-lfs.com) para a pasta `repo-base/backend/data/` ou mantenha-a fora do repositório e documente onde baixar os arquivos. O `.gitignore` da raiz já exclui `venv/`, `node_modules/`, `.env` e `*.db`.

## Solução de problemas

**O seed avisa que o banco já está populado.** O script não carrega os dados duas vezes. Para recomeçar do zero, apague `rocketlab.db`, rode `python -m alembic upgrade head` e depois `python scripts/seed.py`.

**Erro `UnicodeDecodeError` ao criar ou ativar a venv no Windows.** Acontece quando o caminho da pasta ou do usuário tem acentos. Rode `$env:PYTHONUTF8 = "1"` no terminal e repita o comando.

**O frontend abre, mas a lista não carrega.** Confirme que o backend está rodando na porta 8000, que `VITE_API_URL` aponta para `http://localhost:8000/api/v1` e que `BACKEND_CORS_ORIGINS` inclui `http://localhost:5173`. Depois de alterar o `.env` do frontend, reinicie o `npm run dev`.

**Erro de banco inexistente ao rodar o seed.** Rode antes `python -m alembic upgrade head`, sempre de dentro de `repo-base/backend`.