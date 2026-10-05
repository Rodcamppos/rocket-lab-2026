"""Execute com:  streamlit run app.py
Requer:       pip install -r requirements-ui.txt
"""

from __future__ import annotations
import os
import pandas as pd
import streamlit as st

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")  # esconde o banner do PydanticAI

from src.cinedata_agent.agent import AgentAnswer, AgentError, ask  # noqa: E402
from src.cinedata_agent.config import ConfigError  # noqa: E402
from src.cinedata_agent.db import QueryResult  # noqa: E402
from src.cinedata_agent.guardrails import GuardrailError  # noqa: E402
from src.cinedata_agent.viz import chart_spec  # noqa: E402

EXEMPLOS: dict[str, list[str]] = {
    "Bilheteria e Finanças": [
        "Top 10 filmes com maior receita em R$",
        "Lucro médio por gênero, considerando apenas filmes com receita informada",
        "Filmes com maior margem de lucro, entre os que possuem receita e orçamento informados",
    ],
    "Popularidade e Engajamento": [
        "Os 5 filmes mais populares",
        "Filmes com maior divergência entre a nota TMDB e a nota IMDb",
        "Nota média IMDb por ano de lançamento",
    ],
    "Elenco e Equipe": [
        "Ator com mais participações em filmes lançados nos últimos 5 anos",
        "Diretores com maior nota média (mínimo de 5 filmes)",
        "Dupla ator–diretor que mais trabalhou junta",
    ],
    "Gêneros e Produtoras": [
        "Quantidade de filmes por gênero",
        "Produtora com maior lucro total",
        "Gênero com maior margem de lucro média",
    ],
    "Avaliações dos Usuários": [
        "Filmes mais avaliados pelos usuários",
        "Filmes em que a nota média dos usuários mais diverge da nota IMDb",
    ],
}


# ----------------------------------------------------------------------------- estado
def _init_state() -> None:
    st.session_state.setdefault("messages", [])  # o que aparece na tela
    st.session_state.setdefault("history", [])  # memória enviada ao agente
    st.session_state.setdefault("pending", None)  # pergunta escolhida na barra lateral


def _reset() -> None:
    st.session_state.messages = []
    st.session_state.history = []
    st.session_state.pending = None


def _queue(question: str) -> None:
    st.session_state.pending = question


# ----------------------------------------------------------------------------- dados da resposta
def _queries_to_dicts(queries: list) -> list[dict]:
    return [
        {
            "sql": q.sql,
            "error": q.error,
            "columns": q.result.columns if q.result else None,
            "rows": [list(row) for row in q.result.rows] if q.result else None,
        }
        for q in queries
    ]


def _entry_from_answer(answer: AgentAnswer) -> dict:
    if answer.from_cache:
        meta = "resposta do cache (0 requisições)"
    elif answer.requests_used is not None:
        meta = f"{answer.requests_used} requisição(ões) ao modelo"
    else:
        meta = ""
    return {
        "role": "assistant",
        "content": answer.text,
        "queries": _queries_to_dicts(answer.queries),
        "meta": meta,
    }


def _last_ok(entry: dict) -> dict | None:
    for query in reversed(entry["queries"]):
        if query["columns"] is not None:
            return query
    return None


# ----------------------------------------------------------------------------- renderização
def _bar_chart(spec: dict) -> None:
    frame = pd.DataFrame(
        {spec["label_column"]: spec["labels"], spec["value_column"]: spec["values"]}
    )
    try:
        st.bar_chart(frame, x=spec["label_column"], y=spec["value_column"], sort=False)
    except TypeError:  # versões do Streamlit sem o parâmetro `sort`
        st.bar_chart(frame, x=spec["label_column"], y=spec["value_column"])


def _render_assistant(entry: dict, show_sql: bool) -> None:
    st.markdown(entry["content"])
    last = _last_ok(entry)
    if last:
        result = QueryResult(last["columns"], [tuple(row) for row in last["rows"]])
        spec = chart_spec(result)
        if spec:
            _bar_chart(spec)
        with st.expander("Dados retornados"):
            st.dataframe(pd.DataFrame(last["rows"], columns=last["columns"]), hide_index=True)
    if show_sql and entry["queries"]:
        with st.expander("SQL executado"):
            for query in entry["queries"]:
                st.code(query["sql"], language="sql")
                if query["error"]:
                    st.caption(f"erro: {query['error']}")
    if entry["meta"]:
        st.caption(entry["meta"])


def _handle(question: str, show_sql: bool, use_cache: bool) -> None:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Consultando a camada Gold..."):
            try:
                answer = ask(question, history=st.session_state.history, use_cache=use_cache)
                entry = _entry_from_answer(answer)
                st.session_state.history = answer.history
            except GuardrailError as exc:
                entry = {"role": "assistant", "content": f"⚠️ {exc}", "queries": [], "meta": ""}
            except (ConfigError, AgentError) as exc:
                entry = {
                    "role": "assistant",
                    "content": f"❌ {exc}",
                    "queries": _queries_to_dicts(getattr(exc, "queries", [])),
                    "meta": "",
                }
        _render_assistant(entry, show_sql)
    st.session_state.messages.append(entry)


# ----------------------------------------------------------------------------- página
st.set_page_config(page_title="CineData Agent", page_icon="🎬", layout="wide")
_init_state()

with st.sidebar:
    st.header("CineData Agent")
    show_sql = st.checkbox("Mostrar SQL executado", value=True)
    use_cache = st.checkbox("Usar cache de respostas", value=True)
    st.button("Nova conversa", on_click=_reset)
    st.caption("Modelos gratuitos do OpenRouter: limite de 50 requisições por dia.")
    st.subheader("Perguntas de exemplo")
    counter = 0
    for category, questions in EXEMPLOS.items():
        with st.expander(category):
            for example in questions:
                counter += 1
                st.button(example, key=f"example_{counter}", on_click=_queue, args=(example,))

st.title("🎬 CineData Analytics")
st.caption("Pergunte em português sobre o catálogo de filmes. As respostas vêm da camada Gold (SQLite).")

if not st.session_state.messages:
    st.info("Escolha uma pergunta de exemplo na barra lateral ou digite a sua abaixo.")
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["content"])
        else:
            _render_assistant(message, show_sql)

typed = st.chat_input("Pergunte sobre o catálogo de filmes...")
question = st.session_state.pending or typed
st.session_state.pending = None
if question:
    _handle(question, show_sql, use_cache)