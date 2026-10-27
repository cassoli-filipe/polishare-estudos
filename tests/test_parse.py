import pytest

from polishare.parse import Disciplina, Item, classificar_href, esta_deslogado, esta_logado, parse_busca, parse_pasta


def test_busca_extrai_id_codigo_e_nome(fixture):
    assert parse_busca(fixture("busca_pme3100")) == [Disciplina("ExY", "PME3100", "Mecânica I")]


def test_pasta_da_materia_tem_link_pastas_e_arquivo_solto(fixture):
    itens = parse_pasta(fixture("materia"))
    assert itens[0] == Item(
        "link",
        "Material de Apoio",
        "https://www.respondeai.com.br/materias/completas/10?utm_source=Referral&utm_campaign=Polishare",
    )
    assert [i.nome for i in itens if i.tipo == "pasta"] == [
        "Aulas", "Exercícios", "Listas", "Provas", "Resoluções", "Resumos", "Teoria",
    ]
    assert itens[-1] == Item("arquivo", "PME3100 Formulário de Provas 2024", "aBoy")


def test_pasta_de_provas_lista_subpastas(fixture):
    assert parse_pasta(fixture("provas")) == [
        Item("pasta", "P1", "2mKe"),
        Item("pasta", "P2", "dDza"),
        Item("pasta", "P3", "yvEx"),
        Item("pasta", "PRec", "5VQ3"),
        Item("pasta", "PSub", "VN6V"),
    ]


def test_arquivos_tem_espacos_normalizados(fixture):
    itens = parse_pasta(fixture("p1"))
    assert all(i.tipo == "arquivo" for i in itens)
    assert [i.nome for i in itens] == [
        "P1 2026 (Resolução)", "P1 2025", "P1 2023(COM RESOLUÇÃO)", "2022 P1 (Resolução)",
        "2021", "2018 Reof", "2018", "2000",
    ]


def test_favoritos_nunca_viram_item(fixture):
    for nome in ("materia", "provas", "p1"):
        assert not any("favoritos" in i.alvo for i in parse_pasta(fixture(nome)))


@pytest.mark.parametrize(
    "href",
    [
        "?pagina=favoritos&action=ap&codigo=O0yE",
        "index.php?pagina=favoritos&action=ap&codigo=ExY",
        "/perfil.php",
        "perfil.php?id=Z4VP",
        "/logout.php",
        "/index.php?pagina=configuracoes",
        "/course.php?a=r",
        "/index.php?semestre=2",
        "index.php?pagina=pesquisa&t=d&q=PME3100",
        "http://www.polishare.com.br/index.php?id=M7m8",
        "javascript:void(0)",
        "#",
        "",
        None,
    ],
)
def test_lista_de_permissao_recusa_o_resto(href):
    assert classificar_href(href) is None


@pytest.mark.parametrize(
    ("href", "esperado"),
    [
        ("index.php?id=O0yE", ("pasta", "O0yE")),
        ("?id=ExY", ("pasta", "ExY")),
        ("/index.php?id=3Y3w", ("pasta", "3Y3w")),
        ("file.php?id=aBoy", ("arquivo", "aBoy")),
        ("https://www.respondeai.com.br/x", ("link", "https://www.respondeai.com.br/x")),
    ],
)
def test_lista_de_permissao_aceita_pastas_arquivos_e_externos(href, esperado):
    assert classificar_href(href) == esperado


def test_detecta_pagina_deslogada(fixture):
    assert esta_deslogado(fixture("deslogado"))
    assert not esta_logado(fixture("deslogado"))


def test_detecta_pagina_logada(fixture):
    for nome in ("busca_pme3100", "materia", "p1"):
        assert esta_logado(fixture(nome))
        assert not esta_deslogado(fixture(nome))
