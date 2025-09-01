########### 1) BUILD (Node) ###########
FROM node:20-alpine AS build
WORKDIR /app

# Устанавливаем зависимости
COPY web/package.json web/package-lock.json* web/pnpm-lock.yaml* web/yarn.lock* ./
RUN if [ -f package-lock.json ]; then npm ci --force; \
    elif [ -f pnpm-lock.yaml ]; then npm i -g pnpm && pnpm install --frozen-lockfile; \
    elif [ -f yarn.lock ]; then npm i -g yarn && yarn install --frozen-lockfile; \
    else npm install --force; fi

# Копируем исходники UI
COPY web/ .

# Копируем документацию (нужна Umi)
COPY docs/ ./docs

# Можно переопределить публичный путь, если UI будет висеть не в корне
ARG PUBLIC_PATH=/
ENV UMI_PUBLIC_PATH=${PUBLIC_PATH}

# Собираем Umi (dist -> /app/dist)
RUN npm run build

########### 2) RUNTIME (Nginx) ###########
FROM nginx:1.25-alpine

ENV RAGFLOW_BACKEND=http://ragflow-server:9380

RUN mkdir -p /etc/nginx/templates

RUN printf '%s\n' \
'server {' \
'  listen 80;' \
'  server_name _;' \
'' \
'  root /usr/share/nginx/html;' \
'  index index.html;' \
'' \
'  location = /healthz { return 200 "ok\n"; }' \
'' \
'  location ~ ^/(api|v1)/ {' \
'    proxy_pass ${RAGFLOW_BACKEND};' \
'    include /etc/nginx/proxy_params;' \
'    proxy_http_version 1.1;' \
'    proxy_set_header Connection "";' \
'    proxy_buffering off;' \
'  }' \
'' \
'  location / {' \
'    try_files $uri /index.html;' \
'  }' \
'}' > /etc/nginx/templates/default.conf.template

RUN printf '%s\n' \
'proxy_set_header Host $host;' \
'proxy_set_header X-Real-IP $remote_addr;' \
'proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;' \
'proxy_set_header X-Forwarded-Proto $scheme;' \
> /etc/nginx/proxy_params

COPY --from=build /app/dist/ /usr/share/nginx/html/

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget -qO- http://127.0.0.1/healthz || exit 1
