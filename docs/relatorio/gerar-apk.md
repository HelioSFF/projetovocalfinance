# Como gerar o APK do Vocal Finance (passo a passo manual)

O APK é gerado na nuvem da Expo (EAS Build). Não precisa de Android Studio nem de Java no PC.

## Antes de começar

- Node.js instalado.
- Conta gratuita em https://expo.dev.
- Backend publicado com URL pública (o celular não enxerga `localhost`).

## Passo a passo

### 1. Instalar as dependências

```bash
cd frontend
npm install
```

### 2. Entrar na conta Expo

```bash
npx eas-cli login
```

Digite o e-mail (ou usuário) e a senha da conta. Para conferir: `npx eas-cli whoami`.

### 3. Criar o projeto na conta

```bash
npx eas-cli init
```

Responda `y`. O comando grava `owner` e `projectId` no `app.json`.

### 4. Ajustar o `app.json`

Dentro de `"expo"`, no bloco `"android"`, defina o identificador único do app:

```json
"android": {
  "package": "com.seuusuario.vocalfinance"
}
```

O plugin do microfone já deve estar em `plugins`:

```json
"plugins": [
  ["expo-audio", { "microphonePermission": "Permita o acesso ao microfone para registrar por voz" }]
]
```

### 5. Criar o `eas.json` (na pasta `frontend/`)

```json
{
  "build": {
    "preview": {
      "distribution": "internal",
      "android": { "buildType": "apk" },
      "env": {
        "EXPO_PUBLIC_API_URL": "https://vocal-backend.hospedeaqui.app",
        "EXPO_PUBLIC_APP_ENV": "production"
      }
    }
  }
}
```

- `buildType: "apk"` gera um arquivo instalável. O padrão (`aab`) só serve para a Play Store.
- `distribution: "internal"` gera um link de download, sem publicar em loja.
- `env` define as variáveis que ficam embutidas no app.
- Use `EXPO_PUBLIC_APP_ENV: "development"` para mostrar o painel de debug.

### 6. Gerar o APK

```bash
npx eas-cli build -p android --profile preview
```

Na primeira vez, responda `Yes` para o EAS criar a keystore (a chave que assina o app). O build leva de 10 a 20 minutos.

### 7. Instalar no celular

Ao terminar, o terminal mostra o link do `.apk`. Abra no celular, baixe e instale. O Android pode pedir para permitir instalação de fontes desconhecidas.

## Resumo

| Etapa | O que faz |
| --- | --- |
| `eas login` | Liga o terminal à conta Expo |
| `eas init` | Cria o projeto e preenche `owner` e `projectId` |
| `app.json` | Nome, ícone, `android.package` e permissão de microfone |
| `eas.json` | Perfil de build: APK e variáveis de ambiente |
| `eas build` | Compila na nuvem e entrega o link do APK |

## Pontos para lembrar

- As variáveis `EXPO_PUBLIC_*` ficam **embutidas no APK** na hora do build. Mudou a URL do backend: precisa gerar outro APK.
- **Nunca** coloque chave de API em `EXPO_PUBLIC_*`. Qualquer pessoa consegue extrair o conteúdo de um APK. As chaves ficam só no backend.
- As pastas `android/` e `ios/` são geradas pelo Expo no build. Não são editadas à mão.
