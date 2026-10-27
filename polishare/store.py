"""Caminhos, nomes de arquivo e o manifest de cada matéria."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path

from .parse import Disciplina

_INVALIDOS = re.compile(r'[/\\:*?"<>|\x00-\x1f]')
LIMITE_NOME = 120
PRAZO_PADRAO = timedelta(days=30)


def higienizar(nome: str) -> str:
    limpo = _INVALIDOS.sub("-", " ".join(nome.split())).strip(" .")
    return limpo[:LIMITE_NOME].rstrip(" .") or "sem nome"


def diretorio_relativo(pasta: tuple[str, ...] | list[str]) -> Path:
    return Path(*map(higienizar, pasta)) if pasta else Path()


def pasta_da_disciplina(destino: Path, disciplina: Disciplina) -> Path:
    return destino / higienizar(f"{disciplina.codigo} - {disciplina.nome}")


def agora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def expira_em(registro: dict) -> date:
    """Último dia em que o arquivo fica no disco. Registros antigos, sem data, valem 30 dias."""
    if valor := registro.get("expira_em"):
        return date.fromisoformat(valor)
    return datetime.fromisoformat(registro["baixado_em"]).date() + PRAZO_PADRAO


class Manifest:
    def __init__(self, raiz: Path, disciplina: Disciplina):
        self.raiz = raiz
        self.caminho = raiz / "manifest.json"
        dados = json.loads(self.caminho.read_text(encoding="utf-8")) if self.caminho.exists() else {}
        self.disciplina = disciplina
        self.atualizado_em: str | None = dados.get("atualizado_em")
        self.arquivos: dict[str, dict] = dados.get("arquivos", {})
        self.falhas: dict[str, dict] = dados.get("falhas", {})
        self.links: list[dict] = dados.get("links", [])

    @classmethod
    def abrir(cls, raiz: Path) -> Manifest:
        dados = json.loads((raiz / "manifest.json").read_text(encoding="utf-8"))
        return cls(raiz, Disciplina(**dados["disciplina"]))

    def presentes(self) -> dict[str, dict]:
        """Registros cujo arquivo não foi apagado pela expiração."""
        return {i: r for i, r in self.arquivos.items() if not r.get("removido_em")}

    def ja_baixado(self, id_arquivo: str) -> bool:
        registro = self.arquivos.get(id_arquivo)
        return registro is not None and (self.raiz / registro["caminho"]).exists()

    def destino_livre(self, pasta: tuple[str, ...], nome: str, extensao: str, id_arquivo: str) -> Path:
        """Caminho relativo à matéria. Se outro arquivo já ocupa o nome, acrescenta ` [id]`."""
        diretorio, base = diretorio_relativo(pasta), higienizar(nome)
        meu = self.arquivos.get(id_arquivo, {}).get("caminho")
        de_outros = {r["caminho"] for i, r in self.presentes().items() if i != id_arquivo}

        def ocupado(candidato: Path) -> bool:
            relativo = candidato.as_posix()
            return relativo != meu and (relativo in de_outros or (self.raiz / candidato).exists())

        candidato = diretorio / f"{base}{extensao}"
        return diretorio / f"{base} [{id_arquivo}]{extensao}" if ocupado(candidato) else candidato

    def registrar(
        self, id_arquivo: str, caminho: Path, pasta: tuple[str, ...], nome: str, tamanho: int, validade: date
    ) -> None:
        self.arquivos[id_arquivo] = {
            "caminho": caminho.as_posix(),
            "pasta": list(pasta),
            "nome": nome,
            "bytes": tamanho,
            "baixado_em": agora(),
            "expira_em": validade.isoformat(),
        }
        self.falhas.pop(id_arquivo, None)

    def renovar(self, id_arquivo: str, validade: date) -> None:
        self.arquivos[id_arquivo]["expira_em"] = validade.isoformat()

    def registrar_falha(self, id_arquivo: str, pasta: tuple[str, ...], nome: str, erro: str) -> None:
        self.falhas[id_arquivo] = {"pasta": list(pasta), "nome": nome, "erro": erro, "em": agora()}

    def adicionar_link(self, pasta: tuple[str, ...], nome: str, url: str) -> None:
        registro = {"pasta": list(pasta), "nome": nome, "url": url}
        if registro not in self.links:
            self.links.append(registro)

    def salvar(self) -> None:
        self.raiz.mkdir(parents=True, exist_ok=True)
        self.atualizado_em = agora()
        dados = {
            "disciplina": asdict(self.disciplina),
            "atualizado_em": self.atualizado_em,
            "arquivos": self.arquivos,
            "falhas": self.falhas,
            "links": self.links,
        }
        # Grava num temporário e troca de uma vez: um Ctrl+C no meio nunca deixa o manifest pela metade.
        descritor, temporario = tempfile.mkstemp(dir=self.raiz, prefix=".manifest-", suffix=".tmp")
        with os.fdopen(descritor, "w", encoding="utf-8") as saida:
            json.dump(dados, saida, ensure_ascii=False, indent=2)
        os.replace(temporario, self.caminho)
