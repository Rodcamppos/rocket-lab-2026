# CineData Agent — Text-to-SQL sobre a camada Gold

Agente de IA que permite a pessoas **sem conhecimento de SQL** fazerem perguntas em
linguagem natural sobre o catálogo de filmes da **CineData Analytics** e receberem
respostas calculadas em tempo real sobre a camada Gold (`cinerocket.db`, SQLite).

> Atividade GenAI — Rocket Lab 2026 (Visagio).

## Como funciona

```
Pergunta ──► guardrails de entrada ──► Agente (PydanticAI + LLM gratuito do OpenRouter)
                                              │  escreve SQL (tool calling)
                                              ▼
                       guardrails de SQL ──► executar_sql ──► SQLite (somente leitura)
                                              │  linhas
                                              ▼
                         Resposta em português (tabela + critérios usados)
```

| Peça | Arquivo | O que faz |
|---|---|---|
| Persona, regras de negócio, exemplos | `src/cinedata_agent/prompts.py` | Instruções do agente |
| Schema da Gold | `src/cinedata_agent/schema.py` | Tabelas/colunas e tradução de gêneros |
| Ferramenta | `src/cinedata_agent/tools.py` | `executar_sql` (valida, executa, devolve linhas) |
| Guardrails | `src/cinedata_agent/guardrails.py` | Só `SELECT`; bloqueia escrita, múltiplas instruções e prompt injection básico |
| Banco | `src/cinedata_agent/db.py` | Conexão `mode=ro`, limite de linhas e de tempo |
| Agente | `src/cinedata_agent/agent.py` | Modelo com **fallback**, **memória de conversa** e **cache** |
| Configuração | `src/cinedata_agent/config.py` | Variáveis de ambiente / `.env` |
| CLI | `main.py` | Modo interativo ou pergunta única |
| Avaliação | `tests/eval_questions.py` | As 14 perguntas do enunciado com SQL esperado |

**Stack:** Python 3.10+, [PydanticAI](https://ai.pydantic.dev), OpenRouter (modelos `:free`), SQLite.

## Passo a passo para executar

### 1. Clonar e criar o ambiente

```bash
git clone https://github.com/Rodcamppos/rocket-lab-2026.git
cd "rocket-lab-2026/Projeto 03 - Atividade GenAI"

python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# Linux / macOS:         source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Baixar o banco de dados

Baixe o `cinerocket.db` da pasta compartilhada da atividade e coloque em `data/`:

```
data/cinerocket.db
```

> O arquivo tem ~555 MB e **não é versionado** (o GitHub recusa arquivos > 100 MB; ele está no `.gitignore`).
> Se o arquivo baixado se chamar `cinerocket (1).db`, renomeie para `cinerocket.db`.
> Para usar outro local, defina `CINEROCKET_DB_PATH` no `.env`.

### 3. Criar a chave do OpenRouter

1. Crie uma conta em <https://openrouter.ai> e gere uma chave em <https://openrouter.ai/keys> (começa com `sk-or-v1-`).
2. Copie `.env.example` para `.env` e preencha:

```bash
cp .env.example .env        # Windows: copy .env.example .env
```

```
OPENROUTER_API_KEY=sk-or-v1-SUA_CHAVE_AQUI
```

### 4. Validar o ambiente (não gasta cota)

```bash
python -m tests.eval_questions
```

Roda o SQL esperado das 14 perguntas direto no banco. Todas devem aparecer como `[OK  ]`.

### 5. Usar o agente

```bash
python main.py                                   # modo interativo, com memória de conversa
python main.py -q "Top 10 filmes com maior receita em R$"
python main.py -q "Quantidade de filmes por gênero" --show-sql
```

No modo interativo: `sair` encerra e `/limpar` zera a memória da conversa.

Exemplos de perguntas:

- Top 10 filmes com maior receita em R$
- Lucro médio por gênero, considerando apenas filmes com receita informada
- Os 5 filmes mais populares
- Diretores com maior nota média (mínimo de 5 filmes)
- Dupla ator–diretor que mais trabalhou junta
- Produtora com maior lucro total
- Filmes em que a nota média dos usuários mais diverge da nota IMDb
- E agora uma pergunta de acompanhamento: *"E desses, qual é o de terror?"* (usa a memória)

## Avaliação

```bash
python -m tests.eval_questions                    # só SQL esperado, sem LLM (grátis)
python -m tests.eval_questions --llm --only 1,4   # pergunta ao agente e compara com o esperado
python -m tests.eval_questions --llm --all        # as 14 (≈ 30–40 requisições!)
```

A comparação é heurística (empates e escolhas de métrica podem gerar falso `FAIL`);
confira os casos divergentes com `python main.py -q "..." --show-sql`.

## Decisões e premissas de negócio

Os dados têm particularidades que o prompt trata explicitamente:

| Tema | Decisão | Motivo |
|---|---|---|
| Receita / faturamento / bilheteria | Sinônimos → `receita_brl` (R$); `*_usd` só se pedirem dólares | Enunciado |
| Dados financeiros | `receita` é NULL em ~96% dos filmes (3.373 com receita; 7.926 com orçamento) | NULL = não informado (não há zeros) |
| Lucro | Só considerado com `receita_brl IS NOT NULL` | `lucro_*` é NOT NULL e vira `-orçamento` (ou 0) quando falta receita |
| Margem de lucro | `lucro / receita × 100`, só com receita **e** orçamento informados (1.630 filmes) | Enunciado |
| Margem média por gênero | Ranking pela média das margens por filme, **mostrando também** a margem agregada | Há outliers extremos (até −5.409.086%) que distorcem a média simples |
| Notas | `nota_tmdb = 0` e `nota_imdb` NULL/0 tratados como “sem nota” | 36 mil filmes têm `nota_tmdb = 0` |
| “Nota média” sem especificar | IMDb (declarado na resposta) | Fonte com menos zeros |
| “Últimos 5 anos” | `data_lancamento >= hoje − 5 anos` e `status_filme = 'Lançado'` | A base cobre 2016–2024 |
| Gêneros | Banco em inglês; o agente traduz o pedido e responde em português | `Horror` ↔ Terror etc. |
| Pessoas | Sempre filtra `tipo_pessoa` (Ator/Diretor/Roteirista) | Todos ficam em `dim_people` |

## Guardrails, fallback, memória e cache

- **Guardrails de SQL:** apenas `SELECT`/`WITH`; uma instrução; bloqueia `INSERT/UPDATE/DELETE/DROP/PRAGMA/ATTACH...`. Camadas extras: conexão SQLite **somente leitura**, limite de `MAX_ROWS` linhas e timeout por consulta.
- **Guardrails de entrada:** tamanho máximo e padrões básicos de prompt injection. Perguntas fora do escopo são recusadas pelo próprio prompt.
- **Fallback entre modelos:** `openrouter/free` → `nvidia/nemotron-3.5-lightning:free` → `z-ai/glm-5.2:free` → `google/gemma-4-26b-a4b-it:free` (configurável em `OPENROUTER_MODELS`).
- **Memória de conversa:** guarda as últimas `HISTORY_TURNS` (5) perguntas/respostas no modo interativo.
- **Cache:** respostas a perguntas sem contexto ficam em `data/answer_cache.json`; repetir a pergunta custa **0 requisições**. Use `--no-cache` para ignorar.

## Cota do OpenRouter (50 requisições/dia)

- Cada pergunta usa tipicamente **2 requisições** (escrever o SQL + redigir a resposta); o teto é `REQUEST_LIMIT_PER_QUESTION` (6).
- **Requisições que falham também contam** — e cada modelo tentado no fallback conta. Não fique repetindo a mesma pergunta após um `429`.
- O contador zera à meia-noite UTC (21h em Brasília). Confira em <https://openrouter.ai/activity>.
- Para economizar: valide com `python -m tests.eval_questions` (sem LLM), use `--only` na avaliação e aproveite o cache.

## Estrutura

```
.
├── data/                    # coloque aqui o cinerocket.db (não versionado)
├── src/cinedata_agent/
│   ├── agent.py  config.py  db.py  guardrails.py
│   └── prompts.py  schema.py  tools.py
├── tests/eval_questions.py
├── main.py
├── requirements.txt
└── .env.example
```

## Solução de problemas

| Sintoma | O que fazer |
|---|---|
| `OPENROUTER_API_KEY não definida` | Crie o `.env` a partir do `.env.example` e preencha a chave |
| `Banco de dados não encontrado` | Coloque `cinerocket.db` em `data/` (ou ajuste `CINEROCKET_DB_PATH`) |
| `401` | Chave inválida: confirme que começa com `sk-or-v1-` |
| `429` com `upstream_provider` | Modelo gratuito lotado: o fallback tenta o próximo; se todos falharem, aguarde |
| `429` sem provider | Cota diária esgotada: aguarde o reset (21h BRT) |
| Consulta excedeu o tempo limite | Aumente `QUERY_TIMEOUT_S` no `.env` |

## Possíveis evoluções

Busca semântica sobre as sinopses (agente híbrido), gráficos/interface web (FastAPI ou Streamlit), conexão com a camada Gold no Databricks.
