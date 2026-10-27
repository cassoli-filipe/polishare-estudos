---
name: mapa
description: Mapeia o que cai numa prova de uma matéria baixada do Polishare — temas por ano, formatos de questão recorrentes, o que está em alta e o que sumiu. Use quando o usuário perguntar "o que cai na P1 de X", pedir o mapa de uma prova, ou antes de gerar um simulado.
argument-hint: <código> <prova>   (ex.: PME3100 P1)
---

# Mapa de uma prova

Argumentos: `$ARGUMENTS` (código da matéria e prova: P1, P2, P3, PRec, PSub).

1. **Achar a matéria.** Procure `materias/<código> - */INDEX.md`. Se não existir, ou se não houver
   linhas da prova pedida (os PDFs podem ter expirado), pergunte a data da prova e sugira
   `uv run polishare baixar <código> --prova <prova> --ate <data>`. Não rode o download sem o
   usuário pedir.

2. **Escolher as provas.** Na seção `## Provas` do `INDEX.md`, pegue as linhas cuja subpasta é a
   prova pedida (sem diferenciar maiúsculas). Por padrão, use as **8 mais recentes** pela coluna
   Ano; as sem ano vão por último. Se o usuário pedir "todas", use todas. Reoferecimentos ("Reof")
   entram e são marcados como tal. Resoluções de prova em `## Resoluções` também valem.

3. **Ler.** Abra cada PDF com a ferramenta Read (PDFs longos, em partes com `pages`). Muitas provas
   são escaneadas ou manuscritas: leia como imagem. Para cada questão, anote:
   - tema e subtema (ex.: "Dinâmica do corpo rígido / Teorema do Momento Angular")
   - formato (cálculo, demonstração, conceitual, teste)
   - o que é pedido e o valor da questão, se aparecer
   - se a prova traz resolução

   Se um trecho estiver ilegível, registre isso em vez de adivinhar.

4. **Escrever** `materias/<pasta da matéria>/estudo/mapa-<prova>.md`:

   ```markdown
   # Mapa da <prova> — <código> <nome>

   Gerado em <data> a partir de <n> provas: <lista com caminho e ano de cada uma>.

   ## Temas por ano
   | Tema | 2026 | 2025 | ... | Total |
   (✓ onde caiu; uma linha por tema, do mais frequente ao menos)

   ## Formatos que se repetem
   - <padrão> — visto em <provas>

   ## Em alta, estáveis e sumidos
   ## Estrutura típica
   (número de questões, valores, duração, se for possível inferir)
   ## Limitações
   (provas ilegíveis, anos faltando)
   ```

   Cada afirmação deve poder ser conferida: cite a prova e a questão.

5. **Responder** com um resumo de 3 a 5 linhas (os temas que mais caem e o padrão mais forte) e o
   link para o arquivo.
