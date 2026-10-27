---
name: simulado
description: Gera um simulado inédito no estilo das provas antigas de uma matéria baixada do Polishare, com gabarito comentado em arquivo separado. Use quando o usuário pedir um simulado, uma prova para treinar ou questões no estilo da P1/P2/P3.
argument-hint: <código> <prova> [número de questões]   (ex.: PME3100 P1 4)
---

# Simulado

Argumentos: `$ARGUMENTS`.

1. **Mapa.** Leia `materias/<pasta da matéria>/estudo/mapa-<prova>.md`. Se não existir, gere
   antes seguindo a skill `mapa`.

2. **Referência de estilo.** Leia 2 ou 3 das provas mais recentes **com resolução** (coluna
   Resolução do `INDEX.md`) para calibrar dificuldade, tamanho dos enunciados, notação e tempo.

3. **Pontos fracos.** Se `estudo/historico.md` existir, pelo menos um terço das questões deve
   cobrir os temas fracos mais recentes registrados lá. Diga ao usuário quais você priorizou.

4. **Montar as questões.** Quantidade: o argumento, ou o número típico de questões da prova real
   segundo o mapa. Cubra os temas mais frequentes e respeite os formatos recorrentes.
   - **Inéditas.** Mude geometria, valores, vínculos e contexto. Nunca copie um enunciado antigo.
   - **Resolvíveis.** Confira que cada questão tem solução única com os dados dados, resolvendo-a
     antes de escrever o enunciado final.
   - **Figuras.** Se a questão depende de figura (comum em Mecânica), desenhe-a em **TikZ** dentro
     do próprio `.tex`, numa `minipage` ao lado do enunciado, e descreva a geometria também em
     texto, para a questão ser resolvível sem a imagem. Se precisar de SVG, salve como
     `.fontes/<data>-<prova>-fig<n>.svg`: o `polishare pdf` converte para PDF e você inclui com
     `\includegraphics`.

5. **Gerar dois PDFs nativos em LaTeX.** O usuário exige PDF composto direto: **nunca** `.md`, nem
   `.md` convertido para PDF. Escreva as fontes em `materias/<pasta da matéria>/estudo/simulados/.fontes/`:
   - `<AAAA-MM-DD>-<prova>.tex` → `<AAAA-MM-DD>-<prova>.pdf`. A página 1 tem o cabeçalho (matéria,
     prova, "simulado não oficial", duração, sem calculadora) e as questões com o valor de cada item.
     O formulário vai na página 2. Não ponha respostas nem dicas.
   - `<AAAA-MM-DD>-<prova>-gabarito.tex` → `<AAAA-MM-DD>-<prova>-gabarito.pdf`. Para cada questão:
     a resolução passo a passo, as respostas em `\res{}` (caixa), a tabela `\criterios{}` por item
     (usada pelo `/corrigir`) e `\inspirada{}` com as provas e questões antigas.

   **Parta dos modelos** `modelos/simulado.tex` e `modelos/gabarito.tex`, na raiz do projeto: copie
   o preâmbulo e troque as questões. Eles têm a notação da Poli (`\vi`, `\vj`, `\vk`, `\vec`,
   `\wedge`), `\questao`, a lista `itens` com `\pts{}` e as figuras TikZ de referência. Não edite os
   modelos para fazer um simulado.

   Ao salvar cada fonte, o gancho do projeto compila sozinho. Se o LaTeX falhar, o erro volta
   para você: corrija a fonte, e o gancho compila de novo. Salve os SVGs **antes** do `.tex` que os
   inclui. Sem o gancho (por exemplo, numa sessão aberta antes dele existir), rode a partir da raiz
   do projeto:
   - `uv run polishare pdf <fonte.tex>` compila uma fonte.
   - `uv run polishare pdf` compila todas as desatualizadas.

   O motor é o Tectonic. Os auxiliares não ficam na pasta, e em `simulados/` só entram PDFs.

   **Confira cada página antes de entregar.** Rode `pdftoppm -r 80 -png X.pdf "$TMPDIR/p"` e leia as
   imagens. Nada pode sair cortado nem sobreposto (rótulos das figuras!), e a prova inteira tem que
   caber na página 1.

   Se já existir um simulado com o mesmo nome, acrescente `-2`, `-3`...

6. **Responder** com o link do PDF do simulado, a duração sugerida e um aviso para não abrir o
   gabarito antes de terminar. Não mostre as questões nem as respostas na conversa.
