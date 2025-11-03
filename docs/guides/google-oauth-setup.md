# Настройка Google OAuth в RAGFlow

Это руководство поможет вам настроить авторизацию через Google в RAGFlow согласно официальной документации.

## 📋 Обзор

RAGFlow полностью поддерживает OAuth 2.0 авторизацию, включая Google. Все необходимые компоненты уже реализованы:

- ✅ **Backend**: OAuth endpoints и обработчики
- ✅ **Frontend**: Динамическое отображение OAuth кнопок
- ✅ **Иконка Google**: Уже существует в системе

Вам нужно только **настроить конфигурацию**.

## 🚀 Шаг 1: Создание OAuth приложения в Google Cloud Console

### 1.1 Создание проекта

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Запомните ID проекта

### 1.2 Настройка OAuth Consent Screen

1. Перейдите в **APIs & Services** → **OAuth consent screen**
2. Выберите тип приложения:
   - **External** - для публичного приложения
   - **Internal** - только для организации (если у вас Google Workspace)
3. Заполните обязательные поля:
   - **App name**: RAGFlow или название вашего приложения
   - **User support email**: ваш email
   - **Developer contact information**: ваш email
4. Добавьте **Scopes**:
   - `openid`
   - `email`
   - `profile`
5. Сохраните и продолжите

### 1.3 Создание OAuth 2.0 Client ID

1. Перейдите в **APIs & Services** → **Credentials**
2. Нажмите **Create Credentials** → **OAuth 2.0 Client ID**
3. Выберите **Application type**: **Web application**
4. Введите имя: `RAGFlow Web Client`
5. Настройте **Authorized redirect URIs**:
   ```
   https://swipies.app/v1/user/oauth/callback/google
   ```
   
   Для локальной разработки также добавьте:
   ```
   http://localhost:9380/v1/user/oauth/callback/google
   ```

6. Нажмите **Create**
7. **ВАЖНО**: Сохраните:
   - **Client ID** (выглядит как: `123456789-abc123.apps.googleusercontent.com`)
   - **Client Secret** (выглядит как: `GOCSPX-abc123xyz`)

## 🔧 Шаг 2: Настройка RAGFlow

### 2.1 Создание файла .env

Создайте файл `docker/.env` со следующим содержимым:

```bash
# ==========================
# RAGFlow Docker Environment Configuration
# ==========================

# Timezone
TIMEZONE=UTC

# RAGFlow Image
RAGFLOW_IMAGE=infiniflow/ragflow:latest

# HTTP Port
SVR_HTTP_PORT=9380

# Hugging Face Endpoint (optional)
HF_ENDPOINT=

# ==========================
# Elasticsearch Configuration
# ==========================
STACK_VERSION=8.11.3
ES_PORT=1200
ELASTIC_PASSWORD=infini_rag_flow

# ==========================
# OpenSearch Configuration
# ==========================
OS_PORT=1201
OPENSEARCH_PASSWORD=infini_rag_flow_OS_01

# ==========================
# Infinity Configuration
# ==========================
INFINITY_THRIFT_PORT=23817
INFINITY_HTTP_PORT=23820
INFINITY_PSQL_PORT=15432

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
# Google OAuth Configuration
# ==========================
# ⚠️ ЗАМЕНИТЕ НА ВАШИ РЕАЛЬНЫЕ ДАННЫЕ ИЗ GOOGLE CLOUD CONSOLE
OAUTH_GOOGLE_CLIENT_ID=ВАШ_GOOGLE_CLIENT_ID
OAUTH_GOOGLE_CLIENT_SECRET=ВАШ_GOOGLE_CLIENT_SECRET
OAUTH_GOOGLE_REDIRECT_URI=https://swipies.app/v1/user/oauth/callback/google
```

### 2.2 Обновление service_conf.yaml.template (опционально)

Файл `docker/service_conf.yaml.template` уже правильно настроен для Google OAuth:

```yaml
oauth:
  google:
    type: "oauth2"
    icon: "google"
    display_name: "Google"
    client_id: '${OAUTH_GOOGLE_CLIENT_ID:-}'
    client_secret: '${OAUTH_GOOGLE_CLIENT_SECRET:-}'
    authorization_url: 'https://accounts.google.com/o/oauth2/v2/auth'
    token_url: 'https://oauth2.googleapis.com/token'
    userinfo_url: 'https://www.googleapis.com/oauth2/v3/userinfo'
    scope: 'openid email profile'
    redirect_uri: '${OAUTH_GOOGLE_REDIRECT_URI:-https://swipies.app/v1/user/oauth/callback/google}'
```

Этот файл автоматически использует переменные из `.env`.

### 2.3 Обновление conf/service_conf.yaml

Файл `conf/service_conf.yaml` уже обновлен с правильным `redirect_uri` для production:

```yaml
oauth:
  google:
    type: "oauth2"
    icon: "google"
    display_name: "Google"
    client_id: "ВАШ_GOOGLE_CLIENT_ID"
    client_secret: "ВАШ_GOOGLE_CLIENT_SECRET"
    authorization_url: "https://accounts.google.com/o/oauth2/v2/auth"
    token_url: "https://oauth2.googleapis.com/token"
    userinfo_url: "https://www.googleapis.com/oauth2/v3/userinfo"
    scope: "openid email profile"
    redirect_uri: "https://swipies.app/v1/user/oauth/callback/google"
```

## 🐳 Шаг 3: Перезапуск Docker контейнеров

После настройки конфигурации необходимо перезапустить контейнеры:

### 3.1 Остановка контейнеров

```bash
cd docker
docker compose down
```

### 3.2 Пересборка (если нужно)

```bash
docker compose build --no-cache
```

### 3.3 Запуск контейнеров

```bash
docker compose up -d
```

### 3.4 Проверка логов

```bash
docker compose logs -f ragflow
```

## ✅ Проверка работы

### 1. Откройте страницу входа

Перейдите на: `https://swipies.app`

### 2. Проверьте наличие кнопки Google

На странице входа должна появиться кнопка:
```
🔵 Sign in with Google
```

### 3. Тестирование авторизации

1. Нажмите на кнопку "Sign in with Google"
2. Вы будете перенаправлены на страницу авторизации Google
3. Выберите аккаунт Google
4. Разрешите доступ к email и профилю
5. Вы будете перенаправлены обратно в RAGFlow с автоматическим входом

## 🔍 Отладка

### Проверка API endpoints

1. **Получение списка OAuth каналов**:
   ```bash
   curl https://swipies.app/v1/user/login/channels
   ```
   
   Должен вернуть:
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

2. **Проверка redirect URL**:
   ```bash
   curl https://swipies.app/v1/user/login/google
   ```
   
   Должен вернуть 302 redirect на Google OAuth

### Проверка логов backend

```bash
docker compose logs -f ragflow | grep -i oauth
```

### Частые ошибки

#### 1. "redirect_uri_mismatch"

**Причина**: Redirect URI в Google Cloud Console не совпадает с настроенным в RAGFlow

**Решение**: 
- Проверьте, что в Google Cloud Console добавлен точный URL: `https://swipies.app/v1/user/oauth/callback/google`
- Убедитесь, что нет лишних слэшей или пробелов

#### 2. Кнопка Google не появляется

**Причина**: Переменные окружения не загружены

**Решение**:
```bash
# Проверьте, что файл .env существует
ls -la docker/.env

# Проверьте, что переменные загружены в контейнер
docker exec ragflow-server env | grep OAUTH
```

#### 3. "Invalid client"

**Причина**: Неверный Client ID или Client Secret

**Решение**:
- Проверьте, что вы скопировали правильные значения из Google Cloud Console
- Убедитесь, что нет лишних пробелов или переносов строк

## 📚 Дополнительные ресурсы

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [RAGFlow Configuration Guide](https://ragflow.io/docs/configurations)
- [RAGFlow OAuth README](../api/apps/auth/README.md)

## 🔒 Безопасность

1. **Никогда не коммитьте файл `.env`** в Git
2. Используйте **сильные пароли** для MySQL, Redis, MinIO
3. В production используйте **HTTPS**
4. Регулярно **обновляйте Client Secret** в Google Cloud Console
5. Ограничьте **Authorized redirect URIs** только необходимыми доменами

## 🎉 Готово!

Теперь пользователи могут входить в RAGFlow через свои Google аккаунты. Система автоматически:
- Создает новых пользователей при первом входе
- Получает email, имя и аватар из Google профиля
- Сохраняет информацию о канале входа

## 📝 Примечания

- После настройки Google OAuth, пользователи все еще могут использовать обычный email/password вход
- Вы можете настроить несколько OAuth провайдеров одновременно (Google, GitHub, и т.д.)
- Каждый OAuth провайдер требует отдельной настройки в конфигурации

---

**Автор**: RAGFlow Team  
**Дата обновления**: Ноябрь 2025  
**Версия**: 1.0

