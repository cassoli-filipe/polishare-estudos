"""Leitura do HTML do Polishare. Funções puras: recebem texto, devolvem estruturas."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from bs4 import BeautifulSoup

# Lista de permissão: a única regra que decide o que o crawler segue. Qualquer outro href
# (favoritos, perfil, logout, configurações, troca de curso) é ignorado, porque alguns mexem
# na conta só de serem visitados.
_RE_PASTA = re.compile(r"^/?(?:index\.php)?\?id=([A-Za-z0-9]+)$")
_RE_ARQUIVO = re.compile(r"^/?file\.php\?id=([A-Za-z0-9]+)$")
_RE_EXTERNO = re.compile(r"^https?://", re.IGNORECASE)

Tipo = Literal["pasta", "arquivo", "link"]


@dataclass(frozen=True)
class Disciplina:
    id: str
    codigo: str
    nome: str


@dataclass(frozen=True)
class Item:
    tipo: Tipo
    nome: str
    alvo: str  # id, para pasta e arquivo; URL, para link externo


def classificar_href(href: str | None) -> tuple[Tipo, str] | None:
    href = (href or "").strip()
    if m := _RE_PASTA.match(href):
        return "pasta", m.group(1)
    if m := _RE_ARQUIVO.match(href):
        return "arquivo", m.group(1)
    if _RE_EXTERNO.match(href) and "polishare.com.br" not in href.lower():
        return "link", href
    return None


def _texto(texto: str) -> str:
    return " ".join(texto.split())


def parse_busca(html: str) -> list[Disciplina]:
    soup = BeautifulSoup(html, "html.parser")
    disciplinas = []
    for bloco in soup.select("div.resultado"):
        link, paragrafo = bloco.select_one("h3 a"), bloco.find("p")
        alvo = classificar_href(link.get("href")) if link else None
        if not alvo or alvo[0] != "pasta" or paragrafo is None:
            continue
        # O parágrafo começa com o código da disciplina, seguido das subpastas: "PME3100| Aulas | ..."
        codigo = _texto(paragrafo.get_text(" ")).split("|")[0].strip()
        disciplinas.append(Disciplina(alvo[1], codigo, _texto(link.get_text())))
    return disciplinas


def parse_pasta(html: str) -> list[Item]:
    soup = BeautifulSoup(html, "html.parser")
    itens = []
    for linha in soup.select("table tr"):
        celula = linha.find("td")
        if celula is None:  # cabeçalho
            continue
        # O tipo vem do href, não da coluna Descrição. A coluna Autor é ignorada.
        for link in celula.find_all("a", href=True):
            alvo, nome = classificar_href(link["href"]), _texto(link.get_text())
            if alvo and nome:
                itens.append(Item(alvo[0], nome, alvo[1]))
                break
    return itens


def esta_deslogado(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    return any((f.get("action") or "").startswith("login.php") for f in soup.find_all("form"))


def esta_logado(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    return any(a["href"].rstrip("/").endswith("logout.php") for a in soup.find_all("a", href=True))
