# CineData Agent — Text-to-SQL sobre a camada Gold

Agente de IA que permite a pessoas **sem conhecimento de SQL** fazerem perguntas em português
sobre o catálogo de filmes da **CineData Analytics** e receberem respostas calculadas em tempo
real sobre a camada Gold (`cinerocket.db`, SQLite, 10 tabelas do modelo dimensional).

> Atividade GenAI — Rocket Lab 2026 (Visagio).

**O que o projeto entrega**

- Agente **Text-to-SQL** somente leitura, com *tool calling* (PydanticAI + modelos gratuitos do OpenRouter).
- **Guardrails** em camadas (validação do SQL, conexão somente leitura, limite de linhas e de tempo).
- **Fallback** entre modelos gratuitos, **memória de conversa** e **cache de respostas**.
- **Avaliação** com as 14 perguntas do enunciado e o SQL esperado de cada uma.
- **CLI** e **interface web** (Streamlit) com tabela de dados e gráfico de barras automático.

---

## Sumário

1. [Como funciona](#como-funciona)
2. [Passo a passo para executar](#passo-a-passo-para-executar)
3. [Interface web (opcional)](#interface-web-opcional)
4. [Exemplos de perguntas](#exemplos-de-perguntas)
5. [Avaliação](#avaliação)
6. [Decisões e premissas de negócio](#decisões-e-premissas-de-negócio)
7. [Guardrails, fallback, memória e cache](#guardrails-fallback-memória-e-cache)
8. [Configuração](#configuração)
9. [Cota do OpenRouter](#cota-do-openrouter-50-requisições-por-dia)
10. [Estrutura do projeto](#estrutura-do-projeto)
11. [Solução de problemas](#solução-de-problemas)
12. [Resultados da avaliação](#resultados-da-avaliação)
13. [Observações sobre os dados](#observações-sobre-os-dados-camada-gold)
14. [Limitações e próximos passos](#limitações-e-próximos-passos)

---

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

É um **agente único** com uma ferramenta, `executar_sql`. O schema da Gold, as regras de negócio
e alguns exemplos de SQL vão **uma vez** no prompt de sistema (em vez de uma ferramenta de consulta
de schema), o que reduz o número de chamadas ao modelo: uma pergunta custa em geral **2 requisições**
(escrever o SQL e redigir a resposta).

| Peça | Arquivo | O que faz |
|---|---|---|
| Persona, regras de negócio, exemplos | `src/cinedata_agent/prompts.py` | Instruções do agente |
| Schema da Gold | `src/cinedata_agent/schema.py` | Tabelas/colunas e tradução de gêneros |
| Ferramenta | `src/cinedata_agent/tools.py` | `executar_sql`: valida, executa e devolve as linhas |
| Guardrails | `src/cinedata_agent/guardrails.py` | Só `SELECT`; bloqueia escrita, múltiplas instruções e *prompt injection* básico |
| Banco | `src/cinedata_agent/db.py` | Conexão `mode=ro`, limite de linhas e de tempo |
| Agente | `src/cinedata_agent/agent.py` | Modelo com **fallback**, **memória** e **cache** |
| Gráficos | `src/cinedata_agent/viz.py` | Decide quando e como desenhar o gráfico de barras |
| Configuração | `src/cinedata_agent/config.py` | Variáveis de ambiente / `.env` |
| CLI | `main.py` | Modo interativo ou pergunta única |
| Interface web | `app.py` | Chat em Streamlit |
| Avaliação | `tests/eval_questions.py` | As 14 perguntas do enunciado com SQL esperado |

**Stack:** Python 3.10+, [PydanticAI](https://ai.pydantic.dev) (2.x), OpenRouter (modelos `:free`),
SQLite, Streamlit (opcional).

---

## Passo a passo para executar

### Pré-requisitos

- Python 3.10 ou superior e Git.
- Uma conta gratuita no [OpenRouter](https://openrouter.ai) (não é necessário cartão de crédito).
- O arquivo `cinerocket.db`, disponível na pasta compartilhada da atividade.

### 1. Clonar e criar o ambiente

```bash
git clone https://github.com/Rodcamppos/rocket-lab-2026.git
cd "rocket-lab-2026/Projeto 03 - Atividade GenAI"

python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# Linux / macOS:         source .venv/bin/activate

pip install -r requirements.txt
```

> No PowerShell, se a ativação for bloqueada, rode
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` e tente de novo.

### 2. Colocar o banco de dados

Baixe o `cinerocket.db` da pasta compartilhada da atividade e coloque em `data/`:

```
data/cinerocket.db
```

> O arquivo tem cerca de 555 MB e **não é versionado** (o GitHub recusa arquivos acima de 100 MB;
> ele está no `.gitignore`). Se o arquivo baixado se chamar `cinerocket (1).db`, renomeie para
> `cinerocket.db`. Para usar outro local, defina `CINEROCKET_DB_PATH` no `.env`.

### 3. Criar a chave do OpenRouter

1. Entre em <https://openrouter.ai> e crie uma conta (Google, GitHub ou e-mail).
2. Abra <https://openrouter.ai/keys>, clique em **Create Key** e copie a chave (`sk-or-v1-...`).
   Ela só é exibida uma vez.
3. Copie `.env.example` para `.env` e preencha a chave:

```bash
cp .env.example .env        # Windows: copy .env.example .env
```

```
OPENROUTER_API_KEY=sk-or-v1-SUA_CHAVE_AQUI
```

> **Sem custo:** o projeto usa apenas modelos com sufixo `:free` (ou `openrouter/free`), que não são
> cobrados. Não adicione créditos à conta. Se alterar `OPENROUTER_MODELS`, use somente modelos `:free`.
> O arquivo `.env` está no `.gitignore`: nunca o envie ao GitHub.

### 4. Validar o ambiente (não usa o LLM)

```bash
python -m tests.eval_questions
```

Executa o SQL esperado das 14 perguntas direto no banco. Todas devem aparecer como `[OK  ]`
e a última linha deve ser `14/14 consultas executaram com sucesso`. As consultas de elenco
(#7 e #9) podem levar de 25 a 35 segundos, o que é normal.

### 5. Usar o agente

```bash
python main.py                                          # modo interativo, com memória
python main.py -q "Top 10 filmes com maior receita em R$"
python main.py -q "Quantidade de filmes por gênero" --show-sql
python main.py -q "Os 5 filmes mais populares" --no-cache
```

| Opção | Efeito |
|---|---|
| `-q "pergunta"` | Faz uma única pergunta e encerra |
| `--show-sql` | Mostra o SQL executado (inclusive as tentativas com erro) |
| `--no-cache` | Ignora o cache de respostas |

No modo interativo, `sair` encerra e `/limpar` zera a memória da conversa.

---

## Interface web (opcional)

Além da CLI, há uma interface de chat em Streamlit com memória de conversa, perguntas de exemplo
por categoria, SQL executado, tabela de dados e **gráfico de barras automático** quando o
resultado é um ranking ou uma série.

```bash
pip install -r requirements-ui.txt
streamlit run app.py
```

Abre em <http://localhost:8501>. Usa o mesmo agente da CLI (`ask()` em `agent.py`), então guardrails,
fallback e cache valem igualmente. Na barra lateral é possível ocultar o SQL, desligar o cache e
iniciar uma nova conversa.

---

## Exemplos de perguntas

- Top 10 filmes com maior receita em R$
- Lucro médio por gênero, considerando apenas filmes com receita informada
- Filmes com maior margem de lucro, entre os que possuem receita e orçamento informados
- Os 5 filmes mais populares
- Filmes com maior divergência entre a nota TMDB e a nota IMDb
- Nota média IMDb por ano de lançamento
- Ator com mais participações em filmes lançados nos últimos 5 anos
- Diretores com maior nota média (mínimo de 5 filmes)
- Dupla ator–diretor que mais trabalhou junta
- Quantidade de filmes por gênero
- Produtora com maior lucro total
- Gênero com maior margem de lucro média
- Filmes mais avaliados pelos usuários
- Filmes em que a nota média dos usuários mais diverge da nota IMDb
- Perguntas de acompanhamento (usam a memória): *"e desses, qual é o mais antigo?"*

---

## Avaliação

```bash
python -m tests.eval_questions                    # só o SQL esperado, sem LLM (grátis)
python -m tests.eval_questions --llm --only 1,4   # pergunta ao agente e compara com o esperado
python -m tests.eval_questions --llm --all        # as 14 (≈ 30–40 requisições!)
python -m tests.eval_questions --llm --all --no-cache   # ignora o cache (regressão completa)
```

Cada caso tem a pergunta, o SQL esperado e um modo de comparação:

| Modo | Critério |
|---|---|
| `ordered` | As chaves do topo do ranking coincidem, na ordem |
| `set` | Todas as categorias esperadas aparecem no resultado do agente |
| `value` | A métrica da primeira linha coincide (rankings com empates) |

A comparação é **heurística**: empates e escolhas de métrica podem gerar falso `FAIL`. Em caso de
falha, o teste imprime o SQL escrito pelo agente. Confira com
`python main.py -q "..." --show-sql`.

---

## Decisões e premissas de negócio

Os dados têm particularidades que o prompt trata explicitamente:

| Tema | Decisão | Motivo |
|---|---|---|
| Receita / faturamento / bilheteria | Sinônimos → `receita_brl` (R$); `*_usd` só se pedirem dólares | Enunciado |
| Dados financeiros | `receita` é NULL em ~96% dos filmes (3.373 com receita; 7.926 com orçamento) | NULL = não informado (não há zeros) |
| Lucro | Só considerado com `receita_brl IS NOT NULL` | `lucro_*` é NOT NULL e vira `-orçamento` (ou 0) quando falta receita |
| Margem de lucro | `lucro / receita × 100`, só com receita **e** orçamento informados (1.630 filmes) | Enunciado |
| Margem média por gênero | Ranking pela média das margens por filme, **mostrando também** a margem agregada | Há outliers extremos (até −5.409.086%) que distorcem a média simples |
| Notas | `nota_tmdb = 0` e `nota_imdb` NULL/0 tratados como "sem nota" | 36 mil filmes têm `nota_tmdb = 0` |
| "Nota média" sem especificar | IMDb (declarado na resposta) | Fonte com menos zeros |
| "Últimos 5 anos" | `data_lancamento >= hoje − 5 anos` e `status_filme = 'Lançado'` | A base cobre 2016–2024 |
| Gêneros | Banco em inglês: o SQL usa os nomes em inglês e a resposta apresenta em português | `Horror` ↔ Terror etc. |
| Pessoas | Sempre filtra `tipo_pessoa` (Ator, Diretor ou Roteirista) | Todos ficam em `dim_people` |
| Avaliações de usuários | `dim_reviews` ligada por `sk_movie_id`; em `movie_reviews`, `sk_movie_review_id` **não** liga a filmes | Evita *joins* que retornam vazio |

---

## Guardrails, fallback, memória e cache

- **Guardrails de SQL** (`guardrails.py`): apenas `SELECT`/`WITH`; uma única instrução; bloqueia
  `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `PRAGMA`, `ATTACH`, `LOAD_EXTENSION` e
  similares. Comentários e strings são ignorados na análise para evitar falsos positivos.
- **Camadas extras** (`db.py`): conexão SQLite **somente leitura** (`mode=ro` + `query_only`), limite de
  `MAX_ROWS` linhas por consulta e *timeout* por consulta.
- **Guardrails de entrada:** tamanho máximo da pergunta e padrões básicos de *prompt injection*.
  Perguntas fora do escopo são recusadas pelo próprio prompt, e perguntas que dependem de contexto
  inexistente ("desses...") pedem esclarecimento.
- **Reparo de SQL:** erros de SQL e bloqueios voltam ao modelo como mensagem, para ele corrigir a consulta
  (limite de tentativas em `TOOL_RETRIES`).
- **Fallback entre modelos:** `openrouter/free` → `nvidia/nemotron-3.5-lightning:free` →
  `z-ai/glm-5.2:free` → `google/gemma-4-26b-a4b-it:free` (configurável em `OPENROUTER_MODELS`).
  O fallback cobre erros de API (como `429`) e respostas inválidas do provedor
  (`finish_reason = error`).
- **Memória de conversa:** guarda as últimas `HISTORY_TURNS` (5) perguntas e respostas, apenas em texto
  (sem chamadas de ferramenta antigas, para economizar tokens).
- **Cache** (`data/answer_cache.json`): respostas a perguntas **sem contexto** ficam em disco;
  repetir a pergunta custa **0 requisições** (o SQL salvo é reexecutado no banco para recuperar as
  linhas). Resultados vazios não são guardados no cache. Use `--no-cache` para ignorá-lo.

---

## Configuração

Todas as variáveis são opcionais, exceto `OPENROUTER_API_KEY`. Defina no `.env`:

| Variável | Padrão | Descrição |
|---|---|---|
| `OPENROUTER_API_KEY` | — | Chave do OpenRouter (obrigatória) |
| `OPENROUTER_MODELS` | 4 modelos `:free` | Modelos em ordem de tentativa (fallback), separados por vírgula |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | Endpoint compatível com a API da OpenAI |
| `CINEROCKET_DB_PATH` | `data/cinerocket.db` | Caminho do banco |
| `MAX_ROWS` | `50` | Máximo de linhas devolvidas ao modelo por consulta |
| `QUERY_TIMEOUT_S` | `120` | Tempo limite por consulta SQL |
| `REQUEST_LIMIT_PER_QUESTION` | `6` | Teto de chamadas ao modelo por pergunta |
| `TOOL_RETRIES` | `2` | Tentativas de correção de SQL com erro |
| `HISTORY_TURNS` | `5` | Turnos mantidos na memória de conversa |
| `MAX_QUESTION_CHARS` | `500` | Tamanho máximo da pergunta |
| `CACHE_ENABLED` | `true` | Liga/desliga o cache de respostas |

---

## Cota do OpenRouter (50 requisições por dia)

- Cada pergunta usa tipicamente **2 requisições**; o teto é `REQUEST_LIMIT_PER_QUESTION` (6).
- **Requisições que falham também contam** — e cada modelo tentado no fallback conta. Não repita a
  mesma pergunta em sequência depois de um `429`.
- O contador zera à meia-noite UTC (**21h em Brasília**). Confira em <https://openrouter.ai/activity>
  ou consulte `GET https://openrouter.ai/api/v1/key` (campo `free_model_daily_requests`).
- Para economizar: valide com `python -m tests.eval_questions` (sem LLM), use `--only` na avaliação e
  aproveite o cache.

---

## Estrutura do projeto

```
.
├── app.py                       # interface web (Streamlit)
├── main.py                      # CLI
├── requirements.txt             # dependências do agente
├── requirements-ui.txt          # + Streamlit (opcional)
├── .env.example                 # modelo do .env
├── .gitignore
├── data/
│   └── .gitkeep                 # coloque aqui o cinerocket.db (não versionado)
├── src/cinedata_agent/
│   ├── agent.py                 # agente, fallback, memória e cache
│   ├── config.py                # configurações
│   ├── db.py                    # SQLite somente leitura
│   ├── guardrails.py            # validação de SQL e de perguntas
│   ├── prompts.py               # persona, regras e exemplos
│   ├── schema.py                # schema da Gold
│   ├── tools.py                 # ferramenta executar_sql
│   └── viz.py                   # heurística de gráficos
└── tests/
    └── eval_questions.py        # as 14 perguntas do enunciado
```

---

## Solução de problemas

| Sintoma | O que fazer |
|---|---|
| `OPENROUTER_API_KEY não definida` | Crie o `.env` a partir do `.env.example` e preencha a chave |
| `O .env ainda tem a chave de exemplo` | Gere sua chave em <https://openrouter.ai/keys> e substitua o valor |
| `Banco de dados não encontrado` | Coloque `cinerocket.db` em `data/` (ou ajuste `CINEROCKET_DB_PATH`) |
| `401` | Chave inválida: confirme que começa com `sk-or-v1-` |
| `402` ou "key limit exceeded" | A chave tem limite de gasto zerado: crie outra sem limite (modelos `:free` não cobram) |
| `429` com `upstream_provider` | Modelo gratuito lotado: o fallback tenta o próximo; se todos falharem, aguarde |
| `429` sem provider | Cota diária esgotada: aguarde o reset (21h em Brasília) |
| `finish_reason error` | Falha temporária do modelo gratuito: tente novamente em instantes |
| Consulta excedeu o tempo limite | Aumente `QUERY_TIMEOUT_S` no `.env` |
| `ModuleNotFoundError: streamlit` | Rode `pip install -r requirements-ui.txt` |
| Ativação do `.venv` bloqueada (PowerShell) | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |

---

## Resultados da avaliação

As 14 perguntas do enunciado foram executadas com o agente (modelos gratuitos do OpenRouter) e
comparadas com o SQL esperado de cada uma (`tests/eval_questions.py`).

| # | Categoria | Pergunta | Resultado |
|---|---|---|---|
| 1 | Bilheteria e Finanças | Top 10 filmes com maior receita em R$ | PASS |
| 2 | Bilheteria e Finanças | Lucro médio por gênero (apenas filmes com receita informada) | PASS |
| 3 | Bilheteria e Finanças | Filmes com maior margem de lucro (receita e orçamento informados) | PASS |
| 4 | Popularidade e Engajamento | Os 5 filmes mais populares | PASS |
| 5 | Popularidade e Engajamento | Maior divergência entre nota TMDB e nota IMDb | PASS |
| 6 | Popularidade e Engajamento | Nota média IMDb por ano de lançamento | PASS |
| 7 | Elenco e Equipe | Ator com mais participações nos últimos 5 anos | PASS |
| 8 | Elenco e Equipe | Diretores com maior nota média (mínimo de 5 filmes) | PASS |
| 9 | Elenco e Equipe | Dupla ator–diretor que mais trabalhou junta | PASS |
| 10 | Gêneros e Produtoras | Quantidade de filmes por gênero | PASS |
| 11 | Gêneros e Produtoras | Produtora com maior lucro total | PASS |
| 12 | Gêneros e Produtoras | Gênero com maior margem de lucro média | PASS |
| 13 | Avaliações dos Usuários | Filmes mais avaliados pelos usuários | PASS |
| 14 | Avaliações dos Usuários | Filmes em que a nota média dos usuários mais diverge da IMDb | PASS |

**Como ler estes resultados**

- A comparação é **heurística** (veja [Avaliação](#avaliação)) e não substitui a leitura da resposta.
- Cada pergunta consome tipicamente **2 requisições** e até 4 quando há nova tentativa ou fallback.
- As perguntas foram avaliadas em rodadas separadas durante o desenvolvimento, com ajustes de prompt
  e de schema entre elas (por exemplo: gêneros sempre em inglês dentro do SQL e o esclarecimento de que
  `movie_reviews.sk_movie_review_id` não liga a filmes). O resultado pode variar entre execuções, pois
  os modelos gratuitos não são determinísticos.

---

## Observações sobre os dados (camada Gold)

Pontos encontrados ao explorar o `cinerocket.db` e como o agente os trata:

| Observação | Tratamento |
|---|---|
| Receita informada em 3.373 de 95.645 filmes (≈3,5%); orçamento em 7.926; ambos em 1.630 | `receita IS NOT NULL` em rankings e lucro; margem só com receita **e** orçamento |
| `lucro_*` é NOT NULL, mas vale `-orçamento` (ou 0) sem receita e `receita` sem orçamento | Lucro só considerado com receita informada |
| `nota_tmdb = 0` em 36.185 filmes e `nota_imdb` NULL em 12.674 | Tratados como "sem nota" |
| Filmes com status `Planejado` (anos 2027 e 2029) com nota IMDb | Anomalia: o gabarito da pergunta #6 considera só `Lançado` |
| `popularidade` com valores inteiros suspeitos no topo (ex.: 2020.0, 2019.0, 2018.0, 1969.0) | Possível artefato de carga; o agente reporta o que está na base |
| Margem por filme com outliers extremos (até −5.409.086%) | Média por gênero acompanhada da margem agregada (ex.: *War* −534,88% pela média vs. 66,89% agregada) |
| `idioma_original` sempre NULL | Coluna não utilizada |
| Nomes que parecem erro de carga em `dim_people` (países e idiomas como pessoas) | Não tratado; sinalizado como limitação |
| Base cobre lançamentos de 2016 a 2029, quase tudo até 2024 | "Últimos N anos" usa a data atual e informa o período efetivamente considerado |

---

## Limitações e próximos passos

- Modelos gratuitos variam em qualidade e disponibilidade; o fallback mitiga, mas não elimina falhas.
- A cota gratuita (50 requisições por dia) limita a quantidade de testes e a extensão da avaliação.
- A avaliação automática é heurística e depende de um gabarito escolhido pelo projeto (por exemplo, a
  definição de "margem média" e o tratamento de empates).
- Consultas sobre elenco levam de 25 a 35 segundos por varrerem tabelas grandes (`bridge_movie_person` tem
  cerca de 745 mil linhas); índices na camada Gold reduziriam esse tempo.
- Não foram implementados: busca semântica sobre as sinopses (agente híbrido) e conexão com a camada
  Gold no Databricks.