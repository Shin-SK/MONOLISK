# frontend/Dockerfile
FROM node:20-slim

# git 警告を消す（versionスクリプト用）
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# devDeps を確実に入れる & rollup のネイティブを無効化
ENV NODE_ENV=development
ENV ROLLUP_DISABLE_NATIVE=1

# lockfile を使って再現性インストール
COPY package*.json ./
RUN npm ci --include=dev

COPY . .

CMD ["npm","run","dev","--","--host"]
