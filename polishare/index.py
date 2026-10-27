"""Gera o INDEX.md e o links.md de uma matéria a partir do manifest."""

from __future__ import annotations

import re

from .crawl import normalizar
from .store import Manifest, expira_em

_RE_ANO = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")
_SINAIS_DE_RESOLUCAO = ("resolu", "gabarito", "resolvid")
RAIZ = "(raiz)"


def ano(nome: str) -> str:
    m = _RE_ANO.search(nome)
    return m.group(1) if m else ""


def tem_resolucao(nome: str, pasta: list[str]) -> bool:
    texto = normalizar(nome)
    return any(s in texto for s in _SINAIS_DE_RESOLUCAO) or (bool(pasta) and normalizar(pasta[0]) == "resolucoes")


def _celula(texto: str) -> str:
    return texto.replace("|", "\\|")


def gerar_index(manifest: Manifest) -> str:
    d = manifest.disciplina
    presentes = manifest.presentes()
    removidos = len(manifest.arquivos) - len(presentes)
    resumo = f"{len(presentes)} arquivos no disco"
    if removidos:
        resumo += (
            f"; {removidos} já expiraram e foram apagados "
            f"(`uv run polishare baixar {d.codigo} --prova <P1, P2...>` traz de volta)"
        )
    if manifest.falhas:
        resumo += f"; {len(manifest.falhas)} com falha (ver o fim deste arquivo)"
    linhas = [
        f"# {d.codigo} - {d.nome}",
        "",
        f"Polishare: https://www.polishare.com.br/index.php?id={d.id}  ",
        f"Atualizado em {manifest.atualizado_em}. {resumo}.",
        "",
        "> As colunas **Ano** e **Resolução** são heurísticas tiradas do nome do arquivo. "
        '"?" quer dizer que o nome não diz; confira abrindo o arquivo. **Expira** é o último dia '
        "em que o PDF fica no disco; depois, `polishare limpar` apaga.",
        "",
    ]
    grupos: dict[str, list[dict]] = {}
    for registro in presentes.values():
        grupos.setdefault(registro["pasta"][0] if registro["pasta"] else RAIZ, []).append(registro)

    def ordem(registro: dict) -> tuple:
        return (" / ".join(registro["pasta"][1:]).lower(), -int(ano(registro["nome"]) or 0), registro["nome"])

    for grupo in sorted(grupos, key=lambda g: (g != RAIZ, normalizar(g))):
        linhas += [
            f"## {grupo}",
            "",
            "| Subpasta | Nome | Ano | Resolução | Expira | Arquivo |",
            "|---|---|---|---|---|---|",
        ]
        for r in sorted(grupos[grupo], key=ordem):
            subpasta = " / ".join(r["pasta"][1:]) or "—"
            resolucao = "sim" if tem_resolucao(r["nome"], r["pasta"]) else "?"
            arquivo = f"[{_celula(r['caminho'])}](<{r['caminho']}>)"
            linhas.append(
                f"| {_celula(subpasta)} | {_celula(r['nome'])} | {ano(r['nome'])} | {resolucao} "
                f"| {expira_em(r).isoformat()} | {arquivo} |"
            )
        linhas.append("")

    if manifest.falhas:
        linhas += ["## Falhas", "", "Tentadas de novo no próximo `polishare baixar`.", ""]
        for id_arquivo, f in sorted(manifest.falhas.items(), key=lambda par: par[1]["pasta"]):
            linhas.append(f"- {'/'.join([*f['pasta'], f['nome']])} (`{id_arquivo}`): {f['erro']}")
        linhas.append("")
    return "\n".join(linhas)


def gerar_links(manifest: Manifest) -> str:
    d = manifest.disciplina
    linhas = [f"# Links externos: {d.codigo} - {d.nome}", "", "Registrados, não visitados.", ""]
    for link in sorted(manifest.links, key=lambda l: (l["pasta"], l["nome"])):
        onde = "/".join(link["pasta"]) or RAIZ
        linhas.append(f"- **{onde}**: [{link['nome']}]({link['url']})")
    linhas.append("")
    return "\n".join(linhas)


def escrever_indices(manifest: Manifest) -> None:
    manifest.raiz.mkdir(parents=True, exist_ok=True)
    (manifest.raiz / "INDEX.md").write_text(gerar_index(manifest), encoding="utf-8")
    if manifest.links:
        (manifest.raiz / "links.md").write_text(gerar_links(manifest), encoding="utf-8")
