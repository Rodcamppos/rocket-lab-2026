"""Testes do CRUD de filmes, avaliações, busca e paginação."""

BASE = "/api/v1/movies"

NOVO = {
    "titulo": "Filme de Teste",
    "ano_lancamento": 2020,
    "duracao_minutos": 100,
    "sinopse": "Uma sinopse qualquer.",
    "status_filme": "Lançado",
    "diretores": ["Diretora Um"],
    "generos": ["Drama", "Comédia"],
}


async def _criar(client, **extra):
    r = await client.post(BASE, json={**NOVO, **extra})
    assert r.status_code == 201, r.text
    return r.json()


async def _avaliar(client, mid, nota, nome="Ana", comentario="Bom filme"):
    return await client.post(
        f"{BASE}/{mid}/reviews",
        json={"nome": nome, "nota_estrelas": nota, "comentario": comentario},
    )


# ---------- criar / detalhar ----------


async def test_create_and_get_detail(client):
    criado = await _criar(client)
    assert criado["titulo"] == "Filme de Teste"
    assert sorted(g["nome_genero"] for g in criado["generos"]) == ["Comédia", "Drama"]
    assert [d["nome_pessoa"] for d in criado["diretores"]] == ["Diretora Um"]
    assert criado["nota_media_estrelas"] is None
    assert criado["qtd_avaliacoes"] == 0

    r = await client.get(f"{BASE}/{criado['sk_movie_id']}")
    assert r.status_code == 200
    assert r.json()["sinopse"] == "Uma sinopse qualquer."


async def test_get_unknown_movie_returns_404(client):
    assert (await client.get(f"{BASE}/nao-existe")).status_code == 404


async def test_create_rejects_blank_title(client):
    r = await client.post(BASE, json={**NOVO, "titulo": "   "})
    assert r.status_code == 422


async def test_create_dedupes_genres_and_directors(client):
    criado = await _criar(client, generos=["Drama", "drama", " Drama "], diretores=["A", "a"])
    assert len(criado["generos"]) == 1
    assert len(criado["diretores"]) == 1


# ---------- atualizar ----------


async def test_patch_updates_only_sent_fields(client):
    criado = await _criar(client)
    mid = criado["sk_movie_id"]

    r = await client.patch(f"{BASE}/{mid}", json={"titulo": "Novo Título"})
    assert r.status_code == 200
    body = r.json()
    assert body["titulo"] == "Novo Título"
    assert body["ano_lancamento"] == 2020
    assert body["sinopse"] == "Uma sinopse qualquer."
    assert len(body["generos"]) == 2


async def test_patch_can_clear_optional_field(client):
    mid = (await _criar(client))["sk_movie_id"]
    r = await client.patch(f"{BASE}/{mid}", json={"sinopse": None})
    assert r.status_code == 200
    assert r.json()["sinopse"] is None


async def test_patch_replaces_genres_and_directors(client):
    mid = (await _criar(client))["sk_movie_id"]
    r = await client.patch(f"{BASE}/{mid}", json={"generos": ["Terror"], "diretores": ["Outro"]})
    body = r.json()
    assert [g["nome_genero"] for g in body["generos"]] == ["Terror"]
    assert [d["nome_pessoa"] for d in body["diretores"]] == ["Outro"]


async def test_patch_rejects_null_title(client):
    mid = (await _criar(client))["sk_movie_id"]
    assert (await client.patch(f"{BASE}/{mid}", json={"titulo": None})).status_code == 422


async def test_patch_unknown_movie_returns_404(client):
    r = await client.patch(f"{BASE}/nao-existe", json={"titulo": "X"})
    assert r.status_code == 404


# ---------- remover ----------


async def test_delete_movie_and_its_reviews(client):
    mid = (await _criar(client))["sk_movie_id"]
    assert (await _avaliar(client, mid, 4)).status_code == 201

    assert (await client.delete(f"{BASE}/{mid}")).status_code == 204
    assert (await client.get(f"{BASE}/{mid}")).status_code == 404
    assert (await client.get(BASE)).json()["total"] == 0
    # segunda remoção: já não existe
    assert (await client.delete(f"{BASE}/{mid}")).status_code == 404


# ---------- avaliações ----------


async def test_add_review_appears_in_detail(client):
    mid = (await _criar(client))["sk_movie_id"]
    r = await _avaliar(client, mid, 5, nome="Bia", comentario="Ótimo!")
    assert r.status_code == 201
    body = r.json()
    assert body["qtd_avaliacoes"] == 1
    assert body["reviews"][0]["nome"] == "Bia"
    assert body["reviews"][0]["nota_estrelas"] == 5.0
    assert body["reviews"][0]["created_at"]


async def test_average_rating(client):
    mid = (await _criar(client))["sk_movie_id"]
    await _avaliar(client, mid, 2)
    r = await _avaliar(client, mid, 5)
    body = r.json()
    assert body["qtd_avaliacoes"] == 2
    assert body["nota_media_estrelas"] == 3.5

    listagem = (await client.get(BASE)).json()["items"][0]
    assert listagem["nota_media_estrelas"] == 3.5
    assert listagem["qtd_avaliacoes"] == 2


async def test_review_validation(client):
    mid = (await _criar(client))["sk_movie_id"]
    assert (await _avaliar(client, mid, 0)).status_code == 422
    assert (await _avaliar(client, mid, 6)).status_code == 422
    assert (await _avaliar(client, mid, 3, comentario="")).status_code == 422
    assert (await _avaliar(client, mid, 3, nome="")).status_code == 422


async def test_review_on_unknown_movie_returns_404(client):
    assert (await _avaliar(client, "nao-existe", 3)).status_code == 404


# ---------- busca e paginação ----------


async def test_search_is_case_insensitive(client):
    await _criar(client, titulo="O Grande Truque")
    await _criar(client, titulo="Outro Filme")
    r = await client.get(BASE, params={"search": "grande"})
    assert [i["titulo"] for i in r.json()["items"]] == ["O Grande Truque"]


async def test_pagination(client):
    for i in range(5):
        await _criar(client, titulo=f"Paginado {i}")

    p1 = (await client.get(BASE, params={"page": 1, "page_size": 2})).json()
    p3 = (await client.get(BASE, params={"page": 3, "page_size": 2})).json()
    assert p1["total"] == 5
    assert p1["total_pages"] == 3
    assert len(p1["items"]) == 2
    assert len(p3["items"]) == 1
    assert (await client.get(BASE, params={"page": 0})).status_code == 422


async def test_fixed_routes_are_not_shadowed_by_id_route(client):
    assert (await client.get(f"{BASE}/generos")).status_code == 200
    assert (await client.get(f"{BASE}/insights")).status_code == 200