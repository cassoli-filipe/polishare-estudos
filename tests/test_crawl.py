import pytest

from polishare.client import ErroPolishare
from polishare.crawl import ArquivoEncontrado, Escopo, LinkEncontrado, cita_prova, percorrer, pertence_a_prova


def pasta(*linhas: str) -> str:
    corpo = "".join(f"<tr><td>{l}</td><td>x</td><td>--</td></tr>" for l in linhas)
    return f"<table><tr><th>Nome</th></tr>{corpo}</table>"


FAV = '<a href="?pagina=favoritos&action=ap&codigo={0}"></a>'


@pytest.fixture
def site():
    return {
        "index.php?id=raiz": pasta(
            '<a href="https://externo.com/x">Material de Apoio</a>',
            FAV.format("prov") + '<a href="index.php?id=prov"> Provas</a>',
            FAV.format("res") + '<a href="index.php?id=res"> Resoluções</a>',
            '<a href="file.php?id=solto">Formulário</a>',
        ),
        "index.php?id=prov": pasta('<a href="index.php?id=p1"> P1</a>', '<a href="index.php?id=raiz">Volta</a>'),
        "index.php?id=p1": pasta('<a href="file.php?id=a">2021</a>', '<a href="file.php?id=b">2020</a>'),
        "index.php?id=res": pasta('<a href="file.php?id=c">P1 2021 resolvida</a>'),
    }


def test_percorre_tudo_sem_seguir_favoritos_nem_repetir_pasta(site):
    pedidas = []

    def pagina(caminho):
        pedidas.append(caminho)
        return site[caminho]

    achados = list(percorrer(pagina, "raiz"))
    assert achados == [
        LinkEncontrado("Material de Apoio", "https://externo.com/x", ()),
        ArquivoEncontrado("a", "2021", ("Provas", "P1")),
        ArquivoEncontrado("b", "2020", ("Provas", "P1")),
        ArquivoEncontrado("c", "P1 2021 resolvida", ("Resoluções",)),
        ArquivoEncontrado("solto", "Formulário", ()),
    ]
    assert sorted(pedidas) == sorted(set(pedidas))  # o link de volta para a raiz não é visitado de novo
    assert not any("favoritos" in p for p in pedidas)


def test_filtro_de_pastas_ignora_acentos_e_deixa_a_raiz_de_fora(site):
    achados = list(percorrer(site.__getitem__, "raiz", Escopo(pastas=("resolucoes",))))
    assert achados == [ArquivoEncontrado("c", "P1 2021 resolvida", ("Resoluções",))]


def test_filtro_com_pasta_inexistente_explica_as_opcoes(site):
    with pytest.raises(ErroPolishare, match="Provs.*Provas, Resoluções"):
        list(percorrer(site.__getitem__, "raiz", Escopo(pastas=("Provs",))))


def test_respeita_profundidade_maxima(site):
    achados = list(percorrer(site.__getitem__, "raiz", profundidade_maxima=1))
    assert ArquivoEncontrado("a", "2021", ("Provas", "P1")) not in achados
    assert ArquivoEncontrado("c", "P1 2021 resolvida", ("Resoluções",)) in achados


def test_avisa_cada_pasta_visitada(site):
    caminhos = []
    list(percorrer(site.__getitem__, "raiz", ao_entrar=caminhos.append))
    assert caminhos == [(), ("Provas",), ("Provas", "P1"), ("Resoluções",)]


@pytest.fixture
def site_com_provas():
    return {
        "index.php?id=raiz": pasta(
            '<a href="https://externo.com/x">Material de Apoio</a>',
            '<a href="index.php?id=prov"> Provas</a>',
            '<a href="index.php?id=res"> Resoluções</a>',
            '<a href="index.php?id=lis"> Listas</a>',
            '<a href="file.php?id=solto">Formulário</a>',
        ),
        "index.php?id=prov": pasta(
            '<a href="index.php?id=p1"> P1</a>',
            '<a href="index.php?id=p2"> P2</a>',
            '<a href="file.php?id=avulsa">P1 2019 avulsa</a>',
        ),
        "index.php?id=p1": pasta('<a href="file.php?id=a">2021</a>'),
        "index.php?id=p2": pasta('<a href="file.php?id=b">2021</a>'),
        "index.php?id=res": pasta(
            '<a href="file.php?id=r1">P1 2023 Resolução passo a passo</a>',
            '<a href="file.php?id=r2">Resolução Lista 1 - 2014</a>',
            '<a href="file.php?id=r3">Resolução da Prova 1 de 2018</a>',
            '<a href="index.php?id=sub"> Lista 1 - 2014</a>',
        ),
        "index.php?id=sub": pasta('<a href="file.php?id=r4">Exercício 16</a>'),
        "index.php?id=lis": pasta('<a href="file.php?id=l1">Lista 1</a>'),
    }


def test_escopo_por_prova_pega_so_a_prova_e_as_resolucoes_que_a_citam(site_com_provas):
    pedidas = []

    def pagina(caminho):
        pedidas.append(caminho)
        return site_com_provas[caminho]

    achados = list(percorrer(pagina, "raiz", Escopo(prova="p1")))
    assert achados == [
        ArquivoEncontrado("a", "2021", ("Provas", "P1")),
        ArquivoEncontrado("avulsa", "P1 2019 avulsa", ("Provas",)),
        ArquivoEncontrado("r1", "P1 2023 Resolução passo a passo", ("Resoluções",)),
        ArquivoEncontrado("r3", "Resolução da Prova 1 de 2018", ("Resoluções",)),
    ]
    assert "index.php?id=p2" not in pedidas and "index.php?id=lis" not in pedidas


def test_prova_inexistente_lista_as_provas(site_com_provas):
    with pytest.raises(ErroPolishare, match="Prova P4 não encontrada.*P1, P2"):
        list(percorrer(site_com_provas.__getitem__, "raiz", Escopo(prova="P4")))


def test_materia_sem_pasta_provas(site_com_provas):
    site_com_provas["index.php?id=raiz"] = pasta('<a href="index.php?id=lis"> Listas</a>')
    with pytest.raises(ErroPolishare, match="não tem a pasta Provas"):
        list(percorrer(site_com_provas.__getitem__, "raiz", Escopo(prova="P1")))


@pytest.mark.parametrize(
    ("nome", "prova", "esperado"),
    [
        ("P1 2023(COM RESOLUÇÃO)", "P1", True),
        ("2022   P1 (Resolução)", "p1", True),
        ("Resolução da Prova 2", "P2", True),
        ("PREC 26", "PRec", True),
        ("P10 2019", "P1", False),
        ("Resolução Lista 1 - 2014", "P1", False),
        ("Q1 2024", "P1", False),
    ],
)
def test_cita_prova(nome, prova, esperado):
    assert cita_prova(nome, prova) is esperado


def test_pertence_a_prova():
    assert pertence_a_prova(["Provas", "P1"], "2021", "P1")
    assert pertence_a_prova(["Provas", "P1", "Turma A"], "2021", "P1")
    assert not pertence_a_prova(["Provas", "P2"], "P1 2021", "P1")
    assert pertence_a_prova(["Resoluções"], "P1 2023 Resolução", "P1")
    assert not pertence_a_prova(["Listas"], "P1 2023", "P1")
    assert not pertence_a_prova([], "P1 2023", "P1")
