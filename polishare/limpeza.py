"""Apaga os PDFs vencidos. Mantém manifest, INDEX.md e tudo em `estudo/`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .crawl import pertence_a_prova
from .index import escrever_indices
from .store import Manifest, agora, expira_em


@dataclass(frozen=True)
class Apagado:
    caminho: str
    bytes: int


def materias_em(destino: Path) -> list[Manifest]:
    return [Manifest.abrir(m.parent) for m in sorted(destino.glob("*/manifest.json"))]


def limpar_materia(manifest: Manifest, hoje: date, *, imediato: bool = False, prova: str | None = None) -> list[Apagado]:
    """Apaga os arquivos vencidos (ou todos, com `imediato`), opcionalmente só os de uma prova."""
    apagados = []
    for registro in manifest.presentes().values():
        if prova and not pertence_a_prova(registro["pasta"], registro["nome"], prova):
            continue
        if not imediato and hoje <= expira_em(registro):
            continue
        arquivo = manifest.raiz / registro["caminho"]
        tamanho = arquivo.stat().st_size if arquivo.exists() else 0
        arquivo.unlink(missing_ok=True)
        registro["removido_em"] = agora()
        apagados.append(Apagado(registro["caminho"], tamanho))
        _remover_pastas_vazias(arquivo.parent, manifest.raiz)
    if apagados:
        manifest.salvar()
        escrever_indices(manifest)
    return apagados


def _remover_pastas_vazias(pasta: Path, raiz: Path) -> None:
    while pasta != raiz and pasta.is_relative_to(raiz) and pasta.is_dir():
        if any(p.name != ".DS_Store" for p in pasta.iterdir()):
            return
        (pasta / ".DS_Store").unlink(missing_ok=True)
        pasta.rmdir()
        pasta = pasta.parent
