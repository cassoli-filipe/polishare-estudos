import json
from datetime import date
from pathlib import Path

import pytest

from polishare.cli import baixar, escolher_disciplina
from polishare.client import Abortar, Baixado, ErroPolishare
from polishare.crawl import Escopo
from polishare.index import ano, gerar_index, tem_resolucao
from polishare.parse import Disciplina
from polishare.store import Manifest

MECANICA = Disciplina("ExY", "PME3100", "Mecânica I")


class ClienteFalso:
    """Serve as fixtures reais: matéria → Provas → P1. As outras pastas estão vazias."""

    def __init__(self, fixture, falhar=(), abortar_em=None):
        self.paginas = {
            "index.php?id=ExY": fixture("materia"),
            "index.php?id=3Y3w": fixture("provas"),
            "index.php?id=2mKe": fixture("p1"),
        }
        self.falhar, self.abortar_em = set(falhar), abortar_em
        self.baixados = []

    def pagina(self, caminho):
        return self.paginas.get(caminho, "<table></table>")

    def arquivo(self, id_arquivo, destino):
        if id_arquivo == self.abortar_em:
            destino.write_bytes(b"%PD")
            raise Abortar("O Polishare respondeu 429")
        if id_arquivo in self.falhar:
            raise ErroPolishare(f"file.php?id={id_arquivo}: HTTP 500")
        destino.write_bytes(b"%PDF " + id_arquivo.encode())
        self.baixados.append(id_arquivo)
        return Baixado(".pdf", 5 + len(id_arquivo))


def test_baixa_espelhando_as_pastas_e_gera_indices(tmp_path, fixture):
    cliente = ClienteFalso(fixture)
    resumo = baixar(cliente, MECANICA, tmp_path, saida=lambda _: None)

    raiz = tmp_path / "PME3100 - Mecânica I"
    assert resumo.novos == 9 and resumo.falhas == 0 and resumo.links == 1
    assert (raiz / "PME3100 Formulário de Provas 2024.pdf").read_bytes() == b"%PDF aBoy"
    assert (raiz / "Provas/P1/P1 2023(COM RESOLUÇÃO).pdf").exists()
    assert (raiz / "Provas/P1/2018 Reof.pdf").exists() and (raiz / "Provas/P1/2018.pdf").exists()
    assert not list(raiz.rglob("*.part"))

    manifest = json.loads((raiz / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["arquivos"]["jbz7"]["caminho"] == "Provas/P1/2022 P1 (Resolução).pdf"
    assert "respondeai" in (raiz / "links.md").read_text(encoding="utf-8")
    index = (raiz / "INDEX.md").read_text(encoding="utf-8")
    assert "| P1 | 2022 P1 (Resolução) | 2022 | sim |" in index
    assert "| P1 | 2021 | 2021 | ? |" in index


def test_segunda_execucao_nao_baixa_nada(tmp_path, fixture):
    baixar(ClienteFalso(fixture), MECANICA, tmp_path, saida=lambda _: None)
    cliente = ClienteFalso(fixture)
    resumo = baixar(cliente, MECANICA, tmp_path, saida=lambda _: None)
    assert (resumo.novos, resumo.existentes, cliente.baixados) == (0, 9, [])


def test_falha_fica_registrada_e_e_tentada_de_novo(tmp_path, fixture):
    resumo = baixar(ClienteFalso(fixture, falhar={"6krY"}), MECANICA, tmp_path, saida=lambda _: None)
    raiz = tmp_path / "PME3100 - Mecânica I"
    assert resumo.falhas == 1
    assert "6krY" in Manifest(raiz, MECANICA).falhas
    assert "## Falhas" in (raiz / "INDEX.md").read_text(encoding="utf-8")

    cliente = ClienteFalso(fixture)
    baixar(cliente, MECANICA, tmp_path, saida=lambda _: None)
    assert cliente.baixados == ["6krY"]
    assert Manifest(raiz, MECANICA).falhas == {}


def test_abortar_salva_o_que_ja_foi_baixado(tmp_path, fixture):
    resumo = baixar(ClienteFalso(fixture, abortar_em="6krY"), MECANICA, tmp_path, saida=lambda _: None)
    raiz = tmp_path / "PME3100 - Mecânica I"
    assert "429" in resumo.interrompido
    assert len(Manifest(raiz, MECANICA).arquivos) == 4  # as 4 primeiras da P1, antes de 6krY
    assert not list(raiz.rglob("*.part"))

    cliente = ClienteFalso(fixture)
    baixar(cliente, MECANICA, tmp_path, saida=lambda _: None)
    assert cliente.baixados == ["6krY", "rl6x", "aMBl", "LYn", "aBoy"]


def test_simular_nao_escreve_nada(tmp_path, fixture):
    cliente = ClienteFalso(fixture)
    resumo = baixar(cliente, MECANICA, tmp_path, simular=True, saida=lambda _: None)
    assert resumo.novos == 9 and dict(resumo.novos_por_pasta) == {"Provas": 8, "(raiz)": 1}
    assert cliente.baixados == []
    assert not any(tmp_path.iterdir())


def test_filtro_de_pastas(tmp_path, fixture):
    cliente = ClienteFalso(fixture)
    baixar(cliente, MECANICA, tmp_path, Escopo(pastas=("provas",)), saida=lambda _: None)
    assert "aBoy" not in cliente.baixados and len(cliente.baixados) == 8


def test_escolher_disciplina():
    a1 = Disciplina("1V", "MAT3457", "Álgebra Linear I")
    a2 = Disciplina("Lmjn", "MAT3457", "Álgebra Linear I")
    outra = Disciplina("od", "MAT2453", "Cálculo I")
    assert escolher_disciplina([outra, a1], "mat3457", None) == a1
    with pytest.raises(ErroPolishare, match="--id"):
        escolher_disciplina([a1, a2], "MAT3457", None)
    assert escolher_disciplina([a1, a2], "MAT3457", "Lmjn") == a2
    with pytest.raises(ErroPolishare, match="código exato"):
        escolher_disciplina([outra], "MAT3457", None)
    with pytest.raises(ErroPolishare, match="não achou nada"):
        escolher_disciplina([], "MAT3457", None)


@pytest.mark.parametrize(
    ("nome", "esperado"),
    [("P1 2023(COM RESOLUÇÃO)", "2023"), ("2018 Reof", "2018"), ("PREC 26", ""), ("Lista 12345", "")],
)
def test_ano(nome, esperado):
    assert ano(nome) == esperado


def test_tem_resolucao():
    assert tem_resolucao("P1 2023(COM RESOLUÇÃO)", ["Provas", "P1"])
    assert tem_resolucao("2022 gabarito", ["Provas"])
    assert tem_resolucao("P1 2019", ["Resoluções", "P1"])
    assert not tem_resolucao("P1 2019", ["Provas", "P1"])


def test_index_ordena_por_subpasta_e_ano_e_escapa_barras(tmp_path):
    m = Manifest(tmp_path, MECANICA)
    validade = date(2026, 11, 26)
    m.registrar("a", Path("Provas/P2/2019.pdf"), ("Provas", "P2"), "2019", 1, validade)
    m.registrar("b", Path("Provas/P1/2018.pdf"), ("Provas", "P1"), "2018", 1, validade)
    m.registrar("c", Path("Provas/P1/2021.pdf"), ("Provas", "P1"), "2021 | turma A", 1, validade)
    linhas = [l for l in gerar_index(m).splitlines() if l.startswith("| P")]
    assert [l.split(" | ")[1] for l in linhas] == ["2021 \\| turma A", "2018", "2019"]


def test_baixar_por_prova_deixa_a_raiz_e_outras_pastas_de_fora(tmp_path, fixture):
    cliente = ClienteFalso(fixture)
    resumo = baixar(cliente, MECANICA, tmp_path, Escopo(prova="P1"), saida=lambda _: None)
    assert resumo.novos == 8 and resumo.links == 0
    assert "aBoy" not in cliente.baixados


def test_validade_e_renovacao(tmp_path, fixture):
    raiz = tmp_path / "PME3100 - Mecânica I"
    baixar(ClienteFalso(fixture), MECANICA, tmp_path, Escopo(prova="P1"), validade=date(2026, 11, 26), saida=lambda _: None)
    assert {r["expira_em"] for r in Manifest(raiz, MECANICA).arquivos.values()} == {"2026-11-26"}

    # sem renovar, rodar de novo com outra data não mexe nos que já existem
    baixar(ClienteFalso(fixture), MECANICA, tmp_path, Escopo(prova="P1"), validade=date(2026, 12, 1), saida=lambda _: None)
    assert {r["expira_em"] for r in Manifest(raiz, MECANICA).arquivos.values()} == {"2026-11-26"}

    # com renovar (--ate), passam a valer até a nova data
    baixar(ClienteFalso(fixture), MECANICA, tmp_path, Escopo(prova="P1"), validade=date(2026, 12, 1), renovar=True,
           saida=lambda _: None)
    assert {r["expira_em"] for r in Manifest(raiz, MECANICA).arquivos.values()} == {"2026-12-01"}
