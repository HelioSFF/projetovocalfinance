FROM node:22-bookworm-slim

ENV CI=1 \
    EXPO_NO_TELEMETRY=1 \
    EXPO_DEVTOOLS_LISTEN_ADDRESS=0.0.0.0

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 8081

CMD ["npx", "expo", "start", "--web"]
