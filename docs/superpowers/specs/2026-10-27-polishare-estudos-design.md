# Polishare → Claude Code: extrator e comandos de estudo

**Data:** 2026-10-27
**Status:** proposta, aguardando revisão

## 1. Objetivo

Trazer o material do Polishare (provas antigas, resoluções, listas, resumos) de uma matéria para uma
pasta local organizada, de modo que o Claude Code consiga estudar com esse material: mapear o que
cai em cada prova, gerar simulados no estilo das provas antigas e corrigir resoluções.

### Critérios de sucesso

1. `polishare baixar PME3100` baixa todos os arquivos de Mecânica I para
   `materias/PME3100 - Mecânica I/`, espelhando as pastas do site.
2. Rodar o mesmo comando de novo não baixa nada que já foi baixado, e retoma de onde parou se foi
   interrompido.
3. Nenhuma requisição altera a conta (favoritos, perfil, curso, senha).
4. O `INDEX.md` da matéria permite achar, sem abrir PDFs, "todas as P1 com resolução".
5. `/simulado PME3100 P1` gera uma prova inédita no estilo das P1 antigas, com gabarito separado e
   cada questão citando de quais provas antigas veio a inspiração.

### Fora do escopo

- Baixar o site inteiro ou todas as matérias de um semestre de uma vez.
- Servidor MCP (pode embrulhar o extrator depois, se fizer falta).
- Seguir links externos (Responde Aí): só são registrados.
- Publicar, enviar ou compartilhar arquivos de volta para o Polishare.
- Guardar dados de outras pessoas (nome de quem enviou cada arquivo, perfis).

## 2. Como o Polishare funciona (mapeado em 2026-10-27)

Site PHP renderizado no servidor (jQuery/Bootstrap), em hospedagem compartilhada, com sistema de
prevenção de intrusão. Não há API. Tudo exige login.

| Recurso | Requisição | Resposta |
|---|---|---|
| Login | `POST /login.php` com `email`, `password` | Cookie de sessão `PHPSESSID` |
| Busca de disciplina | `GET /index.php?pagina=pesquisa&t=d&q=<termo>` | Blocos `div.resultado`: `h3 > a[href="?id=<id>"]` com o nome, primeiro texto de `p` com o código, links das subpastas |
| Pasta (matéria, subpasta) | `GET /index.php?id=<id>` | `table tr` com colunas Nome, Descrição (`Pasta`, `PDF`, `LINK`…), Autor |
| Arquivo | `GET /file.php?id=<id>` | O arquivo direto; `Content-Disposition: inline; filename="P1 - 2021.pdf"` |

Hierarquia típica: Matéria → `Aulas`, `Listas`, `Provas`, `Resoluções`, `Resumos`, `Teoria`,
`Testes`, `Textos` → em `Provas`: `P1`, `P2`, `P3`, `PRec`, `PSub` → arquivos. Volume: a pasta
`Provas/P1` de Cálculo I tem cerca de 28 arquivos (2006 a 2026).

Observações que moldam o desenho:

- **Links com efeito colateral.** Cada linha de pasta tem `?pagina=favoritos&action=ap&codigo=<id>`,
  que adiciona aos favoritos. Também existem `logout.php`, `course.php`, `pagina=configuracoes`.
- **Nomes repetidos.** A busca pode devolver duas disciplinas com o mesmo nome (ex.: dois
  "Álgebra Linear I" com ids diferentes). Dentro de uma pasta, dois arquivos podem ter o mesmo nome.
- **Política de publicação, cláusula 9.** Proíbe práticas que prejudiquem o servidor, sob pena de
  suspensão da conta. Daí o ritmo lento e uma matéria por vez.
- `robots.txt` não existe (404).

## 3. Arquitetura

Projeto Python (3.11+) com dependências mínimas: `requests`, `beautifulsoup4`. Testes com `pytest`.

```
polishare-estudos/
├── .env                      # POLISHARE_EMAIL, POLISHARE_SENHA (fora do git, chmod 600)
├── .gitignore                # .env, materias/
├── CLAUDE.md                 # organização do projeto e das matérias, regras de estudo
├── pyproject.toml            # expõe o comando `polishare`
├── polishare/
│   ├── client.py             # sessão HTTP: login, ritmo, retentativas, detecção de sessão expirada
│   ├── parse.py              # HTML → estruturas (funções puras)
│   ├── crawl.py              # percorre a árvore de uma matéria com lista de permissão
│   ├── store.py              # caminhos, nomes de arquivo, manifest
│   ├── index.py              # gera INDEX.md e links.md
│   └── cli.py                # comandos `buscar` e `baixar`
├── tests/
│   ├── fixtures/             # HTML real salvo (busca, matéria, pasta, login), sem nomes de autores
│   └── test_*.py
├── .claude/skills/
│   ├── mapa/SKILL.md
│   ├── simulado/SKILL.md
│   └── corrigir/SKILL.md
└── materias/
    └── PME3100 - Mecânica I/
        ├── manifest.json
        ├── INDEX.md
        ├── links.md
        ├── Provas/P1/2021.pdf
        └── estudo/
            ├── mapa-P1.md
            ├── simulados/
            └── historico.md
```

### 3.1 `client.py`: sessão HTTP

- Lê `POLISHARE_EMAIL` e `POLISHARE_SENHA` do `.env` (leitura simples, sem dependência extra).
  Se faltar, para com uma mensagem dizendo como criar o arquivo.
- `login()`: `POST /login.php`. O login conta como bem-sucedido só se a página seguinte contém o link
  `logout.php`. Senão, erro "credenciais recusadas", sem retentar.
- `get(url)`: uma requisição por vez, com **intervalo mínimo de 2,5 s** entre requisições (ajustável,
  piso de 2 s). User-Agent honesto: `polishare-estudos/0.1 (uso pessoal)`.
- **Sessão expirada:** se uma página de pasta volta com o formulário de `login.php`, faz login de novo
  uma vez e repete a requisição. Se acontecer de novo, aborta.
- **Retentativas:** timeout ou 5xx → até 3 tentativas com espera de 10 s, 30 s, 60 s.
- **Parada imediata:** 403 ou 429, ou 5 falhas seguidas → aborta a execução inteira e diz por quê.
  É sinal de que o servidor ou o sistema anti-intrusão está reagindo.
- Só faz `POST` no login. Todo o resto é `GET`.

### 3.2 `parse.py`: leitura do HTML

Funções puras, testadas com fixtures:

- `parse_busca(html) -> list[Disciplina]`, com `Disciplina(id, codigo, nome)`.
- `parse_pasta(html) -> list[Item]`, com `Item(tipo, nome, id | url)` e
  `tipo ∈ {"pasta", "arquivo", "link"}`. O tipo vem do `href` (`index.php?id=` → pasta,
  `file.php?id=` → arquivo, `http…` → link externo), não da coluna Descrição.
- `esta_deslogado(html) -> bool`: presença do formulário com `action="login.php"`.
- A coluna Autor é ignorada.

### 3.3 `crawl.py`: percorrer a matéria

- Busca em profundidade a partir do id da matéria, guardando o caminho de pastas
  (`["Provas", "P1"]`).
- **Lista de permissão**, a única regra que decide o que seguir:
  - pasta: `href` casa com `^(index\.php)?\?id=[A-Za-z0-9]+$`
  - arquivo: `href` casa com `^file\.php\?id=[A-Za-z0-9]+$`
  - qualquer outro `href` (favoritos, perfil, logout, configurações, curso, externos) não é seguido.
    Links externos vão para `links.md`.
- Conjunto de ids visitados (evita ciclos) e profundidade máxima de 6.
- `--pastas Provas,Resoluções` limita a descida às pastas de primeiro nível escolhidas.
- `--simular` percorre só as pastas e mostra quantos arquivos baixaria e quantos já existem, sem
  baixar nenhum.

### 3.4 `store.py`: arquivos e manifest

- Pasta da matéria: `materias/<CODIGO> - <Nome>/`. Pastas e arquivos espelham os nomes do site,
  higienizados (sem `/ \ : * ? " < > |`, espaços nas pontas removidos, até 120 caracteres).
- Nome do arquivo: o nome mostrado na tabela (ex.: `2026 (com resolução)`) mais a extensão tirada do
  `Content-Disposition` (`.pdf` se não houver). Em colisão, acrescenta ` [<id>]`.
- Download em streaming para `<nome>.part`, renomeado só no fim. Arquivos acima de 100 MB são
  pulados e registrados.
- `manifest.json`, salvo de forma atômica (arquivo temporário + rename) **após cada arquivo**:

```json
{
  "disciplina": {"id": "ExY", "codigo": "PME3100", "nome": "Mecânica I"},
  "atualizado_em": "2026-10-27T17:00:00-03:00",
  "arquivos": {
    "n39m": {"caminho": "Provas/P1/2021.pdf", "pasta": ["Provas", "P1"], "nome": "2021",
             "bytes": 1234567, "baixado_em": "2026-10-27T17:00:00-03:00"}
  },
  "falhas": {"abcd": {"pasta": ["Listas"], "nome": "Lista 3", "erro": "timeout",
                      "em": "2026-10-27T17:05:00-03:00"}},
  "links": [{"pasta": ["Provas", "P1"], "nome": "Resolução 2019",
             "url": "https://www.respondeai.com.br/simulator/59/lista/139/3924/exercicio-lista/55606"}]
}
```

- Retomada: id presente em `arquivos` com o arquivo existindo em disco → pula. Ids em `falhas` são
  tentados de novo na próxima execução.

### 3.5 `index.py`: contexto para o Claude

`INDEX.md` gerado a partir do manifest ao fim de cada `baixar`. Uma tabela por pasta de primeiro
nível:

| Subpasta | Nome | Ano | Resolução | Arquivo |
|---|---|---|---|---|
| P1 | 2022 (com Resolução) | 2022 | sim | [Provas/P1/2022 (com Resolução).pdf](<Provas/P1/2022 (com Resolução).pdf>) |

- **Ano:** primeiro `19xx`/`20xx` no nome, senão vazio.
- **Resolução:** "sim" se o nome contém `resolu`, `gabarito` ou `resolvid` (sem diferenciar
  maiúsculas e acentos), ou se o arquivo está na pasta `Resoluções`. Senão, "?". O `INDEX.md`
  avisa que essas colunas são heurísticas, tiradas do nome.

`links.md` lista os links externos por pasta.

### 3.6 `cli.py`: comandos

```
polishare buscar <termo>
    → tabela: código, nome, id

polishare baixar <código> [--id ID] [--pastas A,B] [--simular] [--intervalo 2.5]
    → busca o código e fica só com os resultados cujo código é exatamente igual
    → um resultado: usa esse; nenhum: mostra o que a busca achou e para;
      mais de um: lista e pede --id para escolher entre eles
    → percorre, baixa, atualiza manifest, gera INDEX.md e links.md
    → resumo no fim: novos, já existentes, falhas, tempo total
```

Progresso em linha (`[34] Provas/P1/2019`), sem total, porque a árvore é percorrida enquanto baixa; o total sai no `--simular`. Ctrl+C interrompe com segurança, já que o
manifest é salvo a cada arquivo.

## 4. Comandos de estudo (skills do Claude Code)

Os três leem o `INDEX.md` antes de abrir qualquer PDF e salvam o resultado em `estudo/` dentro da
matéria. PDFs escaneados ou manuscritos são lidos pela visão do Claude. Não há etapa de OCR.

### `/mapa <código> <prova>`

- Lê as provas daquela pasta (ex.: `Provas/P1`), por padrão as 8 mais recentes segundo a coluna Ano
  do `INDEX.md` (sem ano vão por último), para limitar o custo. Se o usuário pedir, lê todas.
- Gera `estudo/mapa-<prova>.md` com:
  - tabela tema × ano, mostrando onde cada tema caiu
  - formatos de questão recorrentes (ex.: "sempre tem um limite com L'Hôpital")
  - os temas mais frequentes e os que sumiram nos anos recentes
  - lista das provas lidas, para o mapa ser verificável

### `/simulado <código> <prova> [número de questões]`

- Usa `estudo/mapa-<prova>.md` (gera antes, se não existir) e as provas com resolução como
  referência de estilo e dificuldade.
- Questões **inéditas** no estilo das antigas, não cópias. Cada uma diz em que provas se inspirou
  (ex.: "estilo de P1 2019 Q2 e P1 2022 Q3").
- Mistura de dificuldade parecida com a das provas reais. Se `estudo/historico.md` existir, dá peso
  maior aos temas fracos registrados lá.
- Salva `estudo/simulados/<data>-<prova>.md` e `estudo/simulados/<data>-<prova>-gabarito.md`
  separados, para o usuário não ver as respostas sem querer.

### `/corrigir <simulado ou prova>`

- O usuário anexa fotos ou PDF da própria resolução.
- Compara com o gabarito do simulado ou com a resolução da prova antiga, questão por questão:
  certo, parcialmente certo ou errado, onde está o erro e qual o conceito por trás dele.
- Acrescenta uma entrada em `estudo/historico.md` com data, prova, nota estimada e temas fracos.

## 5. `CLAUDE.md` da raiz

Explica a organização (`materias/<CODIGO> - <Nome>/`, `INDEX.md`, `estudo/`), os comandos
disponíveis e duas regras:

1. Ao usar material de uma matéria, comece pelo `INDEX.md` e cite de que arquivo veio cada fato ou
   questão.
2. Nunca rode `polishare baixar` sem o usuário pedir, e nunca para mais de uma matéria por vez.

## 6. Privacidade e cuidado com o site

- Credenciais só no `.env` (fora do git, permissão 600). Nunca aparecem em log ou mensagem de erro.
- `materias/` fora do git: o material é de outros alunos e professores e não deve ir para um
  repositório público.
- Nenhum nome de autor ou dado de perfil é guardado. As fixtures de teste têm os nomes de autores
  trocados por `--`.
- Ritmo lento, sequencial, uma matéria por vez, parada imediata diante de 403/429.

## 7. Testes

**Unitários (`pytest`, sem rede):**

- `parse_busca`, `parse_pasta`, `esta_deslogado` contra fixtures reais.
- Lista de permissão: hrefs de favoritos, perfil, logout, configurações, curso e externos nunca
  viram pasta ou arquivo a seguir.
- Higienização de nomes e tratamento de colisão.
- Retomada: com um manifest parcial, só os ids faltantes são baixados (cliente falso).
- Sessão expirada: cliente falso que devolve a página de login uma vez → relogin e sucesso; duas
  vezes → aborto.
- Parada em 403/429 e após 5 falhas seguidas.
- Intervalo entre requisições com relógio falso.

**Piloto manual (PME3100, que no Polishare se chama Mecânica I):**

1. `polishare buscar PME3100` → uma linha: Mecânica I, id `ExY`.
2. `polishare baixar PME3100 --simular` → contagem de arquivos plausível e zero downloads.
3. `polishare baixar PME3100 --pastas Provas` → baixa; conferir uns PDFs e o `INDEX.md`.
4. Rodar de novo → "0 novos".
5. Conferir no site que os favoritos não mudaram.
6. `/mapa PME3100 P1` e `/simulado PME3100 P1` → revisar o resultado juntos.

## 8. Riscos

| Risco | Mitigação |
|---|---|
| O site muda o HTML | Parsing concentrado em `parse.py`, com fixtures; testes quebram cedo |
| Sistema anti-intrusão bloqueia o IP | Ritmo de 2,5 s, sequencial, parada em 403/429 |
| PDF escaneado de baixa qualidade | O Claude lê por visão e avisa quando não consegue ler uma questão |
| Heurística de ano/resolução erra | Colunas marcadas como heurísticas no `INDEX.md` |
| Login muda (ex.: captcha) | Login falha com mensagem clara; o extrator não tenta contornar |

## 9. Economia de espaço (adicionado em 2026-10-27, depois do piloto)

O piloto mostrou que uma prova (todas as P1 de PME3100, de 2000 a 2026) ocupa ~8 MB, e que 57% do
espaço eram resoluções de listas escaneadas, que o usuário considera inúteis. Mudanças:

- **Só provas.** Sem opções, `baixar` pega só a pasta `Provas`. `--prova P1` pega `Provas/P1` e,
  em `Resoluções`, só os arquivos que citam a prova no nome ("P1", "Prova 1"). `--pastas` continua
  para pedidos explícitos e não se combina com `--prova`.
- **Validade.** Cada arquivo no manifest ganha `expira_em`: a data de `--ate` (a data da prova) ou
  30 dias depois do download. Registros antigos, sem o campo, valem `baixado_em` + 30 dias. Rodar
  `baixar` com `--ate` atualiza a validade dos arquivos do escopo que já estão no disco.
- **`polishare limpar [código] [--prova P] [--agora] [--quieto]`.** Apaga os PDFs com
  `expira_em` < hoje (ou todos, com `--agora`, que exige o código). Marca o registro com
  `removido_em` em vez de apagá-lo, regenera o `INDEX.md` e remove pastas vazias. Nunca toca em
  `estudo/`. Não usa rede nem credenciais. `baixar` traz de volta o que foi removido.
- **Limpeza automática.** Um hook `SessionStart` (matcher `startup|resume`) em
  `.claude/settings.json` roda `uv run --quiet polishare limpar --quieto` ao abrir o Claude Code no
  projeto. Ele não imprime nada se nada venceu e nunca falha a sessão.
- **INDEX.md** lista só o que está no disco, com a coluna Expira, e informa quantos arquivos
  expiraram.
