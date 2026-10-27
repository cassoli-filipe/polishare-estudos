# Polishare → estudos

Baixa as provas antigas de uma matéria do [Polishare](https://www.polishare.com.br), uma prova por
vez, para estudar com o Claude Code: mapa do que cai, simulados inéditos em PDF e correção da sua
resolução.

Os PDFs do Polishare ficam só no seu computador (`materias/`, fora do git) e são apagados sozinhos
depois da data da prova. Os mapas, simulados e o histórico de estudo ficam.

## Do que você precisa

- Uma conta **sua** no Polishare.
- Um Mac com [Homebrew](https://brew.sh) e o [Claude Code](https://claude.com/claude-code).
  No Linux funciona igual, instalando as mesmas ferramentas pelo gerenciador de pacotes. No Windows,
  use o WSL: os ganchos do projeto são comandos de shell.

## Instalação

1. Instale as ferramentas. O `uv` cuida do Python (3.11 ou mais novo), o `tectonic` compila os
   simulados em LaTeX e o `poppler` deixa o Claude ler PDFs longos em partes.

   ```bash
   brew install uv tectonic poppler
   ```

   Os ganchos usam o `jq`, que já vem no macOS recente. Se `jq --version` falhar, rode
   `brew install jq`.

2. Baixe o repositório e instale as dependências:

   ```bash
   git clone https://github.com/cassoli-filipe/polishare-estudos.git
   cd polishare-estudos
   uv sync
   ```

3. Crie o arquivo de credenciais:

   ```bash
   cp .env.example .env
   chmod 600 .env
   ```

   Abra o `.env` num editor e preencha `POLISHARE_EMAIL` e `POLISHARE_SENHA` com a sua conta. O
   `.env` não vai para o git. Não mande a sua senha para ninguém, nem para o Claude.

4. Confira se o login funciona:

   ```bash
   uv run polishare buscar PME3100
   ```

   Deve listar a disciplina com o código, o id e o nome que ela tem no Polishare. Se der erro de
   login, confira o `.env`.

## Abrindo no Claude Code

Abra a pasta `polishare-estudos` no Claude Code. Na primeira vez ele pergunta se você confia na
pasta: aceite. Sem isso, os dois ganchos de `.claude/settings.json` não rodam:

- ao abrir, `polishare limpar --quieto` apaga os PDFs de provas que já passaram;
- quando o Claude salva a fonte de um simulado, `polishare pdf` compila o PDF.

A primeira compilação LaTeX demora uns 2 a 3 minutos, porque o Tectonic baixa os pacotes. As
seguintes levam segundos.

## Estudando

Fale com o Claude em português. Um roteiro típico:

1. **"Vou estudar a P2 de PME3100, a prova é dia 28/10."** O Claude conta quantos arquivos há
   (`--simular`), mostra para você e baixa só aquela prova, com validade até o dia dela.
2. **`/mapa PME3100 P2`**: temas que mais caem, por ano, e os formatos de questão que se repetem.
3. **`/simulado PME3100 P2`**: uma prova inédita no estilo das antigas e o gabarito comentado, os
   dois em PDF, em `materias/<matéria>/estudo/simulados/`. Não abra o gabarito antes de terminar.
4. **`/corrigir`** com fotos da sua resolução anexadas: nota estimada por questão, onde errou e os
   temas fracos, que entram no próximo simulado.

Os mesmos comandos à mão:

```bash
uv run polishare buscar PME3100                              # acha a disciplina
uv run polishare baixar PME3100 --prova P2 --simular         # só conta, não baixa
uv run polishare baixar PME3100 --prova P2 --ate 2026-10-28  # baixa a P2; fica até 28/10
uv run polishare limpar                                      # mostra o que há no disco
uv run polishare pdf                                         # compila os simulados pendentes
```

Sem `--ate`, os PDFs valem 30 dias. Cada prova baixada ocupa poucos MB.

## Regras

- **Cada um usa a própria conta.** Não compartilhe o `.env`.
- **`materias/` não sai do seu computador.** São provas de outros alunos e professores: não ponha no
  git, no Drive nem em lugar público. Quem quiser o material baixa com a própria conta.
- **Não sobrecarregue o site.** Uma matéria por vez e o intervalo padrão entre requisições (2,5 s).
  A política do Polishare prevê suspensão para quem sobrecarrega o servidor. Se aparecer erro
  403 ou 429, espere antes de tentar de novo.
- As preferências de estudo ficam no `CLAUDE.md` (por exemplo, guardar só provas e não as
  resoluções de listas). Ajuste se quiser outra coisa.

## Atualizando

```bash
git pull
uv sync
```

## Estrutura

```
polishare/      extrator e CLI (buscar, baixar, limpar, pdf)
modelos/        modelos LaTeX do simulado e do gabarito
.claude/        skills /mapa, /simulado, /corrigir e os ganchos
tests/          testes sem rede (uv run pytest)
docs/           desenho do projeto
materias/       seu material baixado, mapas e simulados (fora do git)
```
