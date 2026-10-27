import pytest
import requests

from polishare.client import (
    Abortar,
    ArquivoGrande,
    Cliente,
    ErroPolishare,
    extensao,
    ler_credenciais,
)

LOGADO = '<a href="/logout.php">Sair</a><table></table>'
DESLOGADO = '<form action="login.php?&f=ExY" method="post"></form>'


class Resposta:
    def __init__(self, status=200, texto="", cabecalhos=None, blocos=None, erro_no_meio=None):
        self.status_code = status
        self.text = texto
        self.headers = cabecalhos or {"Content-Type": "text/html; charset=UTF-8"}
        self._blocos = blocos or []
        self._erro = erro_no_meio

    def iter_content(self, tamanho):
        yield from self._blocos
        if self._erro:
            raise self._erro

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def pdf(*blocos, cabecalhos=None):
    return Resposta(
        cabecalhos=cabecalhos or {"Content-Type": "application/pdf", "Content-Disposition": 'inline; filename="P1 - 2021.pdf'},
        blocos=list(blocos) or [b"%PDF-1.4"],
    )


class Sessao:
    """Devolve as respostas na ordem; uma exceção na fila é lançada no lugar da resposta."""

    def __init__(self, *respostas):
        self.fila = list(respostas)
        self.pedidos = []
        self.headers = {}

    def request(self, metodo, url, **opcoes):
        self.pedidos.append((metodo, url.removeprefix("https://www.polishare.com.br/"), opcoes))
        item = self.fila.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class Relogio:
    def __init__(self):
        self.agora = 0.0
        self.esperas = []

    def __call__(self):
        return self.agora

    def dormir(self, segundos):
        self.esperas.append(segundos)
        self.agora += segundos


def cliente(sessao, relogio=None, **opcoes):
    relogio = relogio or Relogio()
    return Cliente("eu@usp.br", "segredo", sessao=sessao, relogio=relogio, dormir=relogio.dormir, **opcoes)


def test_login_envia_credenciais_e_confere_logout():
    sessao = Sessao(Resposta(texto=LOGADO))
    cliente(sessao).login()
    metodo, caminho, opcoes = sessao.pedidos[0]
    assert (metodo, caminho) == ("POST", "login.php")
    assert opcoes["data"] == {"email": "eu@usp.br", "password": "segredo"}
    assert sessao.headers["User-Agent"].startswith("polishare-estudos/")


def test_login_recusado_aborta_sem_mostrar_a_senha():
    sessao = Sessao(Resposta(texto=DESLOGADO), Resposta(texto=DESLOGADO))
    with pytest.raises(Abortar) as erro:
        cliente(sessao).login()
    assert "segredo" not in str(erro.value)


def test_sessao_expirada_faz_login_de_novo_uma_vez():
    sessao = Sessao(Resposta(texto=DESLOGADO), Resposta(texto=LOGADO), Resposta(texto="<p>pasta</p>"))
    assert cliente(sessao).pagina("index.php?id=x") == "<p>pasta</p>"
    assert [p[1] for p in sessao.pedidos] == ["index.php?id=x", "login.php", "index.php?id=x"]


def test_sessao_que_cai_de_novo_aborta():
    sessao = Sessao(Resposta(texto=DESLOGADO), Resposta(texto=LOGADO), Resposta(texto=DESLOGADO))
    with pytest.raises(Abortar, match="sessão caiu"):
        cliente(sessao).pagina("index.php?id=x")


@pytest.mark.parametrize("status", [403, 429])
def test_403_e_429_abortam_na_hora(status):
    sessao = Sessao(Resposta(status=status))
    with pytest.raises(Abortar, match=str(status)):
        cliente(sessao).pagina("index.php?id=x")
    assert len(sessao.pedidos) == 1


def test_erro_de_servidor_tenta_de_novo_com_espera_crescente():
    relogio = Relogio()
    sessao = Sessao(Resposta(status=503), requests.Timeout(), Resposta(texto="ok"))
    assert cliente(sessao, relogio).pagina("index.php?id=x") == "ok"
    assert relogio.esperas == [10, 30]


def test_desiste_depois_de_quatro_tentativas():
    relogio = Relogio()
    sessao = Sessao(*[Resposta(status=500)] * 4)
    with pytest.raises(ErroPolishare, match="HTTP 500") as erro:
        cliente(sessao, relogio).pagina("index.php?id=x")
    assert not isinstance(erro.value, Abortar)
    assert relogio.esperas == [10, 30, 60]


def test_404_nao_tenta_de_novo():
    sessao = Sessao(Resposta(status=404))
    with pytest.raises(ErroPolishare, match="HTTP 404"):
        cliente(sessao).pagina("index.php?id=x")
    assert len(sessao.pedidos) == 1


def test_cinco_falhas_seguidas_abortam():
    c = cliente(Sessao(*[Resposta(status=404)] * 5))
    for _ in range(4):
        with pytest.raises(ErroPolishare) as erro:
            c.pagina("index.php?id=x")
        assert not isinstance(erro.value, Abortar)
    with pytest.raises(Abortar, match="5 falhas seguidas"):
        c.pagina("index.php?id=x")


def test_sucesso_zera_a_contagem_de_falhas():
    c = cliente(Sessao(*[Resposta(status=404)] * 4, Resposta(texto="ok"), Resposta(status=404)))
    for _ in range(4):
        with pytest.raises(ErroPolishare):
            c.pagina("index.php?id=x")
    c.pagina("index.php?id=x")
    with pytest.raises(ErroPolishare) as erro:
        c.pagina("index.php?id=x")
    assert not isinstance(erro.value, Abortar)


def test_respeita_o_intervalo_entre_requisicoes():
    relogio = Relogio()
    c = cliente(Sessao(Resposta(texto="1"), Resposta(texto="2"), Resposta(texto="3")), relogio, intervalo=2.5)
    c.pagina("a")
    relogio.agora += 1.0  # o programa gastou 1 s processando
    c.pagina("b")
    c.pagina("c")
    assert relogio.esperas == [1.5, 2.5]


def test_intervalo_abaixo_do_minimo_e_recusado():
    with pytest.raises(ValueError):
        cliente(Sessao(), intervalo=1.0)


def test_arquivo_grava_o_conteudo_e_descobre_a_extensao(tmp_path):
    destino = tmp_path / "x.part"
    baixado = cliente(Sessao(pdf(b"%PDF", b"-1.4"))).arquivo("n39m", destino)
    assert destino.read_bytes() == b"%PDF-1.4"
    assert (baixado.extensao, baixado.bytes) == (".pdf", 8)


def test_arquivo_com_sessao_expirada_faz_login_e_baixa(tmp_path):
    sessao = Sessao(Resposta(texto=DESLOGADO), Resposta(texto=LOGADO), pdf())
    cliente(sessao).arquivo("n39m", tmp_path / "x.part")
    assert [p[1] for p in sessao.pedidos] == ["file.php?id=n39m", "login.php", "file.php?id=n39m"]


def test_arquivo_que_vira_pagina_e_falha(tmp_path):
    with pytest.raises(ErroPolishare, match="página em vez do arquivo") as erro:
        cliente(Sessao(Resposta(texto="<p>removido</p>"))).arquivo("n39m", tmp_path / "x.part")
    assert not isinstance(erro.value, Abortar)


def test_arquivo_grande_demais(tmp_path):
    grande = pdf(cabecalhos={"Content-Type": "application/pdf", "Content-Length": str(200 * 2**20)})
    with pytest.raises(ArquivoGrande):
        cliente(Sessao(grande)).arquivo("n39m", tmp_path / "x.part")
    with pytest.raises(ArquivoGrande):
        cliente(Sessao(pdf(b"x" * 10, b"x" * 10))).arquivo("n39m", tmp_path / "y.part", limite=15)


def test_conexao_que_cai_no_meio_vira_falha(tmp_path):
    quebrada = pdf(b"%PDF")
    quebrada._erro = requests.exceptions.ChunkedEncodingError()
    with pytest.raises(ErroPolishare, match="caiu no meio"):
        cliente(Sessao(quebrada)).arquivo("n39m", tmp_path / "x.part")


@pytest.mark.parametrize(
    ("disposicao", "tipo", "esperado"),
    [
        ('inline; filename="P1 - 2021.pdf', "application/pdf", ".pdf"),
        ('attachment; filename="Lista.DOCX"', "application/octet-stream", ".docx"),
        ("attachment; filename*=UTF-8''Resolu%C3%A7%C3%A3o.zip", None, ".zip"),
        (None, "image/png", ".png"),
        (None, None, ".pdf"),
        ('inline; filename="sem extensao"', None, ".pdf"),
    ],
)
def test_extensao(disposicao, tipo, esperado):
    assert extensao(disposicao, tipo) == esperado


def test_ler_credenciais(tmp_path, monkeypatch):
    monkeypatch.delenv("POLISHARE_EMAIL", raising=False)
    monkeypatch.delenv("POLISHARE_SENHA", raising=False)
    env = tmp_path / ".env"
    env.write_text('# comentário\nPOLISHARE_EMAIL=eu@usp.br\nexport POLISHARE_SENHA="a=b"\n', encoding="utf-8")
    assert ler_credenciais(env) == ("eu@usp.br", "a=b")
    with pytest.raises(ErroPolishare, match="Faltam as credenciais"):
        ler_credenciais(tmp_path / "nao-existe")
