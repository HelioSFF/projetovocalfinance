# CLAUDE.md — mobile_voice (Vocal Finance)

Mapa do projeto, verificado contra o código em 2026-10-31. A spec completa está na note Maestri **`spec-mvp`**, que é a fonte de verdade de contratos, schema, regras, telas, plano e E2E. As regras de comportamento dos agents estão em `AGENTS.md`.

## Visão geral

- Repo: https://github.com/HelioSFF/projetovocalfinance.
- **Vocal Finance** é um app de finanças pessoais por voz. O usuário segura o botão de microfone, fala ("comprei 3 cafés de 5 reais") e solta. O backend transcreve, classifica, extrai e grava o registro financeiro.
- Projeto **acadêmico** da disciplina de Dispositivos Móveis (estudo de React Native), feito para nota e para demonstrar o aprendizado. O código deve ter nível de aula introdutória.
- MVP com 2 telas: **Início** (gravar e ver o último registro) e **Histórico** (lista, busca por item). Fora do MVP: login, orçamento e gráficos.
- Desenvolvimento web-first; depois, APK via EAS.

## Estrutura

```
/ (raiz)
  docker-compose.yml   serviços db, backend, frontend, checks (profile)
  .env.example         POSTGRES_USER/PASSWORD/DB
  CLAUDE.md  AGENTS.md  README.md
  frontend/            Expo SDK 58 + React Native 0.88 + React 19.3 + TypeScript strict
    App.tsx  index.ts  app.json  eslint.config.js  Dockerfile  .env.example
    design_exemplo.pdf direção visual (telas 0 = Início, 6 = Histórico)
    AGENTS.md          regras oficiais Expo (ler antes de usar API Expo/RN)
    src/
      routes/          StackRoutes.tsx (Stack: MainTabs) → TabRoutes.tsx (Home, History)
      screens/         HomeScreen.tsx, HistoryScreen.tsx
      components/      EmptyState.tsx (+ RecordButton, RecordCard, StatusMessage em F2/F3)
      constants/       colors.ts, categoryStyles.ts
      types/           navigation.ts
      hooks/ services/ utils/   previstos para F2/F3 (useVoiceRecorder, api.ts, recordService.ts, formatters)
  backend/             Python 3.12, FastAPI, SQLAlchemy async (asyncpg), Pydantic, Alembic
    Dockerfile  requirements.txt  requirements-dev.txt  alembic.ini  pytest.ini  .env.example
    alembic/versions/0001_create_financial_records.py
    app/
      main.py          FastAPI, CORS, routers
      core/            config.py (pydantic-settings), errors.py
      db/session.py    engine e sessão async
      models/ schemas/ repositories/ routers/ services/ clients/
    scripts/latency_spike.py   spike B0 (fora do app)
    tests/             unit/ db/ api/ migrations/ support/
```

Pontos de entrada:
- Frontend: `package.json#main = index.ts` → `App.tsx` (`NavigationContainer` + `StackRoutes`).
- Backend: `app.main:app`.

## Stack

- **Frontend:**
  - React Navigation 7 (`native-stack` + `bottom-tabs`). **Não há Expo Router.**
  - `expo-audio` (gravação + permissão de microfone via plugin em `app.json`), `@expo/vector-icons`, `react-native-web` + `@expo/metro-runtime`.
  - HTTP com `fetch`, sem axios.
  - ESLint (`eslint-config-expo`). Jest em adição (jest-expo).
  - Gerenciador: npm (`npx expo install <pkg>` para instalar).
- **Backend:**
  - fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, alembic, psycopg, pydantic(-settings), python-multipart, openai.
  - Testes: pytest, pytest-asyncio, httpx.
- **Banco:** Postgres 18 (`postgres:18`; volume em `/var/lib/postgresql`). Tabela `financial_records`.
- **Restrição Expo Go:** só módulos incluídos no Expo Go; sem código nativo custom e sem development build. `ios/` e `android/` são gerados e nunca editados.

## Pipeline (backend, `POST /api/voice-records`)

1. Validar o áudio (mime e tamanho ≤ `MAX_AUDIO_MB`).
2. Transcrever com **`gpt-transcribe`** (`languages:["pt"]`, prompt e keywords com as categorias).
3. Em paralelo (`asyncio.gather`):
   - **Decisions API `gpt-6-luna`**, uma única chamada com 4 perguntas: `plausible` (predicate), `is_financial` (predicate), `type` (choice income|expense) e `category` (choice da lista fixa).
   - **Responses API `gpt-6-luna`**, `json_schema` strict, que extrai `item`, `quantity`, `unit_price` e `stated_total`. O modelo é configurável em `EXTRACTION_MODEL`, com `gpt-4o-mini` como substituto.
4. Aceite: as duas probabilidades ≥ `DECISION_THRESHOLD` e extração válida. Se reprovar, o fallback **DeepSeek `deepseek-flash`** (non-thinking) **apenas reescreve a frase**, sem classificar nem extrair. A frase reescrita volta ao passo 3 **uma vez**. Reprovou de novo: 422 com mensagem amigável.
5. Regras:
   - `total = quantity × unit_price` calculado pelo **backend em Decimal** (nunca pela IA). Se só o total for dito, `total = stated_total` e `unit_price = total / quantity`.
   - A choice `type` é a autoridade. O backend só **reconcilia** tipo × categoria: categoria do outro tipo vira `other_expense` ou `other_income`.
6. Gravar em `financial_records` e responder 201 com o FinancialRecord. Valores monetários vão como strings decimais.

Endpoints:
- `GET /health`
- `GET /api/financial-records?limit&offset&q` (mais recentes primeiro)
- `POST /api/voice-records` (multipart `file`)

Formato de erro: `{"error":{"code","message"}}`.

## DEV TOOLS (seção 19 da `spec-mvp`)

- Painel de depuração por requisição de voz, para a apresentação: tempos por etapa, tokens, custo em USD, transcrição bruta, saídas estruturadas da Decisions e da extração, aceite/fallback e o cálculo final do total.
- Liga só com `APP_ENV=development` no `backend/.env` (default `production`). O gate é **do backend**; nenhum header ou campo do cliente liga debug.
- Nesse modo, o `POST /api/voice-records` devolve a chave extra `debug` no nível raiz do 201 e dos erros 422/503 do pipeline. Em qualquer outro ambiente a chave não existe.
- Campo multipart opcional `duration_ms` (duração no cliente), usado só como base de custo da transcrição quando o provedor não devolve a duração.
- Coletor: `PipelineTrace`/`NullTrace` (`app/services/pipeline_trace.py`) injetado pelo construtor; tempo medido só no `VoiceRecordService`; services só entregam a resposta do provedor ao trace. Preços em `app/core/pricing.py`; custo em `app/services/cost_calculator.py` (Decimal).
- Segurança: nada de chave, header, mensagem de exceção de provedor ou prompt no debug; montagem por allowlist; debug nunca é gravado no banco nem logado.
- Frontend: `DevPanel` colapsável abaixo do status na Home, só com `EXPO_PUBLIC_APP_ENV=development` (`src/utils/appEnv.ts`). Sem libs novas.
- Para ligar: `APP_ENV=development` em `backend/.env`, `EXPO_PUBLIC_APP_ENV=development` no `.env` da raiz e `docker compose up -d --build backend frontend` (o Metro embute `EXPO_PUBLIC_*` no start). Para desligar: voltar os dois para `production` e reiniciar.

## Categorias (aprovadas pelo usuário; fonte: `backend/app/services/categories.py`)

- **Despesas:** food, groceries, housing, utilities, transport, health, education, leisure, shopping, clothing, personal_care, pets, subscriptions, travel, taxes_fees, gifts_donations, other_expense.
- **Receitas:** salary, freelance, sales, investments, refunds, gifts_received, other_income.
- O frontend mapeia só code → ícone e cor em `frontend/src/constants/categoryStyles.ts`.

## Variáveis de ambiente

- `backend/.env` (**gitignored, nunca no Git**; modelo em `backend/.env.example`):
  - DATABASE_URL, TEST_DATABASE_URL
  - **OPENAI_API_KEY, DEEPSEEK_API_KEY**
  - CORS_ORIGINS, DECISION_THRESHOLD, MAX_AUDIO_MB, AI_TIMEOUT_SECONDS, OPENAI_SERVICE_TIER, EXTRACTION_MODEL
  - APP_ENV (default `production`; `development` liga o DEV TOOLS). Entra com a etapa B3.
  - No compose, DATABASE_URL é sobrescrita para apontar ao serviço `db`.
- `frontend/.env.example`: `EXPO_PUBLIC_API_URL` (default `http://localhost:8000`). No Android via Expo Go, usar o IP da LAN do PC. **Chave de API nunca em `EXPO_PUBLIC_*`.** `EXPO_PUBLIC_APP_ENV` (default `production`) entra com a etapa F5.
- Raiz `.env.example`: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB (default `vocal` / `vocal` / `vocal_finance`). Também `EXPO_PUBLIC_APP_ENV` (default `production`), que o compose repassa ao frontend.

## Comandos (na raiz, via Docker)

```bash
docker compose up -d --build frontend        # Expo web em http://localhost:8081
docker compose up -d --build backend         # API em http://localhost:8000 (sobe db; roda alembic upgrade head antes do uvicorn)
docker compose run --rm checks               # frontend: npx expo lint + npx tsc --noEmit + npm test
docker compose run --rm backend pytest -m "not migrations" -q   # suíte padrão do backend
docker compose run --rm backend pytest -m migrations -q         # testes de migration (só quando mudam migrations)
docker compose run --rm backend alembic upgrade head            # aplicar migrations manualmente
docker compose down                          # parar (down -v apaga volumes, incluindo o banco: destrutivo)
```

- Health: `GET http://localhost:8000/health` → `{"status":"ok"}`.
- Portas: frontend 8081, backend 8000, db 5432.
- Banco de testes: `TEST_DATABASE_URL` (`vocal_finance_test`). É criado por `db/init/01_create_test_database.sql` só quando o volume do Postgres é novo; em volume existente, ele já precisa existir.
- Após mudar dependências do frontend, recriar o volume `frontend_node_modules` antes do rebuild.
- Testes do frontend (Jest): `npm test` (`jest-expo`), já incluído no `docker compose run --rm checks`.
- APK (última etapa): `eas.json` profile `preview` com `android.buildType: "apk"`; `npx eas-cli@latest build -p android --profile preview`. Pode usar o MCP oficial da Expo (`https://mcp.expo.dev/mcp`), que o usuário instala. `owner`/`projectId` em `app.json` ainda são de `harielgaelins-team`.

## Convenções

- Regras globais: **sem comentários no código**; identificadores e arquivos em **inglês** (textos de UI em pt-BR); SOLID e Clean Code sem over-engineering.
- **Frontend** (estilo da turma):
  - `export default function`, `useState`/`useEffect`, `try/catch/finally` com loading e erro.
  - `StyleSheet.create` no fim do arquivo; cores de `constants/colors.ts`.
  - Arquivos PascalCase para componentes, telas, rotas e tipos; camelCase para services, hooks e utils.
  - Imports relativos. Sem libs de estado. Poucas dependências.
  - Antes de usar API Expo, conferir https://docs.expo.dev/versions/v58.0.0/.
- **Backend:**
  - Camadas `routers` → `services` → `repositories`; `clients` com instâncias únicas de AsyncOpenAI (OpenAI e DeepSeek via `base_url`).
  - Regras puras em funções testáveis. `snake_case`.
- **Migrations (Alembic):** checar tabela, coluna, índice e constraint antes de criar ou alterar; `ADD VALUE IF NOT EXISTS` em enums (o schema evita enums); sair sem erro se a tabela alvo não existir; idempotentes em banco limpo e existente.
- **Testes:**
  - Backend com pytest: unit, db (Postgres real), api e migrations (marcado). Nenhum teste chama OpenAI ou DeepSeek reais.
  - Frontend com Jest.
  - Gate do frontend: lint + tsc + Jest. Gate do backend: suíte padrão verde.

## Status do plano (seção 13 da `spec-mvp`)

| Etapa | Status |
|---|---|
| O1, B0, B1, B2, B2.1, F1, F1b, F2, F3 | feitas |
| E2E rodada 1 (O2) | cenários 1 a 8 aprovados; cenário 9 pendente |
| B3, F5 | DEV TOOLS (seção 19), despachados em 2026-10-31 |
| F4 | APK só no final |

## Regras dos agents (Maestri)

- **Orquestrador** (`ORQUESTRADOR_MOBILE_APP`): coordena; **somente ele sobe servidores e containers**; commita ou dá push só quando o usuário pedir.
- **Arquiteto** (`ARQUITETO_MOBILE_APP`): spec, contratos e plano; não escreve código de produção. Mudança de contrato passa por ele.
- **Backend** (`BACKEND_MOBILE_APP`): implementa `backend/` conforme a `spec-mvp`, com pytest.
- **Frontend** (`FRONTEND_MOBILE_APP`): implementa `frontend/src/` conforme a `spec-mvp`; roda lint, tsc e Jest.
- **QA E2E**: executa o cenário da seção 15 da spec contra o ambiente já levantado. No fluxo de voz, o usuário interage direto no portal e o QA instrui o que falar. Não corrige código nem sobe servidores.
- **Workers não commitam nem dão push.** Informam ao Orquestrador comando, diretório e critério de pronto para processos longos.
- O terminal de cada agent inicia em `.maestri/roles/<id>/`; ir para a raiz antes de usar git ou comandos do projeto.

## Dúvidas em aberto

1. Conta EAS para o APK e URL do backend acessível pelo celular. Resolver só na etapa F4.
2. Fast mode (`OPENAI_SERVICE_TIER`, 2x custo): decidir após o spike B0.
3. A validar no B0: português no `gpt-transcribe`, `json_schema` strict no `gpt-6-luna` e latência real.
4. Critérios de avaliação da disciplina e prazo de entrega.
