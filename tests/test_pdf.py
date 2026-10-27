import os
import shutil
from pathlib import Path

import pytest

from polishare import pdf
from polishare.cli import main
from polishare.pdf import (
    ErroPDF,
    comandos_latex,
    compilar,
    desatualizado,
    destino_do_pdf,
    fontes_de_simulados,
    markdown_em_simulados,
    resumo_do_erro,
    svg_para_pdf,
)

TEX_MINIMO = r"""\documentclass{article}
\begin{document}
Olá, $\vec v = 2\,\vec\imath$.
\end{document}
"""
TYP_MINIMO = "#set page(width: 8cm, height: auto)\nOlá, $arrow(v) = 2 arrow(i)$.\n"
MODELOS = Path(__file__).resolve().parent.parent / "modelos"
SVG_MINIMO = '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20"><rect width="40" height="20" fill="#888"/></svg>'


@pytest.fixture
def simulados(tmp_path):
    fontes = tmp_path / "materias" / "PME3100 - Mecânica I" / "estudo" / "simulados" / ".fontes"
    fontes.mkdir(parents=True)
    return fontes


def test_pdf_de_fonte_em_fontes_sai_na_pasta_simulados(simulados):
    assert destino_do_pdf(simulados / "2026-10-27-P2.tex") == simulados.parent / "2026-10-27-P2.pdf"


def test_pdf_de_fonte_solta_sai_ao_lado(tmp_path):
    assert destino_do_pdf(tmp_path / "x.typ") == tmp_path / "x.pdf"


def test_desatualizado_olha_fonte_e_figuras_do_mesmo_prefixo(simulados):
    fonte = simulados / "2026-10-27-P2.tex"
    figura = simulados / "2026-10-27-P2-fig2.svg"
    outra = simulados / "2026-11-20-P3-fig1.svg"
    for arquivo in (fonte, figura, outra):
        arquivo.write_text("x")
    assert desatualizado(fonte)  # ainda não há PDF

    gerado = destino_do_pdf(fonte)
    gerado.write_bytes(b"%PDF")
    os.utime(fonte, (1000, 1000))
    os.utime(figura, (1000, 1000))
    os.utime(gerado, (2000, 2000))
    os.utime(outra, (3000, 3000))  # figura de outro simulado não conta
    assert not desatualizado(fonte)

    os.utime(figura, (3000, 3000))
    assert desatualizado(fonte)


def test_fontes_e_markdown_de_simulados(simulados, tmp_path):
    (simulados / "a.tex").write_text("x")
    (simulados / "b.typ").write_text("x")
    (simulados / "fig.svg").write_text("x")
    (simulados.parent / "velho.md").write_text("x")
    destino = tmp_path / "materias"
    assert [f.name for f in fontes_de_simulados(destino)] == ["a.tex", "b.typ"]
    assert [f.name for f in markdown_em_simulados(destino)] == ["velho.md"]


@pytest.mark.parametrize(
    ("disponiveis", "motor", "passadas"),
    [({"tectonic", "pdflatex"}, "tectonic", 1), ({"latexmk", "pdflatex"}, "latexmk", 1), ({"pdflatex"}, "pdflatex", 2)],
)
def test_escolhe_o_motor_latex(monkeypatch, tmp_path, disponiveis, motor, passadas):
    monkeypatch.setattr(pdf.shutil, "which", lambda nome: f"/bin/{nome}" if nome in disponiveis else None)
    comandos = comandos_latex(tmp_path / "x.tex", tmp_path)
    assert [c[0] for c in comandos] == [motor] * passadas
    assert all("x.tex" in c for c in comandos)


def test_sem_motor_latex_explica_como_instalar(monkeypatch, tmp_path):
    monkeypatch.setattr(pdf.shutil, "which", lambda nome: None)
    with pytest.raises(ErroPDF, match="brew install tectonic"):
        comandos_latex(tmp_path / "x.tex", tmp_path)


def test_recusa_extensao_errada(tmp_path):
    (tmp_path / "x.md").write_text("# não")
    with pytest.raises(ErroPDF, match="só .tex e .typ"):
        compilar(tmp_path / "x.md")


def test_resumo_do_erro_pega_as_linhas_do_latex():
    log = "linha 1\nlinha 2\n! Undefined control sequence.\nl.7 \\vecc\n{v}\nfim\n"
    assert resumo_do_erro(log).startswith("! Undefined control sequence.\nl.7 \\vecc")
    assert resumo_do_erro("a\nb\nc", linhas=2) == "b\nc"


def test_compila_typst(simulados):
    fonte = simulados / "teste.typ"
    fonte.write_text(TYP_MINIMO, encoding="utf-8")
    assert compilar(fonte).read_bytes().startswith(b"%PDF")


def test_converte_svg_para_pdf(simulados):
    svg = simulados / "teste-fig1.svg"
    svg.write_text(SVG_MINIMO)
    assert svg_para_pdf(svg).read_bytes().startswith(b"%PDF")


@pytest.mark.skipif(not shutil.which("tectonic"), reason="Tectonic não instalado")
def test_compila_latex_e_so_deixa_o_pdf(simulados):
    fonte = simulados / "teste.tex"
    fonte.write_text(TEX_MINIMO, encoding="utf-8")
    gerado = compilar(fonte)
    assert gerado == simulados.parent / "teste.pdf" and gerado.read_bytes().startswith(b"%PDF")
    assert sorted(p.name for p in simulados.parent.iterdir()) == [".fontes", "teste.pdf"]  # sem .aux nem .log


@pytest.mark.skipif(not shutil.which("tectonic"), reason="Tectonic não instalado")
@pytest.mark.parametrize("modelo", ["simulado.tex", "gabarito.tex"])
def test_modelos_do_repositorio_compilam(simulados, modelo):
    fonte = simulados / modelo
    shutil.copy(MODELOS / modelo, fonte)
    assert compilar(fonte).read_bytes().startswith(b"%PDF")


@pytest.mark.skipif(not shutil.which("tectonic"), reason="Tectonic não instalado")
def test_erro_de_latex_vira_erro_legivel(simulados):
    fonte = simulados / "quebrado.tex"
    fonte.write_text("\\documentclass{article}\\begin{document}\\comandoinexistente\\end{document}")
    with pytest.raises(ErroPDF, match="o LaTeX falhou"):
        compilar(fonte)


def test_comando_pdf_compila_pendentes_e_avisa_de_markdown(simulados, tmp_path, capsys):
    (simulados / "teste.typ").write_text(TYP_MINIMO, encoding="utf-8")
    (simulados.parent / "velho.md").write_text("x")
    destino = str(tmp_path / "materias")
    assert main(["pdf", "--destino", destino]) == 0
    saida = capsys.readouterr()
    assert "teste.pdf" in saida.out and "velho.md" in saida.err

    assert main(["pdf", "--destino", destino]) == 0
    assert "já estão em PDF e em dia" in capsys.readouterr().out


def test_comando_pdf_falha_com_codigo_2(tmp_path, capsys):
    (tmp_path / "x.typ").write_text("#chamada_inexistente()")
    assert main(["pdf", str(tmp_path / "x.typ"), "--destino", str(tmp_path)]) == 2
    assert "o Typst falhou" in capsys.readouterr().err
