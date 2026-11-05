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

## Parte do Helio: gravação, interação, animação e estado

O coração do app é um botão de segurar: `onPressIn` começa a gravar, `onPressOut` envia, e uma máquina de estados (`idle` → `recording` → `processing` → `success` ou `error`) controla o que a tela mostra.

### Gravação com `expo-audio`

O fluxo tem quatro passos:

1. **Permissão:** `AudioModule.requestRecordingPermissionsAsync()` devolve `{ granted }`. O texto do pedido vem do plugin em `app.json`.
2. **Modo de áudio:** `setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true })`.
3. **Preparar:** `recorder.prepareToRecordAsync()` deixa o gravador pronto.
4. **Gravar e parar:** `recorder.record()` inicia; `await recorder.stop()` finaliza e preenche `recorder.uri`, o endereço do arquivo gravado.

O `recorder` vem de `useAudioRecorder(recordingOptions)`. As opções partem de `RecordingPresets.HIGH_QUALITY` e ajustam `numberOfChannels: 1` (mono) e `bitRate: 48000`. Áudio mono e de taxa baixa gera um arquivo pequeno para enviar.

|  | Web | Nativo (Expo Go) |
| --- | --- | --- |
| Como grava | API `MediaRecorder` do navegador (`getUserMedia`) | Módulo nativo do `expo-audio` |
| O que é o `uri` | URL `blob:...` criada com `URL.createObjectURL` | Arquivo local no aparelho |
| Nome enviado | `audio.webm` | `audio.m4a` |

No navegador, o microfone só funciona em contexto seguro (HTTPS ou `localhost`), uma regra geral dos navegadores.

### Hook `useVoiceRecorder`

O hook (`hooks/useVoiceRecorder.ts`) esconde os detalhes da gravação e devolve `{ prepare, start, stop, durationMs }`.

| Item | O que é |
| --- | --- |
| `recorderState` | `useAudioRecorderState(recorder, 200)`: lê o estado a cada 200 ms; `durationMs` é o cronômetro da tela |
| `preparationRef` | `useRef` que guarda a preparação em andamento ou concluída |
| `prepare()` | Pede permissão, configura o áudio e prepara o gravador; devolve `false` se o microfone foi negado. Se já há preparação, devolve a mesma promessa |
| `start()` | Aguarda `prepare()`, zera a ref e chama `recorder.record()` |
| `stop()` | Para o gravador e devolve `{ uri, durationMs }`, ou `null` se não houver arquivo |

Quem decide quando preparar é a `HomeScreen`: ao focar a aba (`useFocusEffect`) e ao fim de cada gravação. Efeito colateral aceito: na web o `MediaRecorder` mantém o microfone aberto enquanto a Home está parada, então o navegador mostra o indicador de microfone.

### `RecordButton`: o botão de segurar

A interação é "pressionar e falar, soltar para enviar", como um rádio: define começo e fim da gravação sem precisar de dois botões. Props: `state` (`idle`, `recording`, `processing`, `success`), `onPress`, `onPressIn`, `onPressOut`.

- **`Pressable`** com `onPressIn` e `onPressOut`; um estado local `isPressed` registra se o dedo está sobre o botão.
- **Feedback imediato:** `isRecording = state === "recording" || (isPressed && state === "idle")`. O botão fica vermelho e pulsa assim que o dedo encosta, sem esperar a gravação iniciar.
- **`hitSlop`** de 24 px e **`pressRetentionOffset`** de 80 aumentam a área de toque e a tolerância a pequenos deslizes do dedo.
- **`onLongPress` vazio:** no React Native Web, ter esse handler impede que o toque longo abra o menu do navegador e termine o gesto.
- **Estilos web** (só quando `Platform.OS === "web"`): `touchAction: "none"`, `userSelect: "none"` e `WebkitTouchCallout: "none"`.
- **Conteúdo:** em `processing` mostra `ActivityIndicator` e o botão fica `disabled`; em `success`, um check verde; senão, o ícone de microfone.
- **Acessibilidade:** `accessibilityRole="button"` e `accessibilityLabel="Segure para gravar"`.

### Animação do pulso

`pulse` é um `Animated.Value(1)` criado com `useState(() => new Animated.Value(1))`. Um `useEffect` roda enquanto `isRecording` e liga um `Animated.loop` de `Animated.sequence`: escala de 1 para 1,18 e de volta, 600 ms cada. O círculo de borda vermelha usa `transform: [{ scale: pulse }]`. A função de limpeza do efeito (`return () => animation.stop()`) para o loop, e fora da gravação o valor volta a 1.

O código usa `useNativeDriver: false`, então a animação roda no JavaScript. Na web não existe driver nativo, e o pulso é leve.

### Estados da `HomeScreen`

| Estado (`useState`) | Significado |
| --- | --- |
| `status` | `idle`, `recording`, `processing`, `success` ou `error`: a máquina de estados da voz |
| `feedback` | Texto de sucesso ou erro abaixo do botão |
| `lastRecord` | Último registro financeiro |
| `isLoadingLastRecord`, `hasLastRecordError` | Spinner e erro do cartão "Último registro" |
| `lastDebug` | Campo `debug` da última resposta (alimenta o DevPanel) |
| `clientTotalMs` | Tempo total medido no celular entre enviar e receber |

Quatro `useRef` guardam valores que as funções assíncronas precisam ler na hora, sem esperar uma nova renderização e sem causar re-render: `isPressingRef` (o dedo ainda está no botão?), `isStartingRef`, `isRecordingRef` e `isFinishingRef`. Eles evitam toques duplicados e corridas entre "iniciar" e "soltar".

```
idle ──pressIn──▶ recording ──solta──▶ processing ──201──▶ success ──2,5 s──▶ idle
                      │                      │
                      └── erro / curto ────┴── 422/503/rede ──▶ error ──novo toque──▶ recording
```

Textos de estado: `idle` mostra "Segure para falar"; `recording`, o cronômetro `mm:ss`; `processing`, "Entendendo seu gasto…".

### Funções e efeitos da tela

- **`startRecording`:** ignora se já está iniciando, gravando ou processando. Chama `await start()`. Se o microfone foi negado, mostra "Permita o acesso ao microfone para registrar por voz". Se o dedo já saiu quando o início terminou, descarta e pede "Segure o botão enquanto fala". Senão, muda para `recording`.
- **`handleRecordEnd`** (`onPressOut`): marca que o dedo saiu e, se está gravando, chama `finishRecording`.
- **`finishRecording`:** muda para `processing`, chama `stop()` e descarta gravações com menos de 700 ms (toque acidental). Senão, chama `sendVoiceRecord` e, no sucesso, guarda o registro e mostra "Registrado: Café · R$ 15,00". Se o erro for `ApiError`, mostra a mensagem do backend; qualquer outro erro vira "Sem conexão com o servidor". O `finally` libera a trava e prepara a próxima gravação.
- **`useFocusEffect`:** ao entrar na aba, recarrega o último registro (`getRecords({ limit: 1 })`) e prepara o gravador.
- **`useEffect` com `status === "recording"`:** após 60 s, chama `finishRecording` sozinho (limite de gravação).
- **`useEffect` com `status === "success"`:** após 2,5 s, volta para `idle`.

O padrão `try/catch/finally` aparece no carregamento do último registro e nas funções de gravação: o `finally` sempre desliga o spinner ou a trava.

### DevPanel e DEV TOOLS

`utils/appEnv.ts` expõe `isDevToolsEnabled()`, que é verdadeira quando `EXPO_PUBLIC_APP_ENV === "development"`. O painel é colapsável e mostra tempo por etapa, tokens e custo, transcrição bruta, saídas da IA e o cálculo final do total.

São duas chaves: o backend também precisa estar em `APP_ENV=development`, porque só ele inclui o campo `debug` na resposta. O front não consegue ligar o debug sozinho. Se só o front estiver ligado, o painel avisa "Sem dados de debug". Nenhuma chave de API vai para o front: variáveis `EXPO_PUBLIC_*` são públicas.

### O bug da ponta do dedo: uma história de aprendizado

**O que o usuário viu:** no celular, com a ponta do dedo o app parecia entender só um clique e mostrava "Segure o botão enquanto fala"; com o polegar inteiro funcionava. Além disso, era preciso segurar alguns segundos até a animação vermelha aparecer.

**Causa 1, o atraso:** a cada toque, o `start()` pedia a permissão e preparava o gravador, e só depois o estado virava `recording`. Na web, isso são duas chamadas a `getUserMedia` e uma listagem de dispositivos por toque, sem nada mudar na tela. Quem soltava o dedo antes de terminar caía no caminho "Segure o botão enquanto fala".

**Causa 2, o gesto cancelado:** o `Pressable` do React Native Web permite que a rolagem do `ScrollView` assuma o gesto com um movimento pequeno do dedo, cancelando o toque. Sem `onLongPress`, o toque longo também pode abrir o menu do navegador ou selecionar texto. A ponta do dedo é menos estável e dispara isso mais. Essa segunda causa foi deduzida lendo o código do React Native Web, não reproduzida em aparelho real.

**Correção:**

1. `prepare()` no hook, chamado ao focar a tela e após cada gravação; no toque sobra só `recorder.record()`.
2. Feedback imediato: o botão fica vermelho e pulsa no `onPressIn`.
3. `hitSlop`, `pressRetentionOffset` e `onLongPress` vazio.
4. Estilos web: `touchAction: none`, `userSelect: none`, `WebkitTouchCallout: none`.

**Lição:** o que acontece dentro do gesto deve ser mínimo; o trabalho pesado vai para antes, e sempre se dá feedback visual imediato. A validação da correção em aparelho real ainda está pendente.

### Testes com Jest

O `package.json` usa o preset `jest-expo`, com `@testing-library/react-native` (`render`, `screen`, `fireEvent`) e timers falsos onde há tempo. São **12 suítes e 53 testes**, todos passando em `docker compose run --rm checks`, que roda lint, `tsc --noEmit` e Jest.

| Suíte | Testes | O que cobre |
| --- | --- | --- |
| `HomeScreen.test.tsx` | 12 | Fluxo de voz: descarte de gravação curta, envio, erro da API, erro de conexão, permissão negada, corte em 60 s, DevPanel por ambiente |
| `RecordButton.test.tsx` | 9 | Estados do botão, feedback no `pressIn`, `hitSlop`, `onLongPress` |
| `useVoiceRecorder.test.ts` | 7 | `prepare` e `start` com `expo-audio` simulado |
| `DevPanel.test.tsx` | 5 | Resumo, seções, ausência de debug |
| `recordService.test.ts` | 4 | Query de listagem e envio web/nativo |
| Demais (7 suítes) | 16 | `api`, formatadores, `EmptyState`, `RecordCard`, `appEnv` |

Chamadas HTTP e `expo-audio` são simuladas; nenhum teste usa rede ou microfone reais. Não há testes de tela para o Histórico nem de navegação.

### Pontos para explicar ao vivo

- O botão é de segurar: `onPressIn` começa, `onPressOut` envia.
- `useRef` guarda valores que funções assíncronas precisam ler na hora, sem re-render.
- `prepare()` faz o trabalho pesado antes do toque, e o `record()` fica quase instantâneo.
- Feedback visual imediato no `onPressIn`.
- O pulso é um `Animated.loop` de `scale`; o `useEffect` liga e desliga, com limpeza no `return`.
- Gravações com menos de 700 ms são descartadas; com mais de 60 s, o app envia sozinho.
- O DevPanel só tem dados se front e backend estiverem em `development`.
- O bug da ponta do dedo teve duas causas e uma correção em três frentes.

### Perguntas que a banca pode fazer

**Por que `onPressIn`/`onPressOut` e não `onPress`?** `onPress` só dispara ao completar o toque, depois de soltar. Para "segurar enquanto fala" precisamos saber quando o dedo encosta e quando sai.

**Por que `useRef` e não `useState` para `isPressingRef`?** `useState` só vale na próxima renderização. A função assíncrona precisa saber agora se o dedo saiu, e a ref não re-renderiza.

**O que `useNativeDriver: false` significa?** A animação roda no JavaScript. No nativo, `true` rodaria na thread de interface; na web não há driver nativo.

**O que acontece se o usuário negar o microfone?** `prepare()` devolve `false` e a tela mostra "Permita o acesso ao microfone para registrar por voz". No próximo toque, o app pede de novo.

**O que impede enviar duas gravações ao mesmo tempo?** As refs `isFinishingRef`, `isStartingRef` e `isRecordingRef`, e o botão fica `disabled` em `processing`.

**O DevPanel pode vazar chave de API?** Não: o front nunca tem chave, e o backend monta o `debug` sem chaves e sem prompts.

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
