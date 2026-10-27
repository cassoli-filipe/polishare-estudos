"""Percorre a árvore de pastas de uma matéria."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from .client import ErroPolishare
from .parse import parse_pasta

PROFUNDIDADE_MAXIMA = 6


@dataclass(frozen=True)
class ArquivoEncontrado:
    id: str
    nome: str
    pasta: tuple[str, ...]


@dataclass(frozen=True)
class LinkEncontrado:
    nome: str
    url: str
    pasta: tuple[str, ...]


@dataclass(frozen=True)
class Escopo:
    """O que percorrer. Sem nada, a matéria inteira.

    `pastas`: só essas pastas de primeiro nível. `prova` (ex.: "P1"): só `Provas/<prova>` e, em
    `Resoluções`, os arquivos que citam a prova no nome. Nos dois casos, o que está solto na raiz
    fica de fora.
    """

    pastas: tuple[str, ...] | None = None
    prova: str | None = None


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().split())


def cita_prova(nome: str, prova: str) -> bool:
    texto, alvo = normalizar(nome), normalizar(prova)
    formas = [alvo]
    if m := re.fullmatch(r"p([1-9])", alvo):
        formas.append(f"prova {m.group(1)}")
    return any(re.search(rf"(?<![a-z0-9]){re.escape(f)}(?![a-z0-9])", texto) for f in formas)


def pertence_a_prova(pasta: tuple[str, ...] | list[str], nome: str, prova: str) -> bool:
    if not pasta:
        return False
    topo = normalizar(pasta[0])
    if topo == "provas":
        return normalizar(pasta[1]) == normalizar(prova) if len(pasta) > 1 else cita_prova(nome, prova)
    return topo == "resolucoes" and cita_prova(nome, prova)


def percorrer(
    pagina: Callable[[str], str],
    id_raiz: str,
    escopo: Escopo = Escopo(),
    *,
    ao_entrar: Callable[[tuple[str, ...]], None] | None = None,
    profundidade_maxima: int = PROFUNDIDADE_MAXIMA,
) -> Iterator[ArquivoEncontrado | LinkEncontrado]:
    pedidas = {normalizar(p): p for p in escopo.pastas} if escopo.pastas else None
    filtrado = escopo.prova is not None or pedidas is not None
    visitadas: set[str] = set()

    def entrar(caminho: tuple[str, ...]) -> bool:
        topo = normalizar(caminho[0])
        if escopo.prova:
            if topo == "provas":
                return len(caminho) < 2 or normalizar(caminho[1]) == normalizar(escopo.prova)
            return topo == "resolucoes"
        return pedidas is None or topo in pedidas

    def aceitar(arquivo: ArquivoEncontrado) -> bool:
        if escopo.prova:
            return pertence_a_prova(arquivo.pasta, arquivo.nome, escopo.prova)
        return bool(arquivo.pasta) or not filtrado

    def conferir_pedido(caminho: tuple[str, ...], itens: list) -> None:
        subpastas = {normalizar(i.nome): i.nome for i in itens if i.tipo == "pasta"}
        if not caminho and pedidas is not None:
            if faltando := [p for chave, p in pedidas.items() if chave not in subpastas]:
                raise ErroPolishare(
                    f"Pasta não encontrada: {', '.join(faltando)}. "
                    f"Pastas desta matéria: {', '.join(subpastas.values())}."
                )
        elif not caminho and escopo.prova and "provas" not in subpastas:
            raise ErroPolishare(f"Esta matéria não tem a pasta Provas. Pastas: {', '.join(subpastas.values())}.")
        elif caminho and normalizar(caminho[0]) == "provas" and len(caminho) == 1 and escopo.prova:
            soltos = any(i.tipo == "arquivo" and cita_prova(i.nome, escopo.prova) for i in itens)
            if normalizar(escopo.prova) not in subpastas and not soltos:
                raise ErroPolishare(
                    f"Prova {escopo.prova} não encontrada. Provas desta matéria: {', '.join(subpastas.values())}."
                )

    def visitar(id_pasta: str, caminho: tuple[str, ...]) -> Iterator[ArquivoEncontrado | LinkEncontrado]:
        if id_pasta in visitadas or len(caminho) > profundidade_maxima:
            return
        visitadas.add(id_pasta)
        if ao_entrar:
            ao_entrar(caminho)
        itens = parse_pasta(pagina(f"index.php?id={id_pasta}"))
        conferir_pedido(caminho, itens)
        for item in itens:
            if item.tipo == "pasta":
                filho = (*caminho, item.nome)
                if entrar(filho):
                    yield from visitar(item.alvo, filho)
            elif item.tipo == "arquivo":
                arquivo = ArquivoEncontrado(item.alvo, item.nome, caminho)
                if aceitar(arquivo):
                    yield arquivo
            elif not escopo.prova and (caminho or not filtrado):
                yield LinkEncontrado(item.nome, item.alvo, caminho)

    yield from visitar(id_raiz, ())
