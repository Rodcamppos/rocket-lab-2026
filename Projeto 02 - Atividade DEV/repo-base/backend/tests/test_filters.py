"""Testes de filtros, ordenação, gêneros e insights (usam a fixture `client` do conftest)."""

BASE = "/api/v1/movies"


async def _mk(client, titulo, ano, generos):
    r = await client.post(BASE, json={"titulo": titulo, "ano_lancamento": ano, "generos": generos})
    assert r.status_code == 201, r.text
    return r.json()["sk_movie_id"]


async def _review(client, mid, nota):
    r = await client.post(
        f"{BASE}/{mid}/reviews", json={"nome": "T", "nota_estrelas": nota, "comentario": "x"}
    )
    assert r.status_code == 201, r.text


async def test_filter_by_genre_and_year(client):
    await _mk(client, "Zfiltro A", 1999, ["Zgenero"])
    await _mk(client, "Zfiltro B", 2001, ["Zgenero"])
    await _mk(client, "Zfiltro C", 1999, ["Outro"])

    r = await client.get(BASE, params={"search": "Zfiltro", "genero": "zgenero"})
    assert r.json()["total"] == 2

    r = await client.get(BASE, params={"search": "Zfiltro", "genero": "Zgenero", "ano": 1999})
    assert [i["titulo"] for i in r.json()["items"]] == ["Zfiltro A"]


async def test_sort_by_rating_and_year(client):
    a = await _mk(client, "Znota A", 2000, ["Zg2"])
    b = await _mk(client, "Znota B", 2010, ["Zg2"])
    await _review(client, a, 2)
    await _review(client, b, 5)

    r = await client.get(BASE, params={"search": "Znota", "ordem": "nota"})
    assert [i["titulo"] for i in r.json()["items"]] == ["Znota B", "Znota A"]

    r = await client.get(BASE, params={"search": "Znota", "ordem": "ano"})
    assert [i["titulo"] for i in r.json()["items"]] == ["Znota B", "Znota A"]


async def test_invalid_order_is_rejected(client):
    r = await client.get(BASE, params={"ordem": "aleatorio"})
    assert r.status_code == 422


async def test_genres_endpoint(client):
    await _mk(client, "Zlista", 2005, ["Zlistagenero"])
    r = await client.get(f"{BASE}/generos")
    assert r.status_code == 200
    assert "Zlistagenero" in r.json()


async def test_insights_shape(client):
    r = await client.get(f"{BASE}/insights")
    assert r.status_code == 200
    body = r.json()
    assert {"total_filmes", "total_avaliacoes", "media_geral_estrelas", "generos", "lucrativos"} <= body.keys()