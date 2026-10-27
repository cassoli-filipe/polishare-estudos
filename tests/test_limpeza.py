from datetime import date, timedelta
from pathlib import Path

import pytest

from polishare.cli import main
from polishare.limpeza import limpar_materia, materias_em
from polishare.parse import Disciplina
from polishare.store import Manifest, expira_em

MECANICA = Disciplina("ExY", "PME3100", "Mecânica I")
HOJE = date(2026, 11, 20)


@pytest.fixture
def materia(tmp_path):
    """P1 vence antes de HOJE, P2 depois; há um mapa em estudo/ que nunca pode sumir."""
    raiz = tmp_path / "materias" / "PME3100 - Mecânica I"
    m = Manifest(raiz, MECANICA)
    for id_arquivo, pasta, validade in [
        ("a", ("Provas", "P1"), date(2026, 11, 10)),
        ("b", ("Provas", "P1"), date(2026, 11, 10)),
        ("c", ("Provas", "P2"), date(2026, 12, 5)),
        ("r", ("Resoluções",), date(2026, 11, 10)),
    ]:
        caminho = Path(*pasta, f"{id_arquivo}.pdf")
        (raiz / caminho).parent.mkdir(parents=True, exist_ok=True)
        (raiz / caminho).write_bytes(b"%PDF" + b"x" * 1000)
        m.registrar(id_arquivo, caminho, pasta, f"P1 {id_arquivo}" if id_arquivo == "r" else id_arquivo, 1004, validade)
    (raiz / "estudo").mkdir()
    (raiz / "estudo" / "mapa-P1.md").write_text("# Mapa", encoding="utf-8")
    m.salvar()
    return raiz


def test_apaga_so_o_que_venceu_e_mantem_estudo(materia):
    m = Manifest(materia, MECANICA)
    apagados = limpar_materia(m, HOJE)
    assert sorted(a.caminho for a in apagados) == ["Provas/P1/a.pdf", "Provas/P1/b.pdf", "Resoluções/r.pdf"]
    assert sum(a.bytes for a in apagados) == 3 * 1004
    assert not (materia / "Provas" / "P1").exists() and not (materia / "Resoluções").exists()
    assert (materia / "Provas" / "P2" / "c.pdf").exists()
    assert (materia / "estudo" / "mapa-P1.md").exists()

    de_novo = Manifest(materia, MECANICA)
    assert set(de_novo.presentes()) == {"c"}
    assert de_novo.arquivos["a"]["removido_em"]
    index = (materia / "INDEX.md").read_text(encoding="utf-8")
    assert "Provas/P1/a.pdf" not in index and "Provas/P2/c.pdf" in index
    assert "3 já expiraram" in index


def test_no_ultimo_dia_ainda_nao_apaga(materia):
    assert limpar_materia(Manifest(materia, MECANICA), date(2026, 11, 10)) == []


def test_agora_por_prova(materia):
    apagados = limpar_materia(Manifest(materia, MECANICA), date(2026, 10, 27), imediato=True, prova="P2")
    assert [a.caminho for a in apagados] == ["Provas/P2/c.pdf"]


def test_arquivo_apagado_volta_no_proximo_download(materia):
    m = Manifest(materia, MECANICA)
    limpar_materia(m, HOJE)
    assert not m.ja_baixado("a")
    assert m.destino_livre(("Provas", "P1"), "a", ".pdf", "a") == Path("Provas/P1/a.pdf")
    m.registrar("a", Path("Provas/P1/a.pdf"), ("Provas", "P1"), "a", 1004, date(2026, 12, 20))
    assert "removido_em" not in m.arquivos["a"]


def test_registro_antigo_sem_data_vale_30_dias():
    assert expira_em({"baixado_em": "2026-10-27T14:22:36-03:00"}) == date(2026, 11, 26)
    assert expira_em({"baixado_em": "2026-10-27T14:22:36-03:00", "expira_em": "2026-11-10"}) == date(2026, 11, 10)


def test_materias_em(materia, tmp_path):
    assert [m.disciplina for m in materias_em(tmp_path / "materias")] == [MECANICA]


def test_limpar_pela_linha_de_comando_nao_pede_credenciais(materia, tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("POLISHARE_EMAIL", raising=False)
    monkeypatch.delenv("POLISHARE_SENHA", raising=False)
    m = Manifest(materia, MECANICA)
    for id_arquivo in m.arquivos:
        m.renovar(id_arquivo, date.today() + timedelta(days=10))
    m.salvar()
    destino = str(tmp_path / "materias")
    assert main(["limpar", "--destino", destino, "--quieto"]) == 0
    assert capsys.readouterr().out == ""  # nada venceu ainda

    assert main(["limpar", "PME3100", "--prova", "P1", "--agora", "--destino", destino]) == 0
    saida = capsys.readouterr().out
    assert "3 PDFs apagados" in saida and "1 PDFs no disco" in saida


def test_agora_exige_codigo(tmp_path, capsys):
    assert main(["limpar", "--agora", "--destino", str(tmp_path)]) == 2
    assert "precisa do código" in capsys.readouterr().err


def test_codigo_que_nao_foi_baixado(tmp_path, capsys):
    assert main(["limpar", "MAT2453", "--destino", str(tmp_path)]) == 2


def test_baixar_recusa_data_passada_e_prova_com_pastas():
    with pytest.raises(SystemExit):
        main(["baixar", "PME3100", "--ate", "2000-01-01"])
    with pytest.raises(SystemExit):
        main(["baixar", "PME3100", "--prova", "P1", "--pastas", "Provas"])
