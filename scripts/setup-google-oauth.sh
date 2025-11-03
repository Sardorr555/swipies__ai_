#!/bin/bash

# ==============================================================================
# RAGFlow Google OAuth Setup Script
# ==============================================================================
# Этот скрипт помогает быстро настроить Google OAuth для RAGFlow
# 
# Использование:
#   bash scripts/setup-google-oauth.sh
#
# Автор: RAGFlow Team
# ==============================================================================

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для цветного вывода
print_header() {
    echo -e "${BLUE}===================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Проверка, что скрипт запущен из корневой директории проекта
if [ ! -f "docker/docker-compose.yml" ]; then
    print_error "Пожалуйста, запустите скрипт из корневой директории RAGFlow"
    exit 1
fi

print_header "Настройка Google OAuth для RAGFlow"

# Шаг 1: Проверка существующего .env файла
print_info "Шаг 1: Проверка конфигурации..."

ENV_FILE="docker/.env"

if [ -f "$ENV_FILE" ]; then
    print_warning "Файл docker/.env уже существует"
    read -p "Хотите обновить его? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Отменено пользователем"
        exit 0
    fi
    BACKUP_FILE="docker/.env.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$ENV_FILE" "$BACKUP_FILE"
    print_success "Создана резервная копия: $BACKUP_FILE"
fi

# Шаг 2: Получение учетных данных Google
print_info "\nШаг 2: Ввод учетных данных Google OAuth"
echo
print_info "Получите Client ID и Client Secret из Google Cloud Console:"
print_info "https://console.cloud.google.com/apis/credentials"
echo

read -p "Введите Google Client ID: " GOOGLE_CLIENT_ID
if [ -z "$GOOGLE_CLIENT_ID" ]; then
    print_error "Client ID не может быть пустым"
    exit 1
fi

read -sp "Введите Google Client Secret: " GOOGLE_CLIENT_SECRET
echo
if [ -z "$GOOGLE_CLIENT_SECRET" ]; then
    print_error "Client Secret не может быть пустым"
    exit 1
fi

read -p "Введите Redirect URI (по умолчанию: https://swipies.app/v1/user/oauth/callback/google): " REDIRECT_URI
REDIRECT_URI=${REDIRECT_URI:-https://swipies.app/v1/user/oauth/callback/google}

# Шаг 3: Создание .env файла
print_info "\nШаг 3: Создание файла .env..."

cat > "$ENV_FILE" << EOF
# ==========================
# RAGFlow Docker Environment Configuration
# ==========================
# Автоматически создано: $(date)

# Timezone
TIMEZONE=UTC

# RAGFlow Image
RAGFLOW_IMAGE=infiniflow/ragflow:latest

# HTTP Port
SVR_HTTP_PORT=9380

# Hugging Face Endpoint (optional)
HF_ENDPOINT=

# MacOS flag (optional)
MACOS=

# ==========================
# Elasticsearch Configuration
# ==========================
STACK_VERSION=8.11.3
ES_PORT=1200
ELASTIC_PASSWORD=infini_rag_flow

# ==========================
# OpenSearch Configuration (alternative to Elasticsearch)
# ==========================
OS_PORT=1201
OPENSEARCH_PASSWORD=infini_rag_flow_OS_01

# ==========================
# Infinity Configuration (alternative to Elasticsearch)
# ==========================
INFINITY_THRIFT_PORT=23817
INFINITY_HTTP_PORT=23820
INFINITY_PSQL_PORT=15432

# ==========================
# Kibana Configuration
# ==========================
KIBANA_PORT=6601
KIBANA_USER=rag_flow
KIBANA_PASSWORD=infini_rag_flow

# ==========================
# MySQL Configuration
# ==========================
MYSQL_PASSWORD=infini_rag_flow
MYSQL_PORT=5455

# ==========================
# MinIO Configuration
# ==========================
MINIO_USER=rag_flow
MINIO_PASSWORD=infini_rag_flow
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001

# ==========================
# Redis Configuration
# ==========================
REDIS_PASSWORD=infini_rag_flow
REDIS_PORT=6379

# ==========================
# Resource Management
# ==========================
MEM_LIMIT=8073741824

# ==========================
# Sandbox Configuration (optional)
# ==========================
SANDBOX_EXECUTOR_MANAGER_IMAGE=infiniflow/sandbox-executor-manager:latest
SANDBOX_EXECUTOR_MANAGER_PORT=9385
SANDBOX_EXECUTOR_MANAGER_POOL_SIZE=3
SANDBOX_BASE_PYTHON_IMAGE=infiniflow/sandbox-base-python:latest
SANDBOX_BASE_NODEJS_IMAGE=infiniflow/sandbox-base-nodejs:latest
SANDBOX_ENABLE_SECCOMP=false
SANDBOX_MAX_MEMORY=256m
SANDBOX_TIMEOUT=10s

# ==========================
# Google OAuth Configuration
# ==========================
OAUTH_GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID
OAUTH_GOOGLE_CLIENT_SECRET=$GOOGLE_CLIENT_SECRET
OAUTH_GOOGLE_REDIRECT_URI=$REDIRECT_URI
EOF

print_success "Файл .env создан успешно"

# Шаг 4: Проверка Docker
print_info "\nШаг 4: Проверка Docker..."

if ! command -v docker &> /dev/null; then
    print_error "Docker не установлен"
    print_info "Установите Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose не установлен"
    exit 1
fi

print_success "Docker установлен"

# Шаг 5: Перезапуск контейнеров
print_info "\nШаг 5: Перезапуск Docker контейнеров..."

read -p "Хотите перезапустить контейнеры сейчас? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Остановка контейнеров..."
    cd docker
    docker compose down
    
    print_info "Запуск контейнеров..."
    docker compose up -d
    
    print_success "Контейнеры запущены"
    
    print_info "Ожидание запуска сервисов (30 секунд)..."
    sleep 30
    
    # Проверка статуса
    print_info "Проверка статуса контейнеров..."
    docker compose ps
else
    print_warning "Перезапустите контейнеры вручную:"
    print_info "cd docker && docker compose down && docker compose up -d"
fi

# Шаг 6: Проверка настройки
print_header "Проверка настройки"

print_info "Проверка OAuth endpoints..."
DOMAIN=$(echo $REDIRECT_URI | sed -E 's|/v1/user/oauth/callback/google||')

if curl -s -o /dev/null -w "%{http_code}" "$DOMAIN/v1/user/login/channels" | grep -q "200"; then
    print_success "OAuth endpoints доступны"
else
    print_warning "OAuth endpoints пока недоступны (контейнеры могут еще запускаться)"
fi

# Финальная информация
print_header "Настройка завершена!"

echo
print_success "Google OAuth успешно настроен!"
echo
print_info "Следующие шаги:"
print_info "1. Убедитесь, что в Google Cloud Console добавлен Redirect URI:"
print_info "   $REDIRECT_URI"
print_info "2. Откройте ваше приложение: $DOMAIN"
print_info "3. На странице входа должна появиться кнопка 'Sign in with Google'"
echo
print_info "Документация:"
print_info "- Полное руководство: docs/guides/google-oauth-setup.md"
print_info "- Быстрый старт: GOOGLE_OAUTH_SETUP_RU.md"
echo
print_info "Отладка:"
print_info "- Проверить каналы: curl $DOMAIN/v1/user/login/channels"
print_info "- Логи: cd docker && docker compose logs -f ragflow"
echo
print_warning "⚠️ Важно: Файл docker/.env содержит секретные данные"
print_warning "   Не коммитьте его в Git! (он уже в .gitignore)"
echo

print_success "🎉 Готово! Пользователи могут входить через Google!"

