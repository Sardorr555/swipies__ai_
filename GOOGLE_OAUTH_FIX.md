# 🔧 Исправление Google OAuth - Инструкция

## ❌ Проблема
Google OAuth выдавал ошибку `400: invalid_request` из-за:
1. Использования плейсхолдеров вместо реальных credentials
2. Несоответствия настроек Google OAuth 2.0 политике безопасности

## ✅ Что исправлено
1. **service_conf.yaml** - теперь использует переменные окружения:
   - `${OAUTH_GOOGLE_CLIENT_ID}`
   - `${OAUTH_GOOGLE_CLIENT_SECRET}`
   - `${OAUTH_GOOGLE_REDIRECT_URI}`

## 📋 Что нужно сделать

### 1. Настроить Google Cloud Console

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Выберите или создайте проект
3. Перейдите в **APIs & Services** → **Credentials**
4. Создайте **OAuth 2.0 Client ID** (если еще не создан)
5. Настройте **OAuth consent screen**:
   - User Type: External (для публичного доступа)
   - App name: Swipies
   - User support email: ваш email
   - Developer contact: ваш email
   - Scopes: `openid`, `email`, `profile`

### 2. Настроить Authorized redirect URIs

В настройках OAuth 2.0 Client добавьте следующие URIs:

```
https://api.swipies.app/v1/user/oauth/callback/google
https://swipies.app/v1/user/oauth/callback/google
http://localhost:9380/v1/user/oauth/callback/google
```

### 3. Обновить docker/.env

Откройте файл `docker/.env` и добавьте/обновите:

```bash
OAUTH_GOOGLE_CLIENT_ID=ваш_client_id_из_google_console
OAUTH_GOOGLE_CLIENT_SECRET=ваш_client_secret_из_google_console
OAUTH_GOOGLE_REDIRECT_URI=https://api.swipies.app/v1/user/oauth/callback/google
```

### 4. Перезапустить сервисы

```bash
cd docker
docker-compose down
docker-compose up -d
```

## 🔍 Проверка

После настройки проверьте:
1. Credentials в `docker/.env` заполнены
2. Redirect URIs в Google Console совпадают с `OAUTH_GOOGLE_REDIRECT_URI`
3. OAuth consent screen опубликован (или в тестовом режиме с добавленными тестовыми пользователями)

## ⚠️ Важные замечания

1. **Для production**: используйте `https://api.swipies.app/...`
2. **Для локальной разработки**: используйте `http://localhost:9380/...`
3. **Секреты**: НИКОГДА не коммитьте файл `docker/.env` в git!
4. **OAuth consent screen**: 
   - В режиме "Testing" - только тестовые пользователи могут войти
   - В режиме "Published" - все могут войти

## 🐛 Типичные ошибки

### `redirect_uri_mismatch`
- Проверьте, что URI в Google Console точно совпадает с `OAUTH_GOOGLE_REDIRECT_URI`

### `invalid_client`
- Проверьте правильность `OAUTH_GOOGLE_CLIENT_ID` и `OAUTH_GOOGLE_CLIENT_SECRET`

### `access_denied`
- Пользователь не добавлен в тестовые пользователи (если OAuth в режиме Testing)
