# 🎯 НАЧНИТЕ ЗДЕСЬ - Настройка Google OAuth

## ✨ Что готово?

**RAGFlow полностью поддерживает Google OAuth из коробки!**

Все компоненты уже реализованы:
- ✅ Backend OAuth endpoints
- ✅ Frontend OAuth UI  
- ✅ Автоматическая регистрация пользователей
- ✅ Google иконка и UI элементы

**Нужно только настроить credentials!**

---

## ⚡ За 2 минуты

### 1️⃣ Получите Google OAuth credentials

👉 [Google Cloud Console](https://console.cloud.google.com/apis/credentials)

1. Создайте **OAuth 2.0 Client ID**
2. Тип: **Web application**  
3. Redirect URI: `https://swipies.app/v1/user/oauth/callback/google`
4. Сохраните **Client ID** и **Client Secret**

### 2️⃣ Запустите автоматическую настройку

```bash
bash scripts/setup-google-oauth.sh
```

Скрипт спросит Client ID и Client Secret, создаст конфигурацию и перезапустит контейнеры.

### 3️⃣ Проверьте

Откройте https://swipies.app

На странице входа должна появиться кнопка:
```
🔵 Sign in with Google
```

**Готово! Пользователи могут входить через Google! 🎉**

---

## 📚 Подробная документация

| Документ | Описание | Когда использовать |
|----------|----------|-------------------|
| 📄 [GOOGLE_OAUTH_SETUP_RU.md](GOOGLE_OAUTH_SETUP_RU.md) | Быстрая инструкция (5 мин) | Для быстрой настройки |
| 📘 [docs/guides/google-oauth-setup.md](docs/guides/google-oauth-setup.md) | Полное руководство | Для детального понимания |
| 🔧 [OAUTH_IMPLEMENTATION_SUMMARY.md](OAUTH_IMPLEMENTATION_SUMMARY.md) | Технический обзор | Для разработчиков |
| 🛠️ [scripts/README.md](scripts/README.md) | Документация скриптов | Для автоматизации |

---

## 🔄 Ручная настройка (альтернатива)

Если не хотите использовать скрипт:

### Шаг 1: Создайте `docker/.env`

```bash
cd docker
nano .env
```

### Шаг 2: Добавьте минимальную конфигурацию

```env
# Базовая конфигурация
TIMEZONE=UTC
RAGFLOW_IMAGE=infiniflow/ragflow:latest
SVR_HTTP_PORT=9380

# Database & Storage (используйте значения по умолчанию или свои)
MYSQL_PASSWORD=infini_rag_flow
MYSQL_PORT=5455
REDIS_PASSWORD=infini_rag_flow
REDIS_PORT=6379
MINIO_USER=rag_flow
MINIO_PASSWORD=infini_rag_flow
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001

# Elasticsearch
STACK_VERSION=8.11.3
ES_PORT=1200
ELASTIC_PASSWORD=infini_rag_flow

# Resource limits
MEM_LIMIT=8073741824

# 🔵 Google OAuth - ЗАМЕНИТЕ НА ВАШИ ДАННЫЕ
OAUTH_GOOGLE_CLIENT_ID=ваш_google_client_id
OAUTH_GOOGLE_CLIENT_SECRET=ваш_google_client_secret
OAUTH_GOOGLE_REDIRECT_URI=https://swipies.app/v1/user/oauth/callback/google
```

### Шаг 3: Перезапустите

```bash
docker compose down
docker compose up -d
```

---

## 🔍 Проверка и отладка

### Проверить OAuth endpoints

```bash
curl https://swipies.app/v1/user/login/channels
```

Должен вернуть список с Google:
```json
{
  "code": 0,
  "data": [
    {
      "channel": "google",
      "display_name": "Google",
      "icon": "google"
    }
  ]
}
```

### Проверить переменные окружения

```bash
docker exec ragflow-server env | grep OAUTH
```

### Посмотреть логи

```bash
docker compose -f docker/docker-compose.yml logs -f ragflow
```

---

## ❓ Частые вопросы

### Q: Кнопка Google не появляется?

**A:** Проверьте:
1. Файл `docker/.env` существует и содержит OAUTH_GOOGLE_CLIENT_ID
2. Контейнеры перезапущены после создания .env
3. Переменные загружены: `docker exec ragflow-server env | grep OAUTH`

### Q: Ошибка "redirect_uri_mismatch"?

**A:** В Google Cloud Console должен быть точный URL:
```
https://swipies.app/v1/user/oauth/callback/google
```
Без лишних слэшей или пробелов!

### Q: Ошибка "invalid_client"?

**A:** Проверьте Client ID и Client Secret:
- Скопированы правильно из Google Cloud Console
- Нет лишних пробелов или переносов строк
- Используете credentials для правильного проекта

### Q: Могу ли я использовать несколько OAuth провайдеров?

**A:** Да! RAGFlow поддерживает:
- Google OAuth
- GitHub OAuth  
- Custom OAuth2
- OpenID Connect (OIDC)

Добавьте их в конфигурацию аналогично Google.

### Q: Что происходит при первом входе через Google?

**A:** RAGFlow автоматически:
1. Создает новый аккаунт
2. Получает email, имя и аватар из Google
3. Сохраняет информацию о канале входа
4. Логинит пользователя

---

## 🔒 Безопасность

⚠️ **ВАЖНО:**
- Никогда не коммитьте файл `.env` в Git (он уже в `.gitignore`)
- Используйте HTTPS в production
- Регулярно обновляйте Client Secret
- Ограничьте Redirect URIs только необходимыми доменами

---

## 📞 Нужна помощь?

1. 📖 Прочитайте [Полное руководство](docs/guides/google-oauth-setup.md)
2. 🔍 Проверьте раздел **Отладка** в [GOOGLE_OAUTH_SETUP_RU.md](GOOGLE_OAUTH_SETUP_RU.md#-отладка)
3. 📝 Посмотрите логи: `docker compose logs -f ragflow`

---

## ✅ Checklist

Используйте для проверки:

- [ ] ✅ Создал OAuth App в Google Cloud Console
- [ ] ✅ Добавил Redirect URI в Google
- [ ] ✅ Получил Client ID
- [ ] ✅ Получил Client Secret
- [ ] ✅ Создал файл `docker/.env`
- [ ] ✅ Добавил OAUTH_GOOGLE_CLIENT_ID
- [ ] ✅ Добавил OAUTH_GOOGLE_CLIENT_SECRET
- [ ] ✅ Добавил OAUTH_GOOGLE_REDIRECT_URI
- [ ] ✅ Перезапустил Docker контейнеры
- [ ] ✅ Проверил появление кнопки Google
- [ ] ✅ Протестировал вход через Google

---

## 🎉 Поздравляем!

**Ваш RAGFlow теперь поддерживает вход через Google!**

Пользователи могут:
- ✅ Войти одним кликом через Google
- ✅ Автоматически зарегистрироваться
- ✅ Использовать свой Google аватар и имя
- ✅ Продолжать использовать email/password

---

**Создано**: Ноябрь 2025  
**Версия**: 1.0  
**Статус**: ✅ Production Ready

