# CineData Analytics

Projeto da atividade **Visagio | Rocket Lab 2026.2** — Engenharia de Dados.

Pipeline de dados end-to-end no **Databricks (PySpark | SQL)**, implementando a Arquitetura Medalhão (**Bronze, Silver e Gold**) a partir de uma base de filmes (TMDB/IMDb) intencionalmente suja e fragmentada, com modelagem dimensional (Star Schema) e uma tabela de contexto para alimentar um assistente de IA (RAG).

## Contexto

A CineData Analytics é uma empresa fictícia de inteligência de mercado do setor audiovisual. Este projeto estrutura um catálogo de filmes bruto (5 arquivos CSV) em um Data Lakehouse, entregando:

- Data Marts analíticos para o time de BI
- Modelagem dimensional (Star Schema)
- Tabela de contexto para o assistente de IA (RAG) do time de Inteligência Artificial

## Arquitetura

```
Landing (5 CSVs + API BCB)
        │
        ▼
   Bronze (ingestão crua, Delta, append)
        │
        ▼
   Silver (limpeza, tipagem, tradução, deduplicação)
        │
        ▼
    Gold (Star Schema + tabela de contexto IA)
```

## Notebooks

| Notebook | Descrição |
|---|---|
| `notebooks/Landing_to_Bronze.ipynb` | Ingestão dos 5 CSVs como tabelas Delta na camada Bronze, com `ingestion_datetime`. Inclui ingestão da cotação do dólar via API do Banco Central (PTAX). |
| `notebooks/Bronze_to_Silver.ipynb` | Limpeza, tipagem, tradução, deduplicação e tratamento de inconsistências (column shift, formatos de data multi-padrão, separadores inconsistentes, forward fill). Gera as 7 tabelas Silver. |
| `notebooks/Silver_to_Gold.ipynb` | Modelagem dimensional (Star Schema: 1 fato, 5 dimensões, 3 bridge tables) e a tabela de contexto `gold_genai_movies_context` para o assistente de IA. |
| `notebooks/Gold_Analytics.ipynb` | Respostas às 6 perguntas de negócio do desafio de Analytics. |

## Camada Bronze

5 tabelas geradas a partir dos CSVs originais (`bronze.tb_movies_info`, `tb_movies_financials`, `tb_movies_metrics`, `tb_credits_and_tags`, `tb_movies_reviews`), mais `bronze.tb_cotacao_dolar` (API do Banco Central — PTAX).

**Nota sobre a API do BCB:** o Databricks Free Edition restringe o acesso a domínios externos por padrão. A chamada `requests.get()` está implementada no notebook com fallback: quando a API não está acessível, o pipeline lê um JSON previamente obtido (mesma API, mesma lógica) e já disponibilizado no Volume, mantendo a lógica de ingestão via API documentada e funcional.

## Camada Silver

7 tabelas com regras de limpeza aplicadas conforme o escopo: normalização e tradução de status, tratamento de datas multi-formato, deduplicação por `id_filme` (mantendo o registro mais recente por `ingestion_datetime`), higienização de valores monetários (símbolos de moeda, abreviações, textos de ausência), tratamento de column shift em métricas e colunas categóricas (gêneros, elenco, produtoras), e forward fill na série de cotação do dólar.

## Camada Gold

**Star Schema:**
- `gold.fact_movies_performance` — grão de 1 linha por filme lançado
- `gold.dim_movies`, `dim_genres`, `dim_people`, `dim_companies`, `dim_reviews`
- `gold.bridge_movie_genre`, `bridge_movie_person`, `bridge_movie_company`

**Tabela de contexto para IA:**
- `gold.gold_genai_movies_context` — documento consolidado por filme (frase corrida), com tratamento de nulos via `coalesce` em cada campo antes da concatenação final, evitando que um único campo ausente descarte o documento inteiro.

## Orquestração

Job **CineData_Pipeline** no Databricks Workflows, com 3 tasks (`to_Bronze` → `to_Silver` → `to_Gold`), dependências explícitas entre elas e agendamento diário configurado, simulando uma rotina de atualização em produção.

- `job.yaml`: exportação da definição do Job
- `evidencias/`: print da execução de sucesso do Job, mostrando as dependências entre as tarefas

## Desafio de Analytics

Respostas às 6 perguntas de negócio (notebook `Gold_Analytics.ipynb`):

1. Receita total (R$) de todos os filmes da base
2. Top 5 filmes por popularidade
3. Quantidade de filmes por gênero
4. Top 10 filmes por receita, com posição via `RANK()`
5. Ator com mais participações em filmes lançados nos últimos 2 anos
6. Produtora com maior lucro nos últimos 5 anos

## Tecnologias

- Databricks (Free Edition, Unity Catalog)
- PySpark / Spark SQL
- Delta Lake
- Databricks Workflows (Jobs)
- API do Banco Central (PTAX)

## Estrutura do repositório

```
Projeto 01/
├── README.md
├── job.yaml
├── notebooks/
│   ├── Landing_to_Bronze.ipynb
│   ├── Bronze_to_Silver.ipynb
│   ├── Silver_to_Gold.ipynb
│   └── Gold_Analytics.ipynb
└── evidencias/
    └── job_execucao_sucesso.png
```

---

Desenvolvido por Rodrigo Campos — Rocket Lab 2026.2 (Visagio Recife).
