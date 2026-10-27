"""Sessão HTTP com o Polishare: login, ritmo entre requisições, retentativas e parada."""

from __future__ import annotations

import mimetypes
import os
import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import requests

from .parse import esta_deslogado, esta_logado

BASE = "https://www.polishare.com.br/"
USER_AGENT = "polishare-estudos/0.1 (uso pessoal)"
INTERVALO_PADRAO = 2.5
INTERVALO_MINIMO = 2.0
ESPERAS_RETENTATIVA = (10, 30, 60)
MAX_FALHAS_SEGUIDAS = 5
LIMITE_ARQUIVO = 100 * 1024 * 1024
TIMEOUT = 60


class ErroPolishare(Exception):
    """Algo falhou; quem chamou decide se segue para o próximo arquivo."""


class Abortar(ErroPolishare):
    """O servidor está recusando ou a sessão não se sustenta: parar a execução inteira."""


class ArquivoGrande(ErroPolishare):
    pass


@dataclass(frozen=True)
class Baixado:
    extensao: str
    bytes: int


def ler_credenciais(caminho: Path = Path(".env")) -> tuple[str, str]:
    valores = {}
    if caminho.exists():
        for linha in caminho.read_text(encoding="utf-8").splitlines():
            linha = linha.strip().removeprefix("export ").strip()
            if linha and not linha.startswith("#") and "=" in linha:
                chave, valor = linha.split("=", 1)
                valores[chave.strip()] = valor.strip().strip("'\"")
    email = os.environ.get("POLISHARE_EMAIL") or valores.get("POLISHARE_EMAIL")
    senha = os.environ.get("POLISHARE_SENHA") or valores.get("POLISHARE_SENHA")
    if not email or not senha:
        raise ErroPolishare(
            f"Faltam as credenciais. Crie {caminho} com as linhas\n"
            "  POLISHARE_EMAIL=seu@email\n"
            "  POLISHARE_SENHA=sua-senha\n"
            "e rode `chmod 600 .env`."
        )
    return email, senha


_RE_FILENAME = re.compile(r"""filename\*?=(?:UTF-8'')?["']?([^"';\r\n]+)""", re.IGNORECASE)


def extensao(content_disposition: str | None, content_type: str | None) -> str:
    # O site às vezes manda o filename sem fechar as aspas: inline; filename="P1 - 2021.pdf
    if content_disposition and (m := _RE_FILENAME.search(content_disposition)):
        sufixo = Path(m.group(1).strip()).suffix.lower()
        if re.fullmatch(r"\.[a-z0-9]{1,5}", sufixo):
            return sufixo
    tipo = (content_type or "").split(";")[0].strip().lower()
    return (mimetypes.guess_extension(tipo) if tipo else None) or ".pdf"


class Cliente:
    def __init__(
        self,
        email: str,
        senha: str,
        *,
        intervalo: float = INTERVALO_PADRAO,
        sessao: requests.Session | None = None,
        relogio: Callable[[], float] = time.monotonic,
        dormir: Callable[[float], None] = time.sleep,
        esperas: Sequence[float] = ESPERAS_RETENTATIVA,
    ):
        if intervalo < INTERVALO_MINIMO:
            raise ValueError(f"O intervalo mínimo entre requisições é {INTERVALO_MINIMO} s.")
        self._email, self._senha = email, senha
        self.intervalo = intervalo
        self.sessao = sessao if sessao is not None else requests.Session()
        self.sessao.headers["User-Agent"] = USER_AGENT
        self._relogio, self._dormir, self._esperas = relogio, dormir, tuple(esperas)
        self._ultima: float | None = None
        self._falhas_seguidas = 0

    def login(self) -> None:
        resposta = self._requisitar("POST", "login.php", data={"email": self._email, "password": self._senha})
        if esta_logado(resposta.text) or esta_logado(self._requisitar("GET", "index.php").text):
            return
        raise Abortar("O Polishare recusou o login. Confira POLISHARE_EMAIL e POLISHARE_SENHA no .env.")

    def pagina(self, caminho: str) -> str:
        html = self._requisitar("GET", caminho).text
        if esta_deslogado(html):
            self.login()
            html = self._requisitar("GET", caminho).text
            if esta_deslogado(html):
                raise Abortar("A sessão caiu de novo logo depois do login. Parei; tente mais tarde.")
        return html

    def arquivo(self, id_arquivo: str, destino: Path, limite: int = LIMITE_ARQUIVO) -> Baixado:
        caminho = f"file.php?id={id_arquivo}"
        for tentativa in (1, 2):
            resposta = self._requisitar("GET", caminho, stream=True)
            with resposta:
                tipo = resposta.headers.get("Content-Type", "")
                if tipo.startswith("text/html"):
                    # Deslogado, o file.php devolve a página de login em vez do arquivo.
                    if not esta_deslogado(resposta.text):
                        self._contar_falha()
                        raise ErroPolishare(f"{caminho}: veio uma página em vez do arquivo")
                    if tentativa == 2:
                        raise Abortar("A sessão caiu de novo logo depois do login. Parei; tente mais tarde.")
                    self.login()
                    continue
                if _inteiro(resposta.headers.get("Content-Length")) > limite:
                    raise ArquivoGrande(f"{caminho}: maior que {limite // 2**20} MB")
                total = 0
                try:
                    with destino.open("wb") as saida:
                        for bloco in resposta.iter_content(64 * 1024):
                            total += len(bloco)
                            if total > limite:
                                raise ArquivoGrande(f"{caminho}: maior que {limite // 2**20} MB")
                            saida.write(bloco)
                except requests.RequestException as erro:
                    self._contar_falha()
                    raise ErroPolishare(f"{caminho}: a conexão caiu no meio do download ({type(erro).__name__})") from erro
                finally:
                    # O intervalo conta a partir do fim do download, não do começo.
                    self._ultima = self._relogio()
                return Baixado(extensao(resposta.headers.get("Content-Disposition"), tipo), total)
        raise AssertionError("inalcançável")

    def _requisitar(self, metodo: str, caminho: str, **opcoes) -> requests.Response:
        erro = ""
        for espera in (*self._esperas, None):
            self._aguardar_vez()
            try:
                resposta = self.sessao.request(metodo, urljoin(BASE, caminho), timeout=TIMEOUT, **opcoes)
            except (requests.ConnectionError, requests.Timeout) as e:
                erro = type(e).__name__
            else:
                if resposta.status_code in (403, 429):
                    resposta.close()
                    raise Abortar(
                        f"O Polishare respondeu {resposta.status_code} em {caminho}. "
                        "Parei para não forçar o servidor; tente mais tarde."
                    )
                if resposta.status_code < 400:
                    self._falhas_seguidas = 0
                    return resposta
                resposta.close()
                erro = f"HTTP {resposta.status_code}"
                if resposta.status_code < 500:
                    break  # 4xx não melhora tentando de novo
            if espera is not None:
                self._dormir(espera)
        self._contar_falha()
        raise ErroPolishare(f"{caminho}: {erro}")

    def _aguardar_vez(self) -> None:
        if self._ultima is not None:
            falta = self.intervalo - (self._relogio() - self._ultima)
            if falta > 0:
                self._dormir(falta)
        self._ultima = self._relogio()

    def _contar_falha(self) -> None:
        self._falhas_seguidas += 1
        if self._falhas_seguidas >= MAX_FALHAS_SEGUIDAS:
            raise Abortar(f"{MAX_FALHAS_SEGUIDAS} falhas seguidas. Parei para não forçar o servidor; tente mais tarde.")


def _inteiro(texto: str | None) -> int:
    try:
        return int(texto or 0)
    except ValueError:
        return 0
