---
name: simulado
description: Gera um simulado inédito no estilo das provas antigas de uma matéria baixada do Polishare, com gabarito comentado em arquivo separado. Use quando o usuário pedir um simulado, uma prova para treinar ou questões no estilo da P1/P2/P3.
argument-hint: <código> <prova> [número de questões]   (ex.: PME3100 P1 4)
---

# Simulado

Argumentos: `$ARGUMENTS`.

O padrão é um simulado que um professor da Poli assinaria: questões com contexto e figura de verdade,
uma armadilha planejada em cada uma, respostas conferidas por dois caminhos e uma resolução que
ensina. Entre ocupar menos páginas e ficar claro, fique com o claro.

1. **Mapa.** Leia `materias/<pasta da matéria>/estudo/mapa-<prova>.md`. Se não existir, gere
   antes seguindo a skill `mapa`.

2. **Referência de estilo.** Leia 2 ou 3 das provas mais recentes **com resolução** (coluna
   Resolução do `INDEX.md`) para calibrar dificuldade, tamanho dos enunciados, notação, tempo e o
   formulário do caderno de respostas.

3. **Pontos fracos.** Se `estudo/historico.md` existir, pelo menos um terço das questões deve
   cobrir os temas fracos mais recentes registrados lá. Diga ao usuário quais você priorizou.

4. **Formato.** O número de questões, os valores e a duração são os da prova real, pela seção
   "Estrutura típica" do mapa (em PME3100, 3 questões e 120 min). O número de questões passado como
   argumento vale mais que o mapa. Os itens e os valores deles seguem os formatos recorrentes do
   mapa.

5. **Planejar cada questão antes de escrever.** Para cada uma, decida:
   - **Tema e formato**, do mapa: os mais frequentes primeiro, com os temas em alta e os fracos do
     histórico.
   - **Um contexto físico concreto**: turbina eólica, montanha-russa, braço de robô, trem de pouso,
     guindaste. Nada de "um ponto P" ou "um disco" soltos. O contexto serve à figura e ao
     enunciado e não muda a física.
   - **Uma armadilha planejada**, tirada dos "Formatos que se repetem" do mapa ou dos erros
     clássicos do tema. Em cinemática:
     - θ̈ ≠ 0 na lei horária;
     - α ≠ 0 no disco que rola;
     - aceleração do ponto de contato diferente de zero;
     - ω̇_arr ≠ 0;
     - a translação da origem no arrastamento;
     - Coriolis que se anula por paralelismo.

     A armadilha tem que ser justa: quem sabe a matéria acerta.
   - **Uma variação que nunca caiu**, em pelo menos uma questão e dentro da matéria (ex.:
     ω̇_arr ≠ 0, quando as provas só usaram ω_arr constante).
   - **Um item que separa quem entendeu**: conceitual ou de verificação, como "recalcule pelo
     campo de acelerações e confirme o item c", "o movimento é acelerado ou retardado?" ou
     "classifique o ato de movimento".
   - **Números que fecham sem calculadora**: 30°, 45°, 60°, triângulo 3-4-5, versores exatos.
   - **Inédita.** Mude geometria, valores, vínculos e contexto. Nunca copie um enunciado antigo,
     nem os exemplos dos modelos, nem as questões de simulados anteriores em `estudo/simulados/`.

6. **Resolver e conferir antes de escrever.** Resolva cada questão por inteiro e confira cada
   resposta por um caminho independente:
   - outro método à mão: outro polo, a propriedade das projeções, o campo de acelerações contra a
     composição de movimentos;
   - **e** um script SymPy no scratchpad: `uv run --with sympy python -I <script>`.

   Uma discordância é erro: ache antes de seguir. Confira também que os dados bastam (solução
   única) e que nenhum dado sobra, a não ser um distrator de propósito.

7. **Escrever dois PDFs nativos em LaTeX.** O usuário exige PDF composto direto: **nunca** `.md`,
   nem `.md` convertido para PDF. As fontes ficam em
   `materias/<pasta da matéria>/estudo/simulados/.fontes/`:
   - `<AAAA-MM-DD>-<prova>.tex` gera `<AAAA-MM-DD>-<prova>.pdf`;
   - `<AAAA-MM-DD>-<prova>-gabarito.tex` gera `<AAAA-MM-DD>-<prova>-gabarito.pdf`.

   **Parta dos modelos** `modelos/simulado.tex` e `modelos/gabarito.tex`, na raiz do projeto:
   - Copie o arquivo inteiro e ajuste `\materia`, `\prova`, `\ano` e `\duracao`.
   - Escreva no lugar dos marcadores `\marcador{...}`. No arquivo final não sobra nenhum.
   - O mostruário de figura dos modelos só demonstra o kit TikZ: não o aproveite.
   - Não edite os modelos para fazer um simulado.
   - O cabeçalho com o brasão (`modelos/poli.png`) já vem pronto.

   **Simulado:**
   - Abra cada questão com `\questao{n}{valor}` e marque o valor de cada item com `\pts{}`.
   - Na questão com figura, ponha a figura numa `minipage` de cerca de 40% da largura, ao lado do
     texto, e use `\tituloquestao` dentro da `minipage` do texto, como no modelo.
   - Use o espaço que precisar: as questões ocupam de 1 a 3 páginas. A figura nunca vira
     miniatura: cotas e rótulos têm que ser legíveis. Prefira quebrar a página entre questões a
     espremer.
   - **Figuras** em TikZ com o kit do preâmbulo:
     - estilos `corpo`, `barra`, `articulacao`, `ponto`, `vetor`, `cota`, `auxiliar`;
     - `\piso`, `\parede` e `\giro`;
     - `cavaleira` com `\pic{eixos3d}` para o 3D.

     Ponha hachura no que é fixo, cotas com as dimensões do enunciado, a base desenhada e o nome de
     todo ponto citado. Descreva a geometria também em texto, para a questão ser resolvível sem a
     imagem. Se precisar de SVG, salve como `.fontes/<data>-<prova>-fig<n>.svg`: o `polishare pdf`
     converte para PDF, e você inclui com `\includegraphics`.
   - **Formulário** em página própria, equivalente ao do caderno de respostas da prova real. O do
     modelo é o da P2 de PME3100. Para outra prova, monte um com o que o mapa mostra cair, sem
     entregar resposta.
   - Nenhuma resposta ou dica.

   **Gabarito, uma resolução que ensina:**
   - No topo, a linha de critério com o critério de desconto real, tirado do mapa.
   - Abra cada questão com `\resolucao{n}{valor}`.
   - Abra cada item com `\passo{a)}{Título}`. Depois vêm o raciocínio em uma ou duas frases, as
     contas que importam e `\resultado{...}{valor}`: a resposta em caixa, com a pontuação em
     vermelho. As pontuações somam o valor da questão.
   - Num item gráfico (CIR, trajetória, EHI), redesenhe a figura com a construção marcada em
     `construcao` e `vetorres`.
   - Escreva a conferência por outro caminho (ex.: "Verificação pela propriedade fundamental: … ✓").
   - Uma caixa `armadilhas` por questão, com 2 a 4 observações. Cada uma diz qual é o erro, o que
     ele produz e por quê, ou o que muda se um dado mudar.
   - `\criterios{}` por item, com o crédito parcial explícito (o `/corrigir` usa essa tabela), e
     `\inspirada{}` com as provas e as questões do mapa.
   - No fim, a página "Mapa do simulado":
     - a tabela item → habilidade → onde caiu antes, citando o mapa ou dizendo "nunca caiu";
     - "Como usar";
     - "Autoavaliação", com faixas de nota e o que refazer em cada uma.

   Ao salvar cada fonte, o gancho do projeto compila sozinho. Se o LaTeX falhar, o erro volta
   para você: corrija a fonte, e o gancho compila de novo. Salve os SVGs **antes** do `.tex` que os
   inclui. Sem o gancho (por exemplo, numa sessão aberta antes dele existir), rode a partir da raiz
   do projeto:
   - `uv run polishare pdf <fonte.tex>` compila uma fonte.
   - `uv run polishare pdf` compila todas as desatualizadas.

   O motor é o Tectonic. Os auxiliares não ficam na pasta, e em `simulados/` só entram PDFs.

   **Confira cada página antes de entregar.** Rode `pdftoppm -r 80 -png X.pdf "$TMPDIR/p"` e leia
   as imagens. Confira que:
   - nada sai cortado, sobreposto ou fora da margem (cuidado com os rótulos das figuras);
   - não sobra nenhum `\marcador`;
   - as figuras são legíveis;
   - os valores somam 10 e batem entre o simulado e o gabarito.

   Se já existir um simulado com o mesmo nome, acrescente `-2`, `-3`...

8. **Responder** com o link do PDF do simulado, a duração sugerida e um aviso para não abrir o
   gabarito antes de terminar. Não mostre as questões nem as respostas na conversa.
