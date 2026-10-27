import json
from datetime import date
from pathlib import Path

from polishare.parse import Disciplina
from polishare.store import Manifest, higienizar, pasta_da_disciplina

MECANICA = Disciplina("ExY", "PME3100", "Mecânica I")
VALIDADE = date(2026, 11, 26)


def test_higienizar_remove_caracteres_proibidos_e_espacos():
    assert higienizar("  P1   2023(COM RESOLUÇÃO)  ") == "P1 2023(COM RESOLUÇÃO)"
    assert higienizar('a/b\\c:d*e?f"g<h>i|j') == "a-b-c-d-e-f-g-h-i-j"
    assert higienizar("...") == "sem nome"
    assert len(higienizar("x" * 300)) == 120


def test_pasta_da_disciplina(tmp_path):
    assert pasta_da_disciplina(tmp_path, MECANICA) == tmp_path / "PME3100 - Mecânica I"


def test_manifest_ida_e_volta(tmp_path):
    m = Manifest(tmp_path, MECANICA)
    m.registrar("a", Path("Provas/P1/2021.pdf"), ("Provas", "P1"), "2021", 10, VALIDADE)
    m.registrar_falha("b", ("Listas",), "Lista 3", "timeout")
    m.adicionar_link((), "Material", "https://externo.com")
    m.adicionar_link((), "Material", "https://externo.com")
    m.salvar()

    dados = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert dados["disciplina"] == {"id": "ExY", "codigo": "PME3100", "nome": "Mecânica I"}
    assert dados["arquivos"]["a"]["caminho"] == "Provas/P1/2021.pdf"
    assert dados["falhas"]["b"]["erro"] == "timeout"
    assert len(dados["links"]) == 1
    assert not list(tmp_path.glob(".manifest-*"))

    de_novo = Manifest(tmp_path, MECANICA)
    assert de_novo.arquivos == m.arquivos and de_novo.falhas == m.falhas


def test_sucesso_apaga_falha_anterior(tmp_path):
    m = Manifest(tmp_path, MECANICA)
    m.registrar_falha("a", (), "x", "timeout")
    m.registrar("a", Path("x.pdf"), (), "x", 1, VALIDADE)
    assert m.falhas == {}


def test_ja_baixado_exige_o_arquivo_em_disco(tmp_path):
    m = Manifest(tmp_path, MECANICA)
    m.registrar("a", Path("2021.pdf"), (), "2021", 1, VALIDADE)
    assert not m.ja_baixado("a")
    (tmp_path / "2021.pdf").write_bytes(b"%PDF")
    assert m.ja_baixado("a")
    assert not m.ja_baixado("outro")


def test_colisao_de_nome_acrescenta_o_id(tmp_path):
    m = Manifest(tmp_path, MECANICA)
    primeiro = m.destino_livre(("Provas", "P1"), "2018", ".pdf", "aMBl")
    assert primeiro == Path("Provas/P1/2018.pdf")
    m.registrar("aMBl", primeiro, ("Provas", "P1"), "2018", 1, VALIDADE)
    assert m.destino_livre(("Provas", "P1"), "2018", ".pdf", "outro") == Path("Provas/P1/2018 [outro].pdf")
    # o próprio arquivo, baixado de novo, volta para o mesmo lugar
    assert m.destino_livre(("Provas", "P1"), "2018", ".pdf", "aMBl") == primeiro


def test_colisao_com_arquivo_que_ja_existe_em_disco(tmp_path):
    (tmp_path / "2018.pdf").write_bytes(b"%PDF")
    m = Manifest(tmp_path, MECANICA)
    assert m.destino_livre((), "2018", ".pdf", "novo") == Path("2018 [novo].pdf")
