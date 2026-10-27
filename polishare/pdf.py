"""Compila as fontes dos simulados (LaTeX ou Typst) para PDF nativo.

As fontes ficam em `materias/<matéria>/estudo/simulados/.fontes/` e o PDF sai em `simulados/`.
LaTeX usa o primeiro motor disponível: Tectonic, latexmk ou pdflatex. Figuras SVG na pasta das
fontes viram PDF (via Typst) para entrar com `\\includegraphics`.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

PASTA_FONTES = ".fontes"
EXTENSOES = (".tex", ".typ")
TIMEOUT_LATEX = 600  # o Tectonic baixa os pacotes na primeira compilação


class ErroPDF(Exception):
    pass


def destino_do_pdf(fonte: Path) -> Path:
    """Fontes em `simulados/.fontes/` geram o PDF em `simulados/`; as demais, ao lado da fonte."""
    pasta = fonte.parent.parent if fonte.parent.name == PASTA_FONTES else fonte.parent
    return pasta / f"{fonte.stem}.pdf"


def dependencias(fonte: Path) -> list[Path]:
    """A fonte e as figuras SVG com o mesmo prefixo (ex.: `2026-10-27-P2-fig2.svg`)."""
    return [fonte, *sorted(fonte.parent.glob(f"{fonte.stem}*.svg"))]


def desatualizado(fonte: Path) -> bool:
    pdf = destino_do_pdf(fonte)
    if not pdf.exists():
        return True
    return any(d.stat().st_mtime > pdf.stat().st_mtime for d in dependencias(fonte))


def fontes_de_simulados(destino: Path) -> list[Path]:
    return sorted(p for ext in EXTENSOES for p in destino.glob(f"*/estudo/simulados/{PASTA_FONTES}/*{ext}"))


def markdown_em_simulados(destino: Path) -> list[Path]:
    """Simulados têm que ser PDF: qualquer `.md` nessas pastas é um resto a apagar."""
    return sorted(destino.glob("*/estudo/simulados/**/*.md"))


def compilar(fonte: Path) -> Path:
    fonte = fonte.resolve()
    if fonte.suffix not in EXTENSOES:
        raise ErroPDF(f"{fonte.name}: só .tex e .typ viram PDF")
    if not fonte.exists():
        raise ErroPDF(f"{fonte} não existe")
    destino = destino_do_pdf(fonte)
    if fonte.suffix == ".typ":
        _compilar_typst(fonte, destino)
    else:
        _compilar_latex(fonte, destino)
    return destino


def svg_para_pdf(svg: Path) -> Path:
    import typst

    destino = svg.with_suffix(".pdf")
    if destino.exists() and destino.stat().st_mtime >= svg.stat().st_mtime:
        return destino
    with tempfile.TemporaryDirectory(dir=svg.parent, prefix=".svg-") as temporario:
        # A raiz do Typst tem que conter o SVG, então o documento auxiliar fica numa subpasta.
        documento = Path(temporario) / "figura.typ"
        documento.write_text(
            f'#set page(width: auto, height: auto, margin: 0pt)\n#image("../{svg.name}")\n', encoding="utf-8"
        )
        typst.compile(str(documento), output=str(destino), root=str(svg.parent))
    return destino


def comandos_latex(fonte: Path, saida: Path) -> list[list[str]]:
    if shutil.which("tectonic"):
        return [["tectonic", "--chatter", "minimal", "--outdir", str(saida), fonte.name]]
    if shutil.which("latexmk"):
        return [["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", f"-outdir={saida}", fonte.name]]
    if shutil.which("pdflatex"):
        passada = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={saida}", fonte.name]
        return [passada, passada]  # duas passadas para referências e número de páginas
    raise ErroPDF("Nenhum motor LaTeX encontrado. Instale o Tectonic: brew install tectonic")


def _compilar_latex(fonte: Path, destino: Path) -> None:
    for svg in fonte.parent.glob("*.svg"):
        svg_para_pdf(svg)
    # Os auxiliares (.aux, .log) ficam numa pasta temporária: na pasta do simulado só entra o PDF.
    with tempfile.TemporaryDirectory(prefix="polishare-latex-") as temporario:
        saida = Path(temporario)
        for comando in comandos_latex(fonte, saida):
            try:
                resultado = subprocess.run(
                    comando, cwd=fonte.parent, capture_output=True, text=True, timeout=TIMEOUT_LATEX
                )
            except subprocess.TimeoutExpired as erro:
                raise ErroPDF(f"{fonte.name}: o LaTeX passou de {TIMEOUT_LATEX} s") from erro
            if resultado.returncode != 0:
                raise ErroPDF(f"{fonte.name}: o LaTeX falhou\n{resumo_do_erro(resultado.stdout + resultado.stderr)}")
        gerado = saida / f"{fonte.stem}.pdf"
        if not gerado.exists():
            raise ErroPDF(f"{fonte.name}: o motor LaTeX terminou sem gerar o PDF")
        shutil.move(str(gerado), destino)


def _compilar_typst(fonte: Path, destino: Path) -> None:
    import typst

    try:
        typst.compile(str(fonte), output=str(destino), root=str(fonte.parent))
    except Exception as erro:  # o binding expõe erros de compilação como exceções genéricas
        raise ErroPDF(f"{fonte.name}: o Typst falhou\n{erro}") from erro


def resumo_do_erro(log: str, linhas: int = 25) -> str:
    """As linhas de erro do LaTeX (`! ...`, `error: ...`) com contexto, ou o fim do log."""
    todas = log.splitlines()
    marcadas = [i for i, linha in enumerate(todas) if linha.startswith("!") or "error" in linha.lower()]
    if not marcadas:
        return "\n".join(todas[-linhas:])
    trecho: list[str] = []
    for i in marcadas[:5]:
        trecho += todas[i : i + 4]
    return "\n".join(trecho[:linhas])
