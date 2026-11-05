# Vocal Finance — Relatório Técnico e Roteiro de Apresentação

Nov 2, 2026 · @Thiago Barreto

O Vocal Finance é um app de finanças pessoais por voz: o usuário segura o botão do microfone, fala "comprei 3 cafés de 5 reais", solta, e o registro aparece na tela já classificado e com o total calculado.

## Visão geral

O app tem duas telas, **Início** (gravar e ver o último registro) e **Histórico** (lista com busca por item). Foi feito em React Native com Expo, para a disciplina de Dispositivos Móveis, e roda no navegador e no celular com o mesmo código. Login, orçamento e gráficos ficaram fora do MVP.

O fluxo de uma gravação, de ponta a ponta:

1. O usuário segura o botão e fala; o app grava o áudio (`expo-audio`).
2. Ao soltar, o app envia o áudio por `POST /api/voice-records` (multipart).
3. O backend (FastAPI) valida o áudio e transcreve com a OpenAI (`gpt-transcribe`).
4. Em paralelo, a IA decide se é um gasto/ganho válido, o tipo e a categoria, e extrai item, quantidade e preço.
5. Se a frase for reprovada, o DeepSeek só a reescreve e o backend tenta uma segunda vez.
6. O backend calcula o total em `Decimal`, grava no Postgres e responde 201 com o registro.
7. O app mostra "Registrado: Café · R$ 15,00" e atualiza o cartão "Último registro".

```
 Celular / Navegador
 ┌────────────────────────────┐
 │ App (Expo + React Native)  │
 │ Início · Histórico         │
 └─────────────┬──────────────┘
               │ HTTP (fetch, multipart)
               ▼
 ┌────────────────────────────┐
 │ API FastAPI (Python)       │
 └──┬──────────┬──────────┬───┘
    │          │          │
    ▼          ▼          ▼
 OpenAI     DeepSeek    Postgres
 transcreve  só reescreve  financial_records
 decide      a frase
 extrai      (só no fallback)
```

O app fala só com a API; a API é quem conversa com a OpenAI, com o DeepSeek (apenas se a primeira análise reprovar) e com o Postgres.

## Tecnologias por camada

| Camada | Tecnologias principais |
| --- | --- |
| Frontend | Expo SDK 58, React Native 0.88, React 19.3, TypeScript strict, React Navigation 7, `expo-audio`, `react-native-web` |
| Backend | Python 3.12, FastAPI, SQLAlchemy async (asyncpg), Pydantic, Alembic, cliente `openai` |
| Inteligência artificial | OpenAI (`gpt-transcribe`, `gpt-6-luna` em Decisions e Responses API) e DeepSeek (`deepseek-flash`, só reescrita) |
| Banco | Postgres 18, tabela `financial_records` |
| Infraestrutura | Docker Compose (local) e Hospede Aqui (publicação) |

## Divisão da apresentação

A divisão abaixo segue as três partes do relatório; os tempos são uma sugestão para cerca de 30 minutos e podem ser ajustados.

| Apresentador | Tema | O que mostrar | Tempo sugerido |
| --- | --- | --- | --- |
| Sabrina | Estrutura, navegação, telas e visual | Pastas, dependências, React Navigation, Início e Histórico, componentes, `StyleSheet`, cores e ícones | 8 min |
| Helio | Gravação, interação, animação e estado | `expo-audio`, `useVoiceRecorder`, botão de segurar, `Animated`, `useState`/`useRef`, DevPanel, bug do toque, testes | 10 min |
| Thiago | Backend, integração e hospedagem | Rotas, pipeline de voz com IA, banco e migrations, `fetch`/multipart/CORS, deploy | 12 min |

O elo entre as partes está no fluxo acima: Sabrina mostra o que o usuário vê, Helio mostra como o toque vira áudio, e Thiago mostra o caminho do áudio até o registro.

## Parte do Thiago: backend e integração

O backend recebe o áudio, usa IA para entender a frase, calcula o valor com regras próprias e grava no Postgres; o frontend só envia o áudio com `fetch` e mostra a resposta.

### Camadas do backend

O fluxo segue sempre a mesma direção: `routers` → `services` → `repositories` → `models`, com `clients` para as IAs ao lado dos services.

| Camada (`backend/app/`) | Papel |
| --- | --- |
| `routers/` | Recebe HTTP, valida a entrada, chama o serviço e devolve a resposta |
| `services/` | Regra de negócio e orquestração do pipeline de voz |
| `repositories/` | Só SQL: criar e listar registros |
| `models/` | Mapeamento da tabela `financial_records` |
| `schemas/` | Formato de entrada e saída (Pydantic) |
| `clients/` | Clientes HTTP das IAs (OpenAI e DeepSeek) |
| `core/` | Configuração, formato de erro e tabela de preços |
| `db/` | Engine e sessão assíncrona |

### FastAPI: `app/main.py`

O arquivo faz quatro coisas:

1. **Lifespan:** ao subir, cria um cliente OpenAI e um DeepSeek e guarda em `app.state`; ao desligar, fecha os dois.
2. **CORS:** libera o frontend com `allow_origins=settings.cors_origin_list()`.
3. **Handler de erro único:** toda `AppError` vira `{"error": {"code": ..., "message": ...}}`.
4. **Rotas:** inclui os routers `health`, `financial_records` e `voice_records`.

O front sempre recebe `error.code` e `error.message`, e o status HTTP indica a gravidade.

### Configuração (`app/core/config.py`)

A classe `Settings` usa `pydantic-settings` e lê do ambiente e do arquivo `backend/.env`, que é ignorado pelo Git.

| Variável | Padrão | O que faz |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://...` | Conexão do banco da API |
| `OPENAI_API_KEY` | vazio | Transcrição, decisão e extração |
| `DEEPSEEK_API_KEY` | vazio | Só o fallback de reescrita |
| `CORS_ORIGINS` | `http://localhost:8081` | Origens do frontend, separadas por vírgula |
| `DECISION_THRESHOLD` | `0.6` | Nota mínima para aceitar a frase |
| `MAX_AUDIO_MB` | `10` | Tamanho máximo do áudio |
| `AI_TIMEOUT_SECONDS` | `15` | Timeout de cada chamada às IAs |
| `EXTRACTION_MODEL` | `gpt-6-luna` | Modelo da extração; `gpt-4o-mini` é o substituto |
| `APP_ENV` | `production` | `development` liga o DEV TOOLS |

### Rotas

**`GET /health`** confere o banco com `SELECT 1` e responde `{"status": "ok"}`. Se o banco cair, responde 503 `DB_UNAVAILABLE`.

**`GET /api/financial-records`** aceita `limit` (padrão 50, de 1 a 100), `offset` (padrão 0) e `q` (busca por nome do item). Exemplo de resposta:

```json
{
  "items": [
    {
      "id": "3f2a...",
      "type": "expense",
      "category": "food",
      "category_label": "Alimentação",
      "item": "café",
      "quantity": "3",
      "unit_price": "5.00",
      "total": "15.00",
      "currency": "BRL",
      "transcript": "comprei três cafés de cinco reais",
      "normalized_text": null,
      "created_at": "2026-10-31T12:00:00Z"
    }
  ],
  "limit": 20,
  "offset": 0
}
```

Os valores monetários trafegam como **strings decimais** (`"5.00"`, nunca `5.0`), para não perder precisão no transporte.

**`POST /api/voice-records`** recebe `multipart/form-data` com o campo `file` (o áudio) e o campo opcional `duration_ms`. Responde 201 com o registro criado.

```bash
curl -X POST http://localhost:8000/api/voice-records \
  -F "file=@audio.m4a;type=audio/m4a" -F "duration_ms=3200"
```

| Caso | HTTP | `code` |
| --- | --- | --- |
| Sem arquivo | 400 | `AUDIO_MISSING` |
| Formato fora da lista | 415 | `AUDIO_UNSUPPORTED` |
| Maior que `MAX_AUDIO_MB` | 413 | `AUDIO_TOO_LARGE` |
| Frase sem sentido | 422 | `NOT_UNDERSTOOD` |
| Frase sem dinheiro | 422 | `NOT_FINANCIAL` |
| IA fora do ar | 503 | `AI_UNAVAILABLE` |
| Banco fora do ar | 503 | `DB_UNAVAILABLE` |

Formatos aceitos: `audio/m4a`, `audio/x-m4a`, `audio/mp4`, `audio/aac`, `audio/webm`, `video/webm`, `audio/mpeg`, `audio/wav` e `audio/ogg`.

### O pipeline de voz

O orquestrador é `VoiceRecordService.register()` em `services/voice_record_service.py`; cada etapa vive em um arquivo próprio.

1. **Validação** (`routers/voice_records.py`): confere o tipo de áudio e o tamanho.
2. **Transcrição** (`transcription_service.py`): modelo `gpt-transcribe` em português, com um prompt que ensina gírias ("conto", "pila") e `keywords` com os rótulos das categorias para acertar palavras como "mercado" e "farmácia". Transcrição vazia vira 422 `NOT_UNDERSTOOD`.
3. **Análise em paralelo** (`voice_record_service.py`, `analyze()`): a decisão e a extração rodam ao mesmo tempo com `asyncio.gather`, para a resposta voltar mais rápido.
4. **Critério de aceite** (`record_rules.py`, `is_accepted()`).
5. **Fallback** (`rewrite_service.py`): se reprovar, o DeepSeek reescreve a frase e o passo 3 roda mais uma vez.
6. **Cálculo do total** (`record_rules.py`): feito pelo backend, em `Decimal`.
7. **Reconciliação** do tipo com a categoria.
8. **Gravação** no Postgres e resposta 201.

```
 áudio recebido
      │
 1. Validação (mime e tamanho) ──────── falha ──▶ 4xx
      │
 2. Transcrição (gpt-transcribe) ────── vazia ──▶ 422 NOT_UNDERSTOOD
      │
 3. Análise em paralelo (asyncio.gather)
      ├─ Decisões: plausible, is_financial, type, category
      └─ Extração: item, quantity, unit_price, stated_total
      │
 4. Aceite? (probabilidades ≥ 0,6 e extração válida)
      │ sim                                  │ não (1ª vez)
      │                                      ▼
      │                          5. DeepSeek reescreve a frase
      │                                      │
      │                          volta ao passo 3 (uma única vez)
      │                                      │ reprovou de novo
      │                                      ▼
      │                          422 NOT_UNDERSTOOD / NOT_FINANCIAL
      ▼
 6. Total em Decimal (backend, nunca a IA)
      │
 7. Reconciliação tipo × categoria
      │
 8. Grava no Postgres ──▶ 201 com o registro
```

A frase só vira erro 422 depois de duas análises; a segunda usa o texto reescrito pelo DeepSeek, que não decide nada.

#### Decisão: as quatro perguntas

Uma única chamada à Decisions API (`decision_service.py`, modelo `gpt-6-luna`) faz quatro perguntas:

| Pergunta | Tipo | O que mede |
| --- | --- | --- |
| `plausible` | predicate | A frase é fala coerente em português? |
| `is_financial` | predicate | Descreve gasto ou ganho com valor? |
| `type` | choice `income`/`expense` | O dinheiro entrou ou saiu? |
| `category` | choice, 24 códigos | Qual categoria da lista fixa? |

Os predicates devolvem uma probabilidade; o limiar `DECISION_THRESHOLD` (0,6) funciona como nota de corte.

#### Extração estruturada

`extraction_service.py` chama a Responses API com `json_schema` strict e quatro campos: `item`, `quantity`, `unit_price` e `stated_total`. A IA só **preenche campos**; nunca calcula. A regra do prompt: "N X de Y" sem palavra de total vale quantidade N e unitário Y; com palavra de total ("em", "no total", "ao todo") vale `stated_total`.

#### Critério de aceite e fallback

A frase é aceita se `plausible` e `is_financial` forem pelo menos 0,6 **e** a extração tiver `item` não vazio, `quantity > 0` e um preço unitário ou total maior que zero.

Se reprovar, entra o fallback: `deepseek-flash` (`temperature=0`, thinking desligado) **só reescreve a frase em português padrão**, mantendo números e valores. Ele não classifica nem extrai. A frase reescrita passa pela análise **uma única vez**; reprovando de novo, o backend responde 422 com uma mensagem amigável (`NOT_FINANCIAL` se a frase fez sentido mas não tem dinheiro, `NOT_UNDERSTOOD` nos demais casos).

#### Cálculo do total em `Decimal`

O total é sempre calculado pelo backend (`resolve_prices()` e `compute_amounts()`), nunca pela IA:

- **Unitário conhecido:** `total = quantity × unit_price`. "3 cafés de 5 reais" resulta em `3 × 5.00 = 15.00`.
- **Só o total dito:** `total = stated_total` e `unit_price = total / quantity`. "Gastei 30 em 3 cervejas" resulta em total `30.00` e unitário `10.00`.

Quantidades têm 3 casas decimais, dinheiro tem 2, com arredondamento `ROUND_HALF_UP`. Se a IA tratar um total como unitário (quantidade maior que 1 e frase com palavra de total), `resolve_prices()` corrige para não multiplicar duas vezes.

#### Reconciliação e categorias

A escolha `type` é a autoridade. Se a categoria for do outro tipo (por exemplo, `income` com `food`), vira `other_expense` ou `other_income`. São 17 categorias de despesa (`food`, `groceries`, `housing`, `utilities`, `transport`, `health`, `education`, `leisure`, `shopping`, `clothing`, `personal_care`, `pets`, `subscriptions`, `travel`, `taxes_fees`, `gifts_donations`, `other_expense`) e 7 de receita (`salary`, `freelance`, `sales`, `investments`, `refunds`, `gifts_received`, `other_income`).

### Clients de IA

Os dois usam a mesma classe `AsyncOpenAI`, com `max_retries=1` e o timeout da configuração. O DeepSeek é acessado pela API compatível com a OpenAI, só trocando a URL base:

```python
AsyncOpenAI(api_key=settings.openai_api_key)
AsyncOpenAI(api_key=settings.deepseek_api_key, base_url="https://api.deepseek.com")
```

As instâncias são criadas uma vez no `lifespan` e reutilizadas.

### Banco de dados

O acesso usa SQLAlchemy assíncrono com `asyncpg` (`pool_pre_ping=True`) e uma sessão por requisição, entregue pela dependência `get_session()`.

| Coluna (`financial_records`) | Tipo | Por quê |
| --- | --- | --- |
| `id` | UUID, chave primária | Identificador sem sequência |
| `type` | String(10), `income` ou `expense` | Tipo autoritativo |
| `category` | String(40) | Código da lista fixa |
| `item` | String(120) | Nome do produto |
| `quantity` | Numeric(12,3) | Aceita quantidade fracionada (2,5 kg) |
| `unit_price` | Numeric(12,2) | Dinheiro com centavos |
| `total` | Numeric(14,2) | Dinheiro com centavos |
| `currency` | CHAR(3), padrão `BRL` | Moeda fixa por enquanto |
| `transcript` | Text | Frase transcrita |
| `normalized_text` | Text, opcional | Frase reescrita pelo DeepSeek, se houve fallback |
| `created_at` | timestamptz, padrão `now()` | Ordena do mais recente para o mais antigo |

O modelo usa `Numeric`/`Decimal` e não `float` porque dinheiro em ponto flutuante acumula erro de arredondamento (`0.1 + 0.2 = 0.30000000000000004`). Checks no banco garantem `quantity`, `unit_price` e `total` maiores que zero.

O repositório tem `create()`, `list_records()` (ordena por `created_at` decrescente, filtra com `item ILIKE '%q%'`, aplica `limit` e `offset`) e `count_records()`. A busca é por trecho do item, sem distinção de maiúsculas, e a paginação por `limit`/`offset`, o suficiente para o MVP.

### Alembic: migrations

A migration `0001_create_financial_records.py` cria a extensão `pgcrypto`, a tabela com os checks e o índice em `created_at`. Ela é idempotente: inspeciona o banco antes e, se a tabela já existe, só garante o índice e sai sem erro. O `CMD` do `Dockerfile` roda `alembic upgrade head && uvicorn app.main:app`, então toda subida do backend aplica a migration antes de abrir a API.

### DEV TOOLS no backend

- **Gate:** só com `APP_ENV=development` no servidor. Nenhum header ou campo do cliente liga o debug. Fora desse modo, um coletor `NullTrace` não faz nada.
- **Coletor:** `PipelineTrace` (`pipeline_trace.py`) mede o tempo de cada etapa e recebe a resposta dos provedores. Preços em `core/pricing.py` e custo em `cost_calculator.py`, em `Decimal`.
- **O que entra no `debug`:** tempos por etapa, transcrição, probabilidades da decisão, saída da extração, aceite ou fallback, custo em USD e a fórmula final (`3 × 5.00 = 15.00`). O campo vem no nível raiz do 201 e também dos erros 422 e 503 do pipeline.
- **O que não entra:** chaves de API, headers, mensagens de erro dos provedores e prompts. A montagem usa uma lista de campos permitidos, e o debug nunca é gravado no banco.

### Testes com pytest

São 10 arquivos e 57 testes: unit (regras, custo, trace, orquestração), db (Postgres real), api (contrato das rotas) e migrations (marcado, fora da suíte padrão). Nenhum teste chama OpenAI ou DeepSeek reais: usam fakes em `tests/support/fakes.py`. A suíte padrão roda com `docker compose run --rm backend pytest -m "not migrations" -q`.

### Como o front consome a API

O `services/api.ts` define o endereço e a função genérica `request<T>`:

```ts
export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, options);
  if (!response.ok) { ... throw new ApiError(code, message, status, debug) }
  return (await response.json()) as T;
}
```

- **`EXPO_PUBLIC_API_URL`:** o Expo só embute no app as variáveis com esse prefixo, no momento em que o Metro empacota. Por isso mudar o endereço exige novo build, e por isso **nunca** se coloca chave secreta ali: tudo que tem o prefixo fica visível para quem abrir o app.
- **`ApiError`:** quando `response.ok` é falso, o front lê o JSON do erro (dentro de `try/catch`, porque o corpo pode não ser JSON) e lança `ApiError` com `code`, `message`, `status` e `debug`.
- **Falha de rede:** servidor fora do ar ou CORS bloqueado fazem o `fetch` lançar um `TypeError`, que não é `ApiError`; a tela mostra "Sem conexão com o servidor".
- **Mensagens:** o front não escolhe texto pelo código do erro; qualquer `ApiError` mostra a `message` que veio do backend, então as mensagens em português ficam todas no servidor.

#### Envio do áudio (`recordService.ts`)

`getRecords({ q, limit, offset })` monta a query com `URLSearchParams`. `sendVoiceRecord(uri, durationMs)` monta um `FormData`:

```ts
const formData = new FormData();
if (Platform.OS === "web") {
  const response = await fetch(uri);
  const blob = await response.blob();
  formData.append("file", blob, "audio.webm");
} else {
  const audioFile = { uri, name: "audio.m4a", type: "audio/m4a" };
  formData.append("file", audioFile as unknown as Blob);
}
if (durationMs !== undefined) formData.append("duration_ms", String(Math.round(durationMs)));
return request("/api/voice-records", { method: "POST", body: formData });
```

Na web, o `uri` é uma URL `blob:`, então o código busca o conteúdo e o anexa como arquivo `audio.webm`. No celular, o React Native aceita um objeto `{ uri, name, type }` no lugar do arquivo, e o `as unknown as Blob` só acalma o TypeScript. O código **não define o cabeçalho `Content-Type`** de propósito: o `fetch` precisa gerar sozinho o `multipart/form-data; boundary=...` com o separador correto.

#### Tipos e dinheiro no front

O tipo `FinancialRecord` tem `quantity`, `unit_price` e `total` como `string`. O front só exibe: `formatCurrency` converte `"15.00"` em `R$ 15,00` com `Intl.NumberFormat`. Quem calcula é o backend.

#### O que o front faz com cada resposta

| Resposta | O que a tela faz |
| --- | --- |
| 201 | Troca o "Último registro", mostra "Registrado: Café · R$ 15,00" e volta ao repouso em 2,5 s |
| 422 ou 503 | Mostra em vermelho a mensagem amigável do backend e a dica "Segure para tentar de novo" |
| Falha de rede | Mostra "Sem conexão com o servidor" |

#### CORS visto do navegador

CORS é uma regra do navegador: uma página de uma origem só lê a resposta de outra origem se a API autorizar. App nativo (Expo Go) não tem essa regra. O `CORSMiddleware` do backend lê as origens permitidas da variável `CORS_ORIGINS`. Se o app web abrir em um endereço que não está na lista, o navegador bloqueia a resposta, o `fetch` lança `TypeError` e o app mostra "Sem conexão com o servidor" mesmo com o servidor no ar.

### Do toque ao registro na tela

1. O `Pressable` do `RecordButton` dispara `onPressIn`; o botão fica vermelho e pulsa.
2. A `HomeScreen` chama `start()`; o gravador já estava preparado, então `recorder.record()` inicia rápido e o estado vira `recording`.
3. O usuário solta o dedo; `onPressOut` chama `finishRecording()` e o estado vira `processing`.
4. O hook para o gravador e devolve `{ uri, durationMs }`; menos de 700 ms é descartado.
5. `sendVoiceRecord` monta o `FormData` (web ou nativo).
6. `request` envia o `POST /api/voice-records` com `fetch`, sem `Content-Type` manual.
7. O backend valida, transcreve, decide e extrai em paralelo, calcula o total em `Decimal` e grava no Postgres.
8. O backend responde 201 com o registro.
9. A tela chama `setLastRecord`, mostra "Registrado: ..." e, 2,5 s depois, volta ao repouso e prepara a próxima gravação.
10. Ao abrir o Histórico, `useFocusEffect` busca a lista e o registro aparece lá.

### Decisões de design que valem explicar

- **`Decimal` e não `float`:** dinheiro exige exatidão de centavos; o banco usa `Numeric` e o Python usa `Decimal` com arredondamento explícito.
- **Separar decisão de extração:** a decisão é um julgamento probabilístico com nota de corte; a extração é um preenchimento com schema. Separadas, rodam em paralelo, falham com mensagens próprias e são testadas isoladamente.
- **Fallback que só reescreve:** o modelo barato é bom para normalizar texto ("três de dez conto" vira "3 por 10 reais"), mas não para julgar ou extrair valores. Ele limpa a frase e quem decide continua sendo o modelo principal, uma única vez.

### Pontos para explicar ao vivo

- O caminho do áudio: botão no app, `multipart`, validação de formato e tamanho no router.
- A transcrição em português com `keywords` das categorias.
- As quatro perguntas da Decisions API e o limiar 0,6 como nota de corte.
- A extração com `json_schema` strict: a IA preenche campos e nunca calcula.
- O `asyncio.gather`: decisão e extração em paralelo para a resposta voltar rápido.
- O total em `Decimal`, nos dois casos (unitário × quantidade e só total dito).
- A reconciliação tipo × categoria e as 24 categorias.
- O fallback DeepSeek que só reescreve e dá uma segunda chance.
- O formato de erro único e a tabela de status.
- O DEV TOOLS: tempos, tokens e custo sem vazar chave.

### Perguntas que a banca pode fazer

**Por que não deixar a IA calcular o total?** Modelo de linguagem erra conta e arredondamento; o backend calcula em `Decimal` com uma regra auditável e testada.

**O que acontece se eu falar "oi"?** `is_financial` fica abaixo de 0,6, o fallback reescreve sem sucesso e a API responde 422 `NOT_FINANCIAL` com mensagem amigável.

**E se eu falar "gastei 30 em 3 cervejas"?** A extração devolve `stated_total=30` e o backend deriva `unit_price=10.00` dividindo pela quantidade.

**Por que dois modelos (OpenAI e DeepSeek)?** A OpenAI decide e extrai; o DeepSeek, mais barato, só normaliza o texto na segunda tentativa, reduzindo o custo.

**Onde fica a chave da OpenAI?** Só no `backend/.env` (ignorado pelo Git) e nas variáveis do servidor; nunca no frontend nem no repositório.

**Como testam sem gastar crédito de IA?** Com fakes que imitam as respostas e um Postgres de teste real; os 57 testes não fazem nenhuma chamada externa.

## Hospedagem e execução

O projeto roda de duas formas: localmente com Docker Compose e publicado na Hospede Aqui, com o banco, o backend e o frontend como três serviços separados.

### Execução local com Docker Compose

| Serviço | Porta | O que faz |
| --- | --- | --- |
| `db` | 5432 | Postgres 18 com volume persistente |
| `backend` | 8000 | FastAPI; roda `alembic upgrade head` antes do `uvicorn` |
| `frontend` | 8081 | Expo na web, com o código montado como volume |
| `checks` | não sobe sozinho | Roda `expo lint`, `tsc --noEmit` e `npm test` do frontend |

Comandos principais, na raiz do projeto:

```bash
docker compose up -d --build backend
docker compose up -d --build frontend
docker compose run --rm checks
docker compose run --rm backend pytest -m "not migrations" -q
```

### Publicação na Hospede Aqui

Tudo fica em um workspace próprio chamado `vocal-finance`, na região de São Paulo.

| Serviço | Como foi publicado | Endereço |
| --- | --- | --- |
| Banco `vocal-db` | Postgres 18 gerenciado, acessível só pela rede interna | interno |
| Backend `vocal-backend` | Upload do código e build com o `Dockerfile` do projeto, porta 8000, health check em `/health` | https://vocal-backend.hospedeaqui.app |
| Frontend `vocal-frontend` | Build com `expo export --platform web` e arquivos servidos por nginx, com fallback para `index.html` | https://vocal-frontend.hospedeaqui.app |

O frontend publicado é um site estático, diferente do servidor de desenvolvimento do Expo. Como `EXPO_PUBLIC_API_URL` é embutida no bundle durante o build, o endereço do backend fica gravado no site, e mudar de endereço exige novo build.

O backend lê estas variáveis de ambiente do serviço: `DATABASE_URL` (com o driver `postgresql+asyncpg`), `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `CORS_ORIGINS` (o endereço do frontend) e `APP_ENV`. As chaves ficam só nas variáveis do serviço e não vão no código enviado.

No momento da escrita, o `APP_ENV` do backend publicado está em `development`, então o painel DEV TOOLS aparece na Home e a API devolve o campo `debug`. Para voltar ao modo normal, troque `APP_ENV` para `production` e refaça o build do frontend com `EXPO_PUBLIC_APP_ENV=production`.

### Expo Go e o APK

O desenvolvimento foi web primeiro. No celular, o projeto usa só módulos que já vêm no Expo Go, sem código nativo próprio e sem development build. As pastas `ios/` e `android/`, quando geradas, nunca são editadas à mão. No Expo Go, `localhost` aponta para o próprio celular, então `EXPO_PUBLIC_API_URL` precisa ser o IP do computador na rede ou o endereço público do backend. A geração do APK com EAS é a última etapa e ainda não foi feita.

## Glossário e perguntas gerais da banca

Os termos abaixo aparecem nas três partes; cada um tem uma frase para dizer em voz alta.

### Glossário de React Native

| Termo | Em uma frase |
| --- | --- |
| Componente | Função que devolve pedaços de interface (JSX); pode receber props e ter estado |
| Props | Dados que o componente pai passa para o filho, somente leitura |
| `useState` | Hook que guarda um valor; quando muda, o componente é redesenhado |
| `useRef` | Hook que guarda um valor sem redesenhar a tela; lê o valor atual na hora |
| `useEffect` | Hook que roda código depois de desenhar; a função devolvida faz a limpeza |
| `useFocusEffect` | Hook do React Navigation que roda toda vez que a tela ganha foco |
| `StyleSheet.create` | Declara estilos nomeados, parecidos com CSS, no fim do arquivo |
| `View`, `Text` | Blocos básicos: caixa de layout e texto |
| `Pressable` | Componente que detecta toques: `onPressIn`, `onPressOut`, `onPress`, `onLongPress` |
| `FlatList` | Lista virtualizada: monta só os itens visíveis |
| `Animated` | API de animação: `Animated.Value`, `timing`, `loop`, `sequence` |
| `Platform` | Informa se o código roda em `web`, `ios` ou `android` |
| Expo | Plataforma sobre o React Native que cuida de build, módulos e do Expo Go |
| Expo Go | App que roda o projeto no celular sem gerar APK |
| Metro | Empacotador que junta o código JavaScript e embute as `EXPO_PUBLIC_*` |
| `react-native-web` | Traduz componentes do React Native para HTML, para rodar no navegador |
| React Navigation | Biblioteca de rotas: Stack empilha telas, Tabs alterna entre abas |
| `SafeAreaView` | Mantém o conteúdo fora do notch e da barra de status |
| TypeScript `strict` | JavaScript com tipos checados; `strict` liga as checagens mais rígidas |
| `fetch` | API nativa para chamar HTTP, sem biblioteca extra |
| `multipart/form-data` | Formato de envio de arquivos junto com campos de texto |
| CORS | Regra do navegador que exige a API autorizar a origem da página |

### Perguntas gerais

**O que é o Expo e por que usamos?** É uma plataforma sobre o React Native que simplifica o build e dá acesso a módulos prontos, como o `expo-audio`; com o Expo Go dá para testar no celular sem instalar nada além do app.

**O mesmo código roda no celular e no navegador?** Sim, graças ao `react-native-web`. Por isso o código tem alguns trechos com `Platform.OS === "web"`, como o envio do áudio e os estilos do botão.

**O app funciona sem internet?** Não. Gravar, listar e buscar dependem do backend, que por sua vez depende das APIs de IA e do banco.

**O que ficou fora do MVP?** Login, orçamento, gráficos e a geração do APK final.

**Qual foi a maior dificuldade?** O botão de segurar: com a ponta do dedo, o app tratava o toque como um clique e demorava a reagir. A solução foi preparar o gravador antes do toque e dar feedback visual imediato (história completa na parte do Helio).
