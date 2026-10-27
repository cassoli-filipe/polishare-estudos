---
name: corrigir
description: Corrige a resolução do usuário (fotos ou PDF) de um simulado ou de uma prova antiga do Polishare, questão por questão, e registra os temas fracos no histórico da matéria. Use quando o usuário mandar a resolução dele para correção.
argument-hint: <simulado ou prova antiga>   (anexe as fotos ou o PDF da sua resolução)
---

# Correção

Argumentos: `$ARGUMENTS`.

1. **Referência.**
   - Simulado: use o `-gabarito.pdf` correspondente e os critérios de correção dele. A fonte
     `simulados/.fontes/<...>-gabarito.tex` tem o mesmo conteúdo em texto e é mais fácil de ler.
   - Prova antiga: se o próprio arquivo tem resolução, use-a. Senão, procure no `INDEX.md` uma
     resolução da mesma prova e do mesmo ano (pasta `Resoluções` ou nome com "resolução"). Se não
     houver resolução oficial, resolva você mesmo e diga claramente que a correção se baseia na sua
     resolução, não numa oficial.

2. **Resolução do usuário.** Leia as imagens ou o PDF anexados. Se não vieram, peça e pare.
   Se um trecho estiver ilegível, pergunte em vez de supor.

3. **Corrigir cada questão:**
   - veredito: certo, parcialmente certo ou errado, com a nota estimada pelos critérios
   - onde está o erro (a etapa exata) e o conceito por trás dele
   - o trecho correto daquela etapa, sem refazer a questão inteira (a menos que o usuário peça)
   - acerto de raciocínio com erro só de conta deve ser dito como tal

   Feche com a nota total estimada.

4. **Histórico.** Acrescente ao fim de `materias/<pasta da matéria>/estudo/historico.md` (crie com o
   título `# Histórico de estudo — <código> <nome>` se não existir):

   ```markdown
   ## <AAAA-MM-DD> — <simulado ou prova> — nota estimada <x>/<total>
   - Temas fracos: <tema (questão)>, ...
   - Temas fortes: ...
   - Erros recorrentes: <se o mesmo tipo de erro já apareceu antes no histórico>
   ```

5. **Responder** com o resumo por questão, a nota e uma sugestão do próximo passo (por exemplo,
   `/simulado` focado nos temas fracos).
