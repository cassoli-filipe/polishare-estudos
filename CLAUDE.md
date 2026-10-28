# Polishare → estudos

Material do Polishare (provas antigas, resoluções, listas, resumos), baixado por matéria, para
estudar com o Claude Code. Desenho completo em
`docs/superpowers/specs/2026-10-27-polishare-estudos-design.md`.

## Organização

```
materias/<CÓDIGO> - <Nome>/
├── INDEX.md          # todos os arquivos: pasta, nome, ano, se tem resolução, caminho
├── links.md          # links externos (Responde Aí), só registrados
├── manifest.json     # controle do extrator; não editar à mão
├── Provas/P1/...     # espelho das pastas do Polishare
└── estudo/
    ├── mapa-<prova>.md
    ├── simulados/    # só PDF nativo; fontes LaTeX em simulados/.fontes/; nunca .md
    └── historico.md  # notas e temas fracos, escrito pelo /corrigir
```

O nome da matéria segue o Polishare, que às vezes difere do Júpiter: PME3100 aparece como
"Mecânica I", e a antiga "Mecânica A" é a PME2100.

## Estudando

- Comece sempre pelo `INDEX.md` da matéria. Só abra os PDFs de que precisa.
- Cite de que arquivo veio cada fato ou questão (ex.: `Provas/P1/2019.pdf`, questão 2).
- Muitas provas são escaneadas ou manuscritas: leia o PDF como imagem. Se um trecho estiver
  ilegível, diga, em vez de adivinhar.
- PDFs com mais de 10 páginas (em PME3100, quase só os de `Resoluções/`) precisam ser lidos em
  partes com `pages`, o que exige o poppler (`brew install poppler`).
- As colunas Ano e Resolução do `INDEX.md` são estimativas tiradas do nome do arquivo. Muitas
  provas marcadas "?" trazem a resolução nas últimas páginas (ex.: `Provas/P1/P1 2025.pdf`).
- Comandos: `/mapa <código> <prova>`, `/simulado <código> <prova> [n]`, `/corrigir <arquivo>`.
- Responda em português.

## Baixando

```bash
uv run polishare buscar PME3100
uv run polishare baixar PME3100 --prova P2 --simular         # só conta, não baixa
uv run polishare baixar PME3100 --prova P2 --ate 2026-11-24  # a P2 fica no disco até 24/11
uv run polishare limpar                                      # mostra o que há e apaga o que venceu
uv run polishare limpar PME3100 --prova P1 --agora           # apaga a P1 já
```

**Uma prova por vez, com validade.** Quando o usuário for estudar uma prova, pergunte a data dela e
baixe com `--prova <P> --ate <data>`. Sem `--ate`, os PDFs valem 30 dias. Rodar de novo com outro
`--ate` muda a validade do que já está no disco. Cada PDF mostra a validade na coluna Expira do
`INDEX.md`. Ao abrir o Claude Code neste projeto, um hook (`.claude/settings.json`) roda
`polishare limpar --quieto` e apaga os vencidos. `estudo/` (mapas, simulados, histórico) nunca é
apagado, e `baixar` traz de volta o que expirou. O `limpar` não usa a internet.

O usuário quer **só provas** no disco. Resoluções de listas e exercícios escaneados não ajudam no
estudo e ocupam a maior parte do espaço. Não baixe `Resoluções`, `Listas`, `Aulas` etc. sem um
pedido explícito. Em PME3100, as únicas resoluções mantidas são as de prova (`Resoluções/P1 2023
Resolução passo a passo.pdf` e `Resoluções/Q1 2024.pdf`).

Regras:

1. Nunca rode `polishare baixar` sem o usuário pedir, e nunca para mais de uma matéria por vez.
   O site é pequeno, e a política de publicação (cláusula 9) prevê suspensão de conta para quem
   sobrecarrega o servidor.
2. Rode `--simular` antes do primeiro download de uma matéria e mostre a contagem ao usuário.
3. Não baixe o intervalo abaixo do padrão (2,5 s). Se o extrator parar com 403/429, não tente de novo
   na mesma hora.
4. As credenciais ficam no `.env`. Nunca leia, mostre ou peça o conteúdo dele.
5. `materias/` é material de outros alunos e professores: não vai para o git nem para lugar público.

## Simulados em PDF

Simulados e gabaritos saem **sempre** em PDF composto direto de LaTeX (o usuário não aceita `.md`,
nem `.md` convertido para PDF).

```bash
uv run polishare pdf                                  # compila todas as fontes desatualizadas
uv run polishare pdf "materias/<matéria>/estudo/simulados/.fontes/<arquivo>.tex"
uv run polishare pdf --todos                          # recompila tudo
```

- O motor é o Tectonic (`brew install tectonic`), que baixa os pacotes LaTeX na primeira vez (uns 2
  min) e depois usa o cache. Se ele não estiver instalado, o comando usa `latexmk` ou `pdflatex`.
  Fontes `.typ` (Typst) também compilam.
- Figuras em TikZ dentro do `.tex`, com o kit de estilos do preâmbulo dos modelos. Os SVGs em
  `.fontes/` são convertidos para PDF automaticamente.
- Os modelos ficam em `modelos/simulado.tex` e `modelos/gabarito.tex`, fora de `materias/` para irem
  junto com o repositório. Eles trazem o visual (Palatino, cabeçalho da Poli, formulário) e
  marcadores `\marcador{...}` no lugar das questões, para nenhum simulado herdar questões prontas. O
  brasão é `modelos/poli.png`, achado pelo caminho relativo a partir de `.fontes/`; sem ele, o
  cabeçalho sai só com texto. Testes conferem que os modelos compilam com e sem o brasão.
- O `polishare pdf` avisa se encontrar `.md` em `simulados/`.
- Um gancho `PostToolUse` (`.claude/settings.json`) roda `polishare pdf` sempre que o Claude salva
  um `.tex`, `.typ` ou `.svg` em `simulados/.fontes/`. Se o LaTeX falhar, o erro volta para o Claude
  corrigir na hora. O gancho acha a raiz do projeto pelo caminho da fonte (o que vem antes de
  `/materias/`).

## Desenvolvimento

- `uv run pytest`: testes sem rede, contra páginas reais salvas em `tests/fixtures/` (sem nomes
  de autores nem do usuário).
- Todo o HTML é lido em `polishare/parse.py`. Se o site mudar, comece por lá e pelas fixtures.
- O crawler só segue `index.php?id=` e `file.php?id=` (`classificar_href`). Os links de favoritos
  alteram a conta só de serem visitados: não afrouxe essa regra.
