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

## Parte da Sabrina: estrutura, navegação, telas e visual

O frontend é um projeto Expo com três camadas bem separadas: rotas decidem qual tela aparece, telas juntam estado e componentes, e componentes desenham a interface. Tudo está em `frontend/`, escrito em TypeScript com `strict: true`.

### Estrutura de pastas

| Pasta (`frontend/src/`) | Papel |
| --- | --- |
| `routes/` | Só navegação: `StackRoutes.tsx` e `TabRoutes.tsx` |
| `screens/` | Uma tela inteira por arquivo: `HomeScreen.tsx`, `HistoryScreen.tsx` |
| `components/` | Peças visuais reaproveitáveis: `EmptyState`, `RecordCard`, `StatusMessage`, `RecordButton`, `DevPanel`, `JsonBlock` |
| `constants/` | Valores fixos de visual: `colors.ts`, `categoryStyles.ts` |
| `types/` | Tipos TypeScript: rotas, `FinancialRecord`, `ApiError`, `VoiceDebug` |
| `hooks/` | Lógica com estado reaproveitável: `useVoiceRecorder.ts` |
| `services/` | Conversa com o backend: `api.ts`, `recordService.ts` |
| `utils/` | Funções puras de formatação: moeda, data, debug, ambiente |

Na raiz de `frontend/` ficam `index.ts` (entrada), `App.tsx`, `app.json` (config do Expo), `package.json`, `tsconfig.json` e `eslint.config.js`. Os testes ficam ao lado do arquivo testado (`*.test.tsx`).

### Dependências: o que é do núcleo e o que importamos

O app usa o `fetch` nativo para HTTP (sem axios) e não tem biblioteca de estado (sem Redux ou Zustand): o estado é só `useState` e `useRef`.

| Pacote | Para que serve | Origem |
| --- | --- | --- |
| `react`, `react-native` | Componentes, hooks, `View`, `Text`, `FlatList`, `StyleSheet` | Núcleo |
| `expo` | Plataforma Expo: Metro, Expo Go, `registerRootComponent` | Núcleo Expo |
| `react-dom`, `react-native-web`, `@expo/metro-runtime` | Fazem o mesmo código rodar no navegador | Suporte web |
| `expo-audio` | Gravação de áudio e permissão de microfone | Módulo Expo |
| `expo-status-bar` | Cor da barra de status | Módulo Expo |
| `@expo/vector-icons` | Ícones (conjunto `Ionicons`) | Módulo Expo |
| `@react-navigation/native` | `NavigationContainer`, `useFocusEffect`, temas | Biblioteca importada |
| `@react-navigation/native-stack` | Navegador em pilha | Biblioteca importada |
| `@react-navigation/bottom-tabs` | Barra de abas inferior | Biblioteca importada |
| `react-native-safe-area-context` | `SafeAreaProvider`/`SafeAreaView`: respeita notch e barras | Biblioteca importada |
| `react-native-screens` | Telas nativas otimizadas; exigida pelos navegadores | Biblioteca importada |

Para desenvolvimento e testes: `jest` com o preset `jest-expo`, `@testing-library/react-native`, `typescript`, `eslint` e `eslint-config-expo`.

### Configuração do Expo (`app.json`)

- `scheme: "vocalfinance"` permite abrir o app por links `vocalfinance://`.
- O plugin `expo-audio` recebe o texto do pedido de permissão: "Permita o acesso ao microfone para registrar por voz".
- A orientação é sempre vertical (`portrait`).
- Os campos `owner` e `extra.eas.projectId` servem só para gerar o APK depois (EAS).

### Ponto de entrada e tema

`index.ts` chama `registerRootComponent(App)`, que registra o componente raiz no celular e na web. O `App.tsx` monta três camadas:

```tsx
<SafeAreaProvider>
  <StatusBar style="light" />
  <NavigationContainer theme={navigationTheme}>
    <StackRoutes />
  </NavigationContainer>
</SafeAreaProvider>
```

O `navigationTheme` parte do `DarkTheme` e troca as cores pelas de `constants/colors.ts`. O app é sempre escuro.

### Navegação com React Navigation 7

A hierarquia é `NavigationContainer` → Stack (`StackRoutes`) → Tabs (`TabRoutes`) → telas.

- `StackRoutes.tsx` usa `createNativeStackNavigator` com uma única tela, `MainTabs`, sem cabeçalho. É a base para telas futuras.
- `TabRoutes.tsx` usa `createBottomTabNavigator` com duas abas: `Home` ("Início", ícone `home`) e `History` ("Histórico", ícone `receipt`). A aba ativa usa `colors.accent`.
- `types/navigation.ts` dá nome aos parâmetros das rotas, e o TypeScript checa os nomes:

```ts
export type RootStackParamList = { MainTabs: undefined };
export type MainTabParamList = { Home: undefined; History: undefined };
```

`undefined` significa que a rota não recebe parâmetros. Não usamos Expo Router: a decisão do projeto foi declarar a navegação à mão em dois arquivos, no estilo da turma, o que é mais explícito para estudo.

### Tela Início (layout)

Dentro de `SafeAreaView` e `ScrollView`, de cima para baixo:

1. Cabeçalho: "Olá!" e "Registre seus gastos falando".
2. Seção "Último registro", com quatro situações: spinner enquanto carrega, `EmptyState` de erro, `RecordCard` com o registro, ou `EmptyState` "Nenhum registro ainda".
3. Área de voz: `RecordButton`, `StatusMessage` e a dica "Ex.: comprei 3 cafés de 5 reais".
4. `DevPanel`, só em modo desenvolvimento.

O conteúdo tem `maxWidth: 520` e fica centralizado, então no navegador do computador parece uma coluna de celular. A lógica da tela está na parte do Helio.

### Tela Histórico

Título, cartão "Gastos recentes" com a soma, campo de busca e a lista.

- **`FlatList`:** `data`, `keyExtractor` pelo `id` e `renderItem` com `RecordCard`. Ela só monta os itens visíveis (virtualização).
- **Busca por item:** `TextInput` com `onSubmitEditing`; a busca roda ao confirmar (Enter), não a cada letra, e não há debounce. O texto digitado fica em `search` e o termo aplicado em `appliedSearch`.
- **Quatro estados:** carregando (spinner), erro (mensagem e botão "Tentar novamente"), vazio (`ListEmptyComponent`) e dados.
- **Pull to refresh:** `refreshing` e `onRefresh` na `FlatList`.
- **Recarrega ao ganhar foco** (`useFocusEffect`), buscando 50 registros. O total soma só as despesas carregadas; não há paginação nem scroll infinito.

### Componentes visuais

| Componente | Props | Estado interno | Nativos do React Native | Biblioteca |
| --- | --- | --- | --- | --- |
| `EmptyState` | `title`, `description?`, `icon?` | nenhum | `View`, `Text` | `Ionicons` |
| `RecordCard` | `record` | nenhum | `View`, `Text` | `Ionicons` |
| `StatusMessage` | `message`, `tone?` | nenhum | `Text` | nenhuma |
| `RecordButton` | `state`, `onPress`, `onPressIn`, `onPressOut` | `pulse`, `isPressed` | `Pressable`, `Animated`, `ActivityIndicator`, `Platform` | `Ionicons` |
| `DevPanel` | `debug`, `clientTotalMs` | `expanded` | `View`, `Text`, `Pressable` | nenhuma |
| `JsonBlock` | `value` | nenhum | `ScrollView`, `Text`, `Platform` | nenhuma |

- **`RecordCard`** mostra data, item com a primeira letra maiúscula, categoria com ponto colorido e, se a quantidade não for 1, a linha "quantidade × preço". Despesa aparece com "- " e receita com "+ " em verde. O fundo do ícone usa a cor da categoria com sufixo `22` (transparência).
- **`StatusMessage`** escolhe o estilo pela prop `tone` (`default`, `danger`, `success`).
- **`RecordButton` e `DevPanel`** estão na parte do Helio.

### Estilo, cores, ícones e formatação

- **`StyleSheet.create`** no fim de cada arquivo, com estilos nomeados. Não há biblioteca de estilo.
- **`constants/colors.ts`** concentra a paleta (fundo `#070B14`, cartão `#0E1524`, primária `#0955EF`, destaque `#04C7D2`, perigo `#F25C6B`, sucesso `#01D58A`). Mudar a identidade visual é mexer nesse arquivo.
- **`constants/categoryStyles.ts`** liga o código da categoria a `{ icon, color }`. O backend manda só o código (`food`) e o rótulo em português; ícone e cor são decididos no front. Categoria desconhecida cai em `defaultCategoryStyle` (etiqueta cinza). O tipo do ícone é `keyof typeof Ionicons.glyphMap`, então o TypeScript recusa nomes inexistentes.
- **`formatCurrency`** usa `Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" })`: `"15.00"` vira `R$ 15,00`.
- **`formatDate`** monta `dd/mm/aaaa` com `padStart(2, "0")`.

### Pontos para explicar ao vivo

- A hierarquia `NavigationContainer` → Stack → Tabs → telas, e por que o Stack tem uma tela só.
- `types/navigation.ts` dá nome e parâmetros às rotas e o TypeScript confere.
- `StyleSheet.create` e um único arquivo de cores.
- A `FlatList` só renderiza o que aparece; o `keyExtractor` dá identidade a cada item.
- Quatro estados em toda chamada assíncrona: carregando, erro, vazio e dados.
- O backend manda só o código da categoria; o front traduz em ícone e cor.
- `react-native-web` é o motivo de o mesmo código rodar no navegador e no celular.

### Perguntas que a banca pode fazer

**Por que React Navigation e não Expo Router?** Foi o que a turma estudou: rotas declaradas em código, sem convenção de arquivos, funcionando igual na web e no celular.

**Qual a diferença entre Stack e Tabs?** Stack empilha telas e volta com "voltar"; Tabs alterna entre telas irmãs pela barra inferior. Aqui o Tabs fica dentro do Stack.

**Por que `FlatList` e não `ScrollView` com `map`?** A `FlatList` é virtualizada e já traz `onRefresh` e `ListEmptyComponent`.

**O que é `SafeAreaView`?** Mantém o conteúdo fora do notch e da barra de status. Vem de `react-native-safe-area-context`, não do núcleo.

**O app tem tema claro?** Não. O tema é sempre escuro, embora o `app.json` declare `userInterfaceStyle: automatic`.

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
