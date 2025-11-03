# 🚀 Инструкции по настройке RAGFlow

## 🔐 Google OAuth Аутентификация

### ⚡ Быстрый старт

RAGFlow уже полностью поддерживает Google OAuth! Настройка займет 5 минут.

#### Автоматическая настройка (Рекомендуется)

```bash
bash scripts/setup-google-oauth.sh
```

#### Ручная настройка

1. **Получите OAuth credentials из [Google Cloud Console](https://console.cloud.google.com/)**
2. **Создайте файл `docker/.env`** (см. пример в документации)
3. **Добавьте переменные**:
   ```env
   OAUTH_GOOGLE_CLIENT_ID=ваш_client_id
   OAUTH_GOOGLE_CLIENT_SECRET=ваш_client_secret
   OAUTH_GOOGLE_REDIRECT_URI=https://swipies.app/v1/user/oauth/callback/google
   ```
4. **Перезапустите контейнеры**:
   ```bash
   cd docker
   docker compose down && docker compose up -d
   ```

### 📚 Документация

- **Быстрый старт (5 мин)**: [GOOGLE_OAUTH_SETUP_RU.md](GOOGLE_OAUTH_SETUP_RU.md)
- **Полное руководство**: [docs/guides/google-oauth-setup.md](docs/guides/google-oauth-setup.md)
- **Технический обзор**: [OAUTH_IMPLEMENTATION_SUMMARY.md](OAUTH_IMPLEMENTATION_SUMMARY.md)
- **Скрипты**: [scripts/README.md](scripts/README.md)

### ✅ Проверка

После настройки откройте https://swipies.app - на странице входа должна появиться кнопка:

```
🔵 Sign in with Google
```

---

## 🐳 Docker Deployment

### Стандартный запуск

```bash
cd docker
docker compose up -d
```

### Проверка статуса

```bash
docker compose ps
docker compose logs -f ragflow
```

### Перезапуск после изменений конфигурации

```bash
docker compose down
docker compose up -d
```

---

## 🔧 Конфигурация

### Основные файлы конфигурации

- **`docker/.env`** - Переменные окружения (не коммитить!)
- **`docker/service_conf.yaml.template`** - Шаблон конфигурации backend
- **`conf/service_conf.yaml`** - Локальная конфигурация
- **`docker/docker-compose.yml`** - Docker Compose конфигурация

### Переменные окружения

См. подробную информацию в [docker/README.md](docker/README.md)

---

## 📖 Дополнительные ресурсы

- [RAGFlow Official Docs](https://ragflow.io/docs)
- [Docker Compose Docs](https://docs.docker.com/compose/)
- [Google OAuth 2.0 Docs](https://developers.google.com/identity/protocols/oauth2)

---

## 🆘 Поддержка

### Частые проблемы

См. раздел **Troubleshooting** в [GOOGLE_OAUTH_SETUP_RU.md](GOOGLE_OAUTH_SETUP_RU.md#-отладка)

### Логи

```bash
# Все логи
docker compose logs -f

# Только RAGFlow
docker compose logs -f ragflow

# OAuth логи
docker compose logs -f ragflow | grep -i oauth
```

---

**Последнее обновление**: Ноябрь 2025

