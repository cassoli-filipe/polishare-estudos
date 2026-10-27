"""Linha de comando: `polishare buscar`, `baixar`, `limpar` e `pdf`."""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Protocol
from urllib.parse import quote

from .client import INTERVALO_MINIMO, INTERVALO_PADRAO, Abortar, Baixado, Cliente, ErroPolishare, ler_credenciais
from .crawl import ArquivoEncontrado, Escopo, LinkEncontrado, percorrer
from .index import escrever_indices
from .limpeza import limpar_materia, materias_em
from .parse import Disciplina, parse_busca
from .pdf import ErroPDF, compilar, desatualizado, fontes_de_simulados, markdown_em_simulados
from .store import PRAZO_PADRAO, Manifest, diretorio_relativo, expira_em, pasta_da_disciplina


class ClientePolishare(Protocol):
    def pagina(self, caminho: str) -> str: ...
    def arquivo(self, id_arquivo: str, destino: Path) -> Baixado: ...


@dataclass
class Resumo:
    novos: int = 0
    existentes: int = 0
    falhas: int = 0
    links: int = 0
    pastas: int = 0
    novos_por_pasta: Counter = field(default_factory=Counter)
    interrompido: str | None = None


def buscar(cliente: ClientePolishare, termo: str) -> list[Disciplina]:
    return parse_busca(cliente.pagina(f"index.php?pagina=pesquisa&t=d&q={quote(termo)}"))


def _tabela(disciplinas: list[Disciplina]) -> str:
    return "\n".join(f"  {d.codigo:<10} --id {d.id:<6} {d.nome}" for d in disciplinas)


def escolher_disciplina(disciplinas: list[Disciplina], codigo: str, id_disciplina: str | None) -> Disciplina:
    if id_disciplina:
        for d in disciplinas:
            if d.id == id_disciplina:
                return d
        raise ErroPolishare(f"Nenhum resultado da busca por {codigo} tem o id {id_disciplina}:\n{_tabela(disciplinas)}")
    exatas = [d for d in disciplinas if d.codigo.upper() == codigo.upper()]
    if len(exatas) == 1:
        return exatas[0]
    if exatas:
        raise ErroPolishare(f"Mais de uma disciplina com o código {codigo}. Escolha uma com --id:\n{_tabela(exatas)}")
    if disciplinas:
        raise ErroPolishare(f"Nenhuma disciplina com o código exato {codigo}. A busca achou:\n{_tabela(disciplinas)}")
    raise ErroPolishare(f"A busca por {codigo} não achou nada.")


def baixar(
    cliente: ClientePolishare,
    disciplina: Disciplina,
    destino: Path,
    escopo: Escopo = Escopo(),
    *,
    validade: date | None = None,
    renovar: bool = False,
    simular: bool = False,
    saida: Callable[[str], None] = print,
) -> Resumo:
    """`validade` é o último dia em que os arquivos novos ficam no disco (padrão: daqui a 30 dias).
    Com `renovar`, os já baixados que estão no escopo também passam a valer até essa data."""
    validade = validade or date.today() + PRAZO_PADRAO
    manifest = Manifest(pasta_da_disciplina(destino, disciplina), disciplina)
    resumo = Resumo()

    def ao_entrar(caminho: tuple[str, ...]) -> None:
        resumo.pastas += 1
        if caminho:
            saida(f"  pasta {'/'.join(caminho)}")

    try:
        for achado in percorrer(cliente.pagina, disciplina.id, escopo, ao_entrar=ao_entrar):
            if isinstance(achado, LinkEncontrado):
                manifest.adicionar_link(achado.pasta, achado.nome, achado.url)
                resumo.links += 1
            elif manifest.ja_baixado(achado.id):
                resumo.existentes += 1
                if renovar:
                    manifest.renovar(achado.id, validade)
            elif simular:
                resumo.novos += 1
                resumo.novos_por_pasta[achado.pasta[0] if achado.pasta else "(raiz)"] += 1
            else:
                _baixar_um(cliente, manifest, achado, validade, resumo, saida)
    except (Abortar, KeyboardInterrupt) as e:
        resumo.interrompido = str(e) or "Interrompido pelo usuário."
    finally:
        if not simular:
            manifest.salvar()
            escrever_indices(manifest)
    return resumo


def _baixar_um(
    cliente: ClientePolishare,
    manifest: Manifest,
    achado: ArquivoEncontrado,
    validade: date,
    resumo: Resumo,
    saida: Callable[[str], None],
) -> None:
    saida(f"[{resumo.novos + resumo.falhas + 1}] {'/'.join((*achado.pasta, achado.nome))}")
    diretorio = manifest.raiz / diretorio_relativo(achado.pasta)
    diretorio.mkdir(parents=True, exist_ok=True)
    parcial = diretorio / f".{achado.id}.part"
    try:
        baixado = cliente.arquivo(achado.id, parcial)
        relativo = manifest.destino_livre(achado.pasta, achado.nome, baixado.extensao, achado.id)
        parcial.replace(manifest.raiz / relativo)
        manifest.registrar(achado.id, relativo, achado.pasta, achado.nome, baixado.bytes, validade)
        resumo.novos += 1
    except Abortar:
        raise
    except ErroPolishare as erro:
        manifest.registrar_falha(achado.id, achado.pasta, achado.nome, str(erro))
        resumo.falhas += 1
        saida(f"    falhou: {erro}")
    finally:
        parcial.unlink(missing_ok=True)
        manifest.salvar()


def _intervalo(texto: str) -> float:
    valor = float(texto)
    if valor < INTERVALO_MINIMO:
        raise argparse.ArgumentTypeError(f"o mínimo é {INTERVALO_MINIMO} s")
    return valor


def _data(texto: str) -> date:
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            valor = datetime.strptime(texto, formato).date()
            break
        except ValueError:
            continue
    else:
        raise argparse.ArgumentTypeError("use AAAA-MM-DD ou DD/MM/AAAA")
    if valor < date.today():
        raise argparse.ArgumentTypeError("essa data já passou")
    return valor


def _duracao(segundos: float) -> str:
    minutos, segundos = divmod(int(segundos), 60)
    return f"{minutos} min {segundos:02d} s" if minutos else f"{segundos} s"


def _mb(tamanho: int) -> str:
    return f"{tamanho / 2**20:.1f} MB"


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    comum = argparse.ArgumentParser(add_help=False)
    comum.add_argument("--env", type=Path, default=Path(".env"), help="arquivo com as credenciais (padrão: .env)")
    destino = argparse.ArgumentParser(add_help=False)
    destino.add_argument("--destino", type=Path, default=Path("materias"), help="onde ficam as matérias (padrão: materias)")
    parser = argparse.ArgumentParser(prog="polishare", description="Baixa provas do Polishare para estudar.")
    comandos = parser.add_subparsers(dest="comando", required=True)

    p_buscar = comandos.add_parser("buscar", parents=[comum], help="procura disciplinas por código ou nome")
    p_buscar.add_argument("termo")

    p_baixar = comandos.add_parser(
        "baixar",
        parents=[comum, destino],
        help="baixa as provas de uma disciplina",
        description="Sem --prova nem --pastas, baixa só a pasta Provas.",
    )
    p_baixar.add_argument("codigo", help="código da disciplina, ex.: PME3100")
    p_baixar.add_argument("--id", dest="id_disciplina", help="escolhe entre disciplinas com o mesmo código")
    qual = p_baixar.add_mutually_exclusive_group()
    qual.add_argument("--prova", help="só esta prova (P1, P2, P3, PRec, PSub) e as resoluções que a citam")
    qual.add_argument("--pastas", help="estas pastas de primeiro nível, separadas por vírgula (ex.: Provas,Resumos)")
    p_baixar.add_argument("--ate", type=_data, help="data da prova: os PDFs ficam até esse dia (padrão: 30 dias)")
    p_baixar.add_argument("--simular", action="store_true", help="só percorre as pastas e conta; não baixa nada")
    p_baixar.add_argument("--intervalo", type=_intervalo, default=INTERVALO_PADRAO, help="segundos entre requisições (mínimo 2)")

    p_limpar = comandos.add_parser(
        "limpar", parents=[destino], help="apaga os PDFs vencidos; mantém INDEX.md, manifest e estudo/ (sem internet)"
    )
    p_limpar.add_argument("codigo", nargs="?", help="só esta disciplina")
    p_limpar.add_argument("--prova", help="só os arquivos desta prova")
    p_limpar.add_argument("--agora", action="store_true", help="apaga já, mesmo antes de vencer (exige o código)")
    p_limpar.add_argument("--quieto", action="store_true", help="só escreve algo se apagar arquivos")

    p_pdf = comandos.add_parser(
        "pdf",
        parents=[destino],
        help="compila simulados (.tex ou .typ) para PDF",
        description="Sem fontes, compila as de estudo/simulados/.fontes/ cujo PDF falta ou está velho.",
    )
    p_pdf.add_argument("fontes", nargs="*", type=Path, help="arquivos .tex ou .typ para compilar")
    p_pdf.add_argument("--todos", action="store_true", help="recompila todas as fontes, mesmo as em dia")
    return parser.parse_args(argv)


def _pdf(args: argparse.Namespace) -> int:
    fontes = args.fontes or [
        f for f in fontes_de_simulados(args.destino) if args.todos or desatualizado(f)
    ]
    falhas = 0
    for fonte in fontes:
        try:
            print(f"{fonte} → {compilar(fonte)}")
        except ErroPDF as erro:
            print(f"Erro: {erro}", file=sys.stderr)
            falhas += 1
    if not fontes and not args.fontes:
        print("Todos os simulados já estão em PDF e em dia.")
    for sobra in markdown_em_simulados(args.destino):
        print(f"Aviso: {sobra} é Markdown; simulados devem ser só PDF.", file=sys.stderr)
    return 2 if falhas else 0


def _limpar(args: argparse.Namespace) -> int:
    if args.agora and not args.codigo:
        print("Erro: --agora precisa do código da disciplina.", file=sys.stderr)
        return 2
    materias = [
        m for m in materias_em(args.destino) if not args.codigo or m.disciplina.codigo.upper() == args.codigo.upper()
    ]
    if args.codigo and not materias:
        print(f"Erro: {args.codigo} não foi baixada em {args.destino}.", file=sys.stderr)
        return 2
    for m in materias:
        nome = f"{m.disciplina.codigo} - {m.disciplina.nome}"
        if apagados := limpar_materia(m, date.today(), imediato=args.agora, prova=args.prova):
            print(f"{nome}: {len(apagados)} PDFs apagados ({_mb(sum(a.bytes for a in apagados))}). "
                  "Mapas, simulados e histórico em estudo/ continuam.")
        if args.quieto:
            continue
        presentes = list(m.presentes().values())
        if not presentes:
            print(f"{nome}: nenhum PDF no disco.")
            continue
        proximo = min(expira_em(r) for r in presentes)
        quantos = sum(1 for r in presentes if expira_em(r) == proximo)
        print(f"{nome}: {len(presentes)} PDFs no disco ({_mb(sum(r['bytes'] for r in presentes))}); "
              f"{quantos} ficam só até {proximo:%d/%m/%Y}.")
    if not materias and not args.quieto:
        print("Nenhuma matéria baixada.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)
    if args.comando == "limpar":
        return _limpar(args)
    if args.comando == "pdf":
        return _pdf(args)
    try:
        cliente = Cliente(*ler_credenciais(args.env), intervalo=getattr(args, "intervalo", INTERVALO_PADRAO))
        cliente.login()
        if args.comando == "buscar":
            disciplinas = buscar(cliente, args.termo)
            print(_tabela(disciplinas) if disciplinas else "Nada encontrado.")
            return 0
        disciplina = escolher_disciplina(buscar(cliente, args.codigo), args.codigo, args.id_disciplina)
        if args.prova:
            escopo = Escopo(prova=args.prova)
        elif args.pastas:
            escopo = Escopo(pastas=tuple(p.strip() for p in args.pastas.split(",") if p.strip()))
        else:
            escopo = Escopo(pastas=("Provas",))
        validade = args.ate or date.today() + PRAZO_PADRAO
        print(f"{disciplina.codigo} - {disciplina.nome} (id {disciplina.id})")
        inicio = time.monotonic()
        resumo = baixar(
            cliente, disciplina, args.destino, escopo, validade=validade, renovar=args.ate is not None, simular=args.simular
        )
    except ErroPolishare as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nInterrompido.", file=sys.stderr)
        return 130

    if args.simular:
        print(f"\nSimulação: {resumo.novos + resumo.existentes} arquivos em {resumo.pastas} pastas; "
              f"{resumo.novos} novos, {resumo.existentes} já baixados, {resumo.links} links externos. Nada foi baixado.")
        for pasta, quantidade in sorted(resumo.novos_por_pasta.items()):
            print(f"  {pasta}: {quantidade} novos")
        print(f"Baixar os novos deve levar uns {_duracao(resumo.novos * (args.intervalo + 1))}.")
    else:
        print(f"\nNovos: {resumo.novos} | já existiam: {resumo.existentes} | falhas: {resumo.falhas} | "
              f"links externos: {resumo.links} | tempo: {_duracao(time.monotonic() - inicio)}")
        print(f"Pasta: {pasta_da_disciplina(args.destino, disciplina)}")
        renovados = " (inclusive os que já estavam no disco)" if args.ate else ""
        print(f"Os PDFs novos{renovados} ficam até {validade:%d/%m/%Y}; depois, `polishare limpar` apaga.")
        if resumo.falhas:
            print("As falhas ficam no manifest.json e são tentadas de novo na próxima vez.")
    if resumo.interrompido:
        print(f"Parei antes do fim: {resumo.interrompido}", file=sys.stderr)
        print("Rode o mesmo comando de novo para continuar de onde parou.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
