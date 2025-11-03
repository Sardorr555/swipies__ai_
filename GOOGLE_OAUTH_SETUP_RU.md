# 🔐 Быстрая настройка Google OAuth для RAGFlow

## ✨ Что уже готово?

RAGFlow **уже полностью поддерживает** Google OAuth! Все компоненты реализованы:

✅ Backend OAuth endpoints  
✅ Frontend с динамическими кнопками  
✅ Google иконка  
✅ Автоматическая регистрация пользователей  

Нужно только **настроить credentials**.

---

## 🚀 Быстрый старт (5 минут)

### Шаг 1: Google Cloud Console

1. Откройте [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Создайте **OAuth 2.0 Client ID** (тип: Web application)
3. Добавьте **Authorized redirect URIs**:
   ```
   https://swipies.app/v1/user/oauth/callback/google
   ```
4. Сохраните **Client ID** и **Client Secret**

### Шаг 2: Создайте файл `docker/.env`

```bash
cd docker
nano .env
```

Вставьте (замените `ВАШ_CLIENT_ID` и `ВАШ_CLIENT_SECRET`):

```env
# Базовая конфигурация
TIMEZONE=UTC
RAGFLOW_IMAGE=infiniflow/ragflow:latest
SVR_HTTP_PORT=9380

# Elasticsearch
STACK_VERSION=8.11.3
ES_PORT=1200
ELASTIC_PASSWORD=infini_rag_flow

# MySQL
MYSQL_PASSWORD=infini_rag_flow
MYSQL_PORT=5455

# MinIO
MINIO_USER=rag_flow
MINIO_PASSWORD=infini_rag_flow
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001

# Redis
REDIS_PASSWORD=infini_rag_flow
REDIS_PORT=6379

# Resource limits
MEM_LIMIT=8073741824

# 🔵 Google OAuth - ЗАМЕНИТЕ НА ВАШИ ДАННЫЕ!
OAUTH_GOOGLE_CLIENT_ID=ВАШ_CLIENT_ID
OAUTH_GOOGLE_CLIENT_SECRET=ВАШ_CLIENT_SECRET
OAUTH_GOOGLE_REDIRECT_URI=https://swipies.app/v1/user/oauth/callback/google
```

### Шаг 3: Перезапустите Docker

```bash
cd docker
docker compose down
docker compose up -d
```

### Шаг 4: Проверка

Откройте https://swipies.app - на странице входа должна появиться кнопка:

```
🔵 Sign in with Google
```

---

## 📋 Полная документация

Подробное руководство: [docs/guides/google-oauth-setup.md](docs/guides/google-oauth-setup.md)

---

## 🔧 Быстрая отладка

### Проверить, что OAuth настроен:

```bash
curl https://swipies.app/v1/user/login/channels
```

Должен вернуть Google в списке каналов.

### Проверить переменные окружения:

```bash
docker exec ragflow-server env | grep OAUTH
```

### Посмотреть логи:

```bash
docker compose logs -f ragflow | grep -i oauth
```

---

## ⚠️ Частые проблемы

| Проблема | Решение |
|----------|---------|
| Кнопка Google не появляется | Проверьте, что `.env` файл существует и загружен |
| `redirect_uri_mismatch` | Проверьте URL в Google Cloud Console |
| `invalid_client` | Проверьте Client ID и Client Secret |

---

## 🎯 Что происходит при входе через Google?

1. Пользователь нажимает "Sign in with Google"
2. Перенаправление на Google для авторизации
3. Google возвращает пользователя в RAGFlow
4. **Автоматическое создание аккаунта** (если пользователь новый)
5. Получение email, имени и аватара из Google
6. Вход в систему

---

## 📱 Архитектура

```
┌─────────────┐     OAuth Flow     ┌──────────────┐
│   Browser   │ ─────────────────> │    Google    │
│             │                    │   OAuth 2.0   │
└─────────────┘                    └──────────────┘
       │                                   │
       │ 1. Redirect to authorize         │
       │ <─────────────────────────────── │
       │                                   │
       │ 2. User authorizes                │
       │ ──────────────────────────────> │
       │                                   │
       │ 3. Redirect with code             │
       │ <─────────────────────────────── │
       │                                   │
       v                                   │
┌─────────────┐                           │
│  RAGFlow    │ 4. Exchange code for token│
│  Backend    │ <───────────────────────> │
└─────────────┘                           │
       │                                   │
       │ 5. Get user info                  │
       │ <─────────────────────────────── │
       │                                   │
       │ 6. Create/login user              │
       v                                   │
┌─────────────┐                           │
│   Database  │                           │
└─────────────┘                           │
```

---

## 🔗 Полезные ссылки

- [Google Cloud Console](https://console.cloud.google.com/)
- [Google OAuth 2.0 Docs](https://developers.google.com/identity/protocols/oauth2)
- [RAGFlow Documentation](https://ragflow.io/docs)

---

## ✅ Checklist

- [ ] Создал OAuth App в Google Cloud Console
- [ ] Добавил redirect URI в Google
- [ ] Создал файл `docker/.env`
- [ ] Добавил OAUTH_GOOGLE_CLIENT_ID
- [ ] Добавил OAUTH_GOOGLE_CLIENT_SECRET
- [ ] Перезапустил Docker контейнеры
- [ ] Проверил появление кнопки Google
- [ ] Протестировал вход через Google

---

**🎉 Готово! Теперь пользователи могут входить через Google!**

