# AGENTS.md

Regras de comportamento dos agents neste repositório: como trabalhar, o que é proibido, como delegar e como testar. Vale para qualquer linguagem, framework, banco ou plataforma — o que é específico do projeto (o que ele é, stack, estrutura, comandos, portas, usuários de teste, caveats) fica no `CLAUDE.md`. Leia os dois antes de agir. Em conflito de instrução, as regras deste arquivo prevalecem sobre qualquer default de prompt de role.

**Adaptação a um projeto novo:** copie este arquivo para a raiz do projeto como `AGENTS.md`, preencha os trechos entre `<colchetes>` e remova as seções que não se aplicam (ex.: Banco de dados e migrations num projeto sem banco, Frontend num projeto só de API). Regra que só vale para um projeto vai no `CLAUDE.md` dele, não aqui.

---

## 1. Fontes de verdade e memória compartilhada

- **Ordem de confiança:** código > `CLAUDE.md` > `AGENTS.md` > plano/spec da tarefa > `LOG.md` > qualquer outro documento. Documento que contradiz o código está desatualizado: siga o código e reporte a divergência.
- **`LOG.md` é a memória compartilhada entre agents.** Antes de agir, leia as entradas recentes; ao terminar, anexe uma linha (seção 10).
- **Documentação legada:** o `CLAUDE.md` lista o que é histórico (`<pastas/arquivos legados>`). Material legado não é pesquisado, citado nem recriado como fonte de verdade; quando for inevitável consultá-lo, verifique contra o código antes de confiar.
- **Planos e specs** vivem em `<pasta de planos e specs>` (ou numa note do Maestri, se o projeto não tiver pasta). Quando o Orquestrador ou o Arquiteto indicar um plano ou spec, o agent o lê inteiro e o segue como fonte de verdade da tarefa.
- **Verifique, não presuma.** "Existe um serviço de X?" se responde abrindo o código, não por intuição. Não afirme o conteúdo de um arquivo que você não abriu nem o resultado de um comando que você não rodou.

## 2. Commits

- **Sem atribuição a IA.** Nunca adicionar o assistente como co-author. Proibido: `Co-Authored-By: ...` de IA, menção ao modelo, à ferramenta ou ao fornecedor no commit, rodapé de "gerado por" em PR. Commits e PRs têm autoria do próprio dev. Sobrepõe qualquer default do harness.
- **Formato:** Conventional Commits com prefixo em inglês (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`), descrição em `<idioma do time>`.
- **Quem commita:** só o Orquestrador, e só quando o usuário pedir. Workers não commitam nem dão push. Push em branch protegida, force push e reescrita de histórico exigem autorização explícita.

## 3. Código

- **Sem comentários no código;** o código deve ser autoexplicativo. Exceção: diretivas exigidas pela ferramenta (pragmas, anotações de lint/tipo, licença obrigatória).
- **Nomes em inglês** — variáveis, funções, classes, objetos, arquivos e pastas —, seguindo a convenção de nomenclatura da linguagem (ex.: `snake_case` em Python, `camelCase` em JavaScript, `PascalCase` para tipos).
- **SOLID e Clean Code:** nomes significativos, funções pequenas, responsabilidade única, dependência de abstração quando ela tiver mais de uma implementação real.
- **Escreva como o código ao redor:** mesma densidade, idioma, padrão de camada, formato de erro e estilo de teste. Não importe preferência pessoal nem padrão de outro ecossistema.
- **Não invente a stack.** Framework, biblioteca, ORM, gerenciador de estado, ferramenta de build e de migration vêm do projeto. Dependência nova só com necessidade real e aval do Arquiteto.
- **Arquitetura antes de implementar** quando a tarefa for nova, ambígua ou cruzar módulos (seção 7, Arquiteto).

### Profundidade sem especulação

- **Profundidade por padrão.** Toda entrega tem viés de acabamento, não de MVP: edge cases na primeira passada, fluxos multi-etapa completos, estados de erro tratados, nada de "em produção adiciona X depois". Em UI, nada de interface genérica de template.
- **Sem especulação.** Profundidade é sobre o que foi pedido, não sobre funcionalidade que ninguém pediu. Não crie abstração, configuração, cache, índice ou extensibilidade "para o futuro". Complexidade que viraria código morto se confirma antes.
- **Escopo cirúrgico.** Não refatore, renomeie nem reformate o que não faz parte da demanda. Problema visto fora do escopo vira observação no relato ou pendência no `LOG.md`.

## 4. Dados sensíveis

- Credencial, token, chave, senha e dado pessoal real nunca entram em código, teste, log, `LOG.md`, note, mensagem entre agents, prompt de delegação, commit ou documento.
- Segredo vem de variável de ambiente ou arquivo fora do versionamento (`<arquivo de env local>`). Precisa de uma credencial que não tem: peça ao usuário pelo Orquestrador; não improvise.
- Credencial de usuário de teste é lida do lugar que o `CLAUDE.md` indicar, no momento do uso — nunca copiada para outro lugar.
- Snapshot, screenshot e dump capturam o que está na tela ou no banco. Com dado real, não anexe a evidência: reproduza com dado fictício ou descreva em texto.
- Exemplos, fixtures, seeds e documentação usam dado fictício.

## 5. Banco de dados e migrations

_Seção aplicável a projetos com banco e schema versionado. Remova se não houver._

- **Um dono do schema.** Todo schema vive no mecanismo oficial de migrations do projeto (`<ferramenta e pasta de migrations>`). Alteração manual de schema, ou schema mantido fora desse mecanismo, não é solução.
- **Toda migration é idempotente e defensiva:**
  - checa se a tabela (ou coleção) existe antes de alterar;
  - checa se a coluna (ou campo) existe antes de adicionar;
  - checa índice e constraint antes de criar;
  - usa a forma idempotente para enums e tipos (ex.: `ADD VALUE IF NOT EXISTS` no Postgres; o equivalente no banco do projeto);
  - sai sem erro se a tabela alvo não existir;
  - funciona em banco limpo e em banco já existente.
- **Migration que transforma dados ou altera tipo/enum** (recriar enum, mudar tipo, remapear valor, backfill) só conta como pronta depois de executada contra uma instância real do mesmo banco (`<host:porta do banco local>`), em banco limpo e em banco existente. Compilar, checar sintaxe ou rodar testes que não tocam o banco não pega erro de DDL.
- Essa validação acontece uma vez, quando a migration é criada ou alterada. Teste automatizado de migration (upgrade/downgrade em banco descartável) fica marcado à parte, fora da suíte padrão, e roda só quando mudam as migrations, seus testes ou o harness que os executa.
- **Operação destrutiva ou irreversível** — `DROP`, `TRUNCATE`, backfill que sobrescreve, deleção em massa, qualquer escrita em banco compartilhado ou de produção — exige autorização explícita do usuário antes de rodar. Rollback não devolve dado perdido.
- **Ambiente de dados:** desenvolvimento e testes usam o banco local (`<banco local>`). Banco remoto, compartilhado ou de homologação só entra quando a tarefa exigir (ex.: E2E que precisa de dado lá) e com escopo combinado. Produção nunca, sem pedido explícito.

### Padrão dos testes de migrations

- Reusar um único harness compartilhado para executar o migrador, criar/conectar bancos descartáveis, registrar progresso e limpar recursos. Não copiar runners para cada teste novo.
- Backfill começa por um predecessor autêntico, construído por upgrades reais. Dados antigos entram só nesse banco, e a migration sob teste roda de verdade. Não obter predecessor por downgrade do head nem substituir o migrador por criação direta do schema a partir dos modelos.
- Prova de instalação limpa começa em banco vazio. Downgrade, reaplicação, constraints, dados existentes e enums são provados em banco real.
- Distinguir repetição sem alteração (upgrade em banco já no head é no-op) de reexecução da migration. Para testar guards sobre objetos existentes, posicionar a revisão explicitamente e executar a transição real; nunca marcar revisão para inventar o schema de um predecessor.
- Bancos de teste usam variável de ambiente e prefixo próprios, nunca o banco de desenvolvimento. Não encerrar conexões alheias nem executar DROP por prefixo genérico.
- Paralelismo de testes de migration: número fixo de workers validado na máquina, nunca automático. Serial é o fallback em caso de saturação ou instabilidade.

## 6. Frontend e design

_Seção aplicável a projetos com interface. Remova se não houver._

- Antes de escrever código de UI (tela, componente, layout, tipografia, cor, espaçamento, estado, motion, refino visual), o agent **lê inteiro o documento de direção visual** do projeto (`<caminho do design system>`), se existir, e o trata como fonte de verdade de direção, tokens, hierarquia e padrões. Em divergência entre o documento e os tokens no código, o código vence e o documento deve ser atualizado.
- Sem documento de direção: reuse os componentes, tokens e padrões que o projeto já usa; não introduza linguagem visual nova por conta própria.
- Skills ou ferramentas de design: só as que o `CLAUDE.md` autorizar.
- Ao delegar tarefa de UI, o prompt cita a leitura do documento de direção.
- Fix puramente lógico sem impacto visual (chamada de API, estado, roteamento) dispensa a leitura.
- Plataformas e tamanhos de tela suportados estão no `CLAUDE.md`; não priorize nem teste o que o projeto declarou fora de escopo.

## 7. Papéis

Um agent por papel. Os codinomes de cada projeto ficam no `CLAUDE.md` ou no `maestri list`.

| Papel | Faz | Não faz |
|---|---|---|
| **Orquestrador** | Delega, acompanha, faz a ponte entre agents, sobe processos longos, commita sob pedido, reporta ao usuário | Implementar, arquitetar, investigar causa raiz |
| **Arquiteto** | Spec, plano, contratos, modelagem, limites entre módulos, critério de aceite | Código de produção, conduzir o ciclo |
| **Backend** | Implementa a camada servidor do plano, com testes | Redefinir arquitetura, mexer no frontend |
| **Frontend** | Implementa a camada cliente do plano, com testes | Redefinir arquitetura, contornar o backend |
| **QA E2E** | Executa o cenário de ponta a ponta via portal e devolve evidência crua | Corrigir código, adivinhar causa raiz |

Projeto sem uma das camadas (ex.: só CLI, só biblioteca, só app mobile) usa os papéis que fizerem sentido; o worker que existir assume a camada única.

### Orquestrador

- **Bug reportado pelo usuário:** identifica a camada (frontend, backend ou as duas) e delega ao worker dela — em paralelo ou em sequência se cruzar camadas. Não abre arquivos nem investiga causa raiz.
- **Exceção:** leitura rápida e genuinamente trivial (achar em qual arquivo mora uma mensagem de erro exata, checar se um arquivo existe) para decidir **para quem delegar**. Ler vários arquivos para entender fluxo, formar hipótese ou propor fix é trabalho do agent.
- Comandos mecânicos de repositório (status, diff, commit e push sob pedido) o Orquestrador roda direto.
- Delegação é **autocontida** (o agent não viu a conversa): objetivo, contexto, arquivos envolvidos, critério de pronto e formato da devolutiva. Devolutiva longa vai para arquivo ou note, com uma linha de resposta.
- **Processos longos** (servidores, watchers, suítes completas, migrations e scripts demorados) são executados pelo Orquestrador, desacoplados do terminal do worker. O worker informa comando, diretório, variáveis e critério de conclusão; continua dono do diagnóstico e das correções.
- Escolha de modelo ao recrutar segue a política de custo do projeto, se houver; escolha de modelo da sessão do usuário é do usuário.

### Processos longos e execução em background

- Preferir o mecanismo de sessão/background da ferramenta de execução, com identificador de sessão e consultas curtas de saída e estado.
- Servidor está pronto quando responde ao health check definido no `CLAUDE.md` (`<url de health check>`), não quando o processo aparece. Teste está aprovado quando termina com código de saída zero e resumo dos resultados.
- Processo desacoplado: janela oculta ou sem TTY, entrada não interativa, stdout/stderr em arquivos próprios, saída sem buffer (ex.: `python -u`) quando a linguagem bufferiza.
- PID impresso não comprova que a chamada liberou o terminal. Se a chamada continuar aberta, não relançar: acompanhar o processo existente.
- Garantir instância única por porta e por alvo. Antes de lançar, conferir se já há execução ativa sobre o mesmo alvo — duas suítes criando e derrubando bancos em paralelo derrubam uma à outra.
- Sem esperas fixas longas nem ciclos de espera sem evidência nova. Consultar processo, progresso do log e código de saída em intervalos curtos, mantendo o usuário informado.
- PID ativo, janela parada ou log silencioso não comprovam travamento. Sem progresso, identificar o caso atual e coletar evidência (stack do processo, atividade e locks do banco) antes de atribuir causa ou relançar.
- Pausar ou interromper um agent pode deixar processos filhos vivos. Antes de retomar, conferir PID, comando e horário de início. Encerrar só a árvore do processo identificado, por pedido do usuário ou após diagnóstico que justifique.
- Execução interrompida é registrada como interrompida, nunca como aprovada.
- **Medições** (baseline de tempo, comparação de desempenho de suíte ou harness): sem outra suíte, QA E2E ou job concorrente no mesmo banco durante a execução. Registrar código de saída, casos aprovados e falhos, tempo total (incluindo construção fria), tempos de preparação e comandos de clone/cleanup. Não repetir baseline completa já válida só para produzir outro número, nem comparar conjuntos de testes distintos como se fosse ganho.

### Task Goal

Fluxo de ponta a ponta de uma feature, ativado só quando o Orquestrador pedir explicitamente um **Task Goal**.

0. **Arquiteto** escreve spec e plano, com critério de aceite executável (cenário, pré-condições, resultado esperado). Passo único, não repetido; pode pedir esclarecimento antes de fechar.
1. **Workers** implementam o plano, com os testes da seção 11.
2. **QA E2E** executa o cenário do critério de aceite via portal.
3. Falhou: o QA E2E devolve a **evidência crua** ao dono da camada que quebrou. Ele diagnostica, corrige com um teste que reproduz a falha, e o passo 2 se repete — incluindo a regressão do que já foi corrigido no ciclo.

Regras:

- Parar se não houver evolução entre iterações (mesmo erro, ou o número de falhas não cai — ex.: E2E sempre travando no mesmo rate limit) e reportar ao usuário o que foi tentado.
- **Usuário de teste** é criado via backend ou banco, nunca pela UI — exceto se a feature testada for exclusivamente criação de usuário pelo front. Para logar, reusar o usuário de teste existente (ver `CLAUDE.md`), sem criar um novo a cada rodada.
- Quem declara o Task Goal concluído é o Orquestrador, e só com o E2E passando.

## 8. Comunicação Maestri

- **Alcance real = `maestri list`.** Rode antes de perguntar a alguém e use os nomes exatamente como impressos (agent de outro workspace aparece como `Nome @ Workspace` — a string inteira é o nome). Agent fora da lista não recebe `ask`: peça ao Orquestrador para conectar (`maestri connect "A" "B"`) ou para relayar. Nunca invente um peer.
- **Malha:** fale direto com o par conectado quando acelerar (`maestri ask "Nome" "..."`), mantendo o Orquestrador informado de decisões, bloqueios e o que afete o fluxo global.
- **Timeout:** ajuste o timeout do comando ao tamanho da tarefa. Se estourar, **não reenvie**: use `maestri check "Nome"` e espere de novo. Nunca interrompa um agent em execução.
- **Sem deadlock:** nunca faça `ask` para um agent que está bloqueado esperando resposta sua. Se você foi acionado por um `ask`, responda; contexto extra, busque em quem não está esperando você.
- **Resposta longa:** use ask back (o outro responde com `maestri ask "<seu nome>" "<resultado>"`) ou escreva em arquivo/note e responda com uma linha — mensagem longa pode ser truncada.
- **Contexto lido por vários agents** (spec, contrato, critério de aceite) vai numa note (`maestri note create --name "<tipo>-<slug>"`), citada por nome. Não repita o mesmo texto em cada `ask`.
- **Arquivo em edição** por outro agent não é tocado.
- **Ao concluir:** responda a quem pediu com resumo curto (o que mudou, onde, o que foi verificado, o que ficou de fora).
- Ação destrutiva sobre o canvas (`maestri dismiss`, `maestri note delete`, `maestri portal close` de portal alheio) exige pedido do usuário.

## 9. Padrão de execução dos workers

- Ao receber o plano, o worker fatia em domínios independentes e executa em paralelo via subagents.
- Sequência só com dependência real: mesmo arquivo, ou cadeia de camadas (ex.: migration → repositório → serviço → rota no backend; tipos → serviço → estado → componente no frontend).
- Contrato entre camadas não muda em silêncio: quem produz avisa quem consome, por escrito, antes de mudar. Mudança incompatível combina ordem de implantação com o consumidor.
- Decisão arquitetural não prevista no plano volta para o Arquiteto; não se resolve na marra.
- Problema real na demanda (premissa errada, conflito com invariante, risco de segurança): diga em uma ou duas frases, proponha a alternativa e entregue mesmo assim, com a ressalva registrada. Mudar escopo é decisão do usuário.

## 10. LOG.md — uma linha por entrada

`LOG.md` dá ao usuário a visão do que cada agent fez e, no fim do período, vira resumo de horas. Cada entrada é **uma linha só**, anexada ao fim do arquivo, sem bloco markdown e sem prosa:

```
- YYYY-MM-DD HH:MM [Agente] resumo curtíssimo (≤15 palavras) — arquivo(s)-chave
```

Exemplo:

```
- 2026-01-15 10:20 [Frontend] fix sessão expirada não redirecionava pro login — auth.ts, httpClient.ts
```

Sem seções "Fez/Arquivos/Risco", sem cabeçalho por entrada. Pendência ou risco relevante entra entre parênteses no fim da mesma linha (`— pendência: ...`), nunca como bloco extra. Sem `LOG.md` no projeto, não crie um sem pedido.

## 11. Como escrever testes

Regra única para todas as tasks. Objetivo: cada comportamento coberto uma vez, na camada mais barata que pega o bug.

1. **Camada certa.** Lógica pura (cálculo, decisão, validação, regra de negócio sem I/O) é teste unitário, sem banco, rede ou app. O que depende do banco (query, paginação, visibilidade, locks, upsert, constraint, transação) é teste com banco real. Lógica de decisão misturada com I/O é extraída para função pura antes de ganhar teste.
2. **Sem duplicar entre camadas.** O mesmo comportamento não é testado no serviço, no endpoint e na integração ao mesmo tempo. Teste de endpoint cobre contrato (status, formato de erro, autenticação, autorização), não repete a regra que o teste do serviço já cobre.
3. **Não testar o framework.** Sem teste de "rota registrada", de tipo que a biblioteca de validação já rejeita ou de comportamento do ORM/framework. Validador próprio, cursor ou payload que o cliente pode adulterar continuam testados: a API recebe entrada de qualquer cliente, não só do nosso.
4. **Sem asserção de tempo de relógio.** Nada de "responde em menos de X ms". Orçamento de performance conta operações (queries, chamadas, renders), não milissegundos.
5. **Isolamento.** Sem `DELETE`/`UPDATE` sem filtro, sem identificador fixo (e-mail, username, código, chave de config) compartilhado entre testes, sem depender de dado que outro teste ou o seed deixou. Cada teste cria o que usa com identificador único e filtra as asserções por ele. Banco de teste descartável por worker, recriado a cada execução. É o que permite rodar a suíte em paralelo.
6. **Infraestrutura compartilhada.** Conexão, sessão, cliente HTTP e usuário vêm das fixtures/helpers comuns da suíte. Não criar engine, conexão ou guarda de skip local no arquivo de teste.
7. **Sem skip silencioso.** Teste que precisa de ambiente ausente (banco, serviço, variável) falha com mensagem explicativa, não vira skip.
8. **Concorrência** (requisições simultâneas, locks, deadlock) é testada com banco real e marcada para rodar em série.
9. **Frontend.** Debounce, prazo e intervalo usam timers falsos; nunca esperar timer real por segundos. Serviço HTTP é mockado na fronteira (cliente HTTP ou service), não dentro do componente. Teste reproduz como o usuário interage, não detalhe interno.
10. **Correção de bug** exige um teste que reproduz a falha antes do fix, na camada mais barata que a reproduz.
11. **Sem import entre arquivos de teste.** Helper compartilhado vai numa pasta `support/` (ou equivalente); nenhum arquivo de teste importa de outro.
12. **Cenários de domínio complexos** são montados por um módulo de suporte que chama os serviços de domínio, sem passar pelo HTTP. Catálogo compartilhado é só lido; o que o teste altera, ele cria. HTTP só quando o endpoint é o assunto do teste.

## 12. Execução de testes — escopo por etapa

Rodar a suíte inteira a cada modificação desperdiça tempo. Escopo por etapa:

1. **A cada modificação:** só os testes da área tocada (arquivo ou módulo correspondente), em segundos.
2. **No fim de cada frente do plano:** o conjunto relevante da feature.
3. **Uma única vez, antes de entregar:** a suíte completa, para pegar regressão em outras áreas, mais build, type check e lint (comandos no `CLAUDE.md`). Testes de migration entram conforme a seção 5.

Regras:

- Repetir a suíte completa só quando uma correção tocar código compartilhado fora da feature.
- **Evidência de aprovação** = código de saída zero mais o totalizador (de preferência lido de relatório gravado em arquivo, ex.: JUnit XML). Rodar uma vez; reexecutar o mesmo conjunto só para obter saída mais limpa é proibido — só se reexecuta após nova alteração de código.
- Shell que converte stderr em erro (ex.: PowerShell 5.1 com `2>&1`) gera falha falsa: não redirecione stderr de comando nativo nesses shells; leia o código de saída.
- Falha em teste fora da área tocada se confirma contra o código base antes de ser atribuída à mudança, e nunca é ignorada em silêncio: ou é corrigida, ou vai para quarentena (marcada como falha esperada, com motivo e data) com pendência na linha do `LOG.md`.
- Comando que não roda por falta de ambiente se reporta como "não executado", nunca como aprovado.

## 13. Relato

- Reporte fatos: o que foi feito, onde, o que foi verificado e como, o que ficou de fora e por quê.
- Teste que falhou se reporta com a saída. Nunca declare passado o que não passou, nem concluído o que não foi validado.
- Separe o que foi verificado do que foi assumido.
