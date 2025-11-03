# 🔐 Google OAuth для RAGFlow - Полная документация

## 🎯 Быстрая навигация

### 🚀 Начните здесь
**[START_HERE_RU.md](START_HERE_RU.md)** - Начните с этого файла для быстрой настройки

---

## 📚 Документация по уровням

### 🟢 Быстрый старт (5 минут)
**[GOOGLE_OAUTH_SETUP_RU.md](GOOGLE_OAUTH_SETUP_RU.md)**
- Минимальная инструкция
- Checklist
- Частые проблемы
- Для быстрого запуска

### 🔵 Полное руководство (30 минут)
**[docs/guides/google-oauth-setup.md](docs/guides/google-oauth-setup.md)**
- Пошаговая инструкция
- Детальное описание каждого шага
- Настройка Google Cloud Console
- Troubleshooting
- Для глубокого понимания

### 🟡 Технический обзор
**[OAUTH_IMPLEMENTATION_SUMMARY.md](OAUTH_IMPLEMENTATION_SUMMARY.md)**
- Архитектура OAuth в RAGFlow
- Диаграммы и схемы
- Описание всех компонентов
- OAuth flow
- Для разработчиков

---

## 🛠️ Инструменты

### Автоматическая настройка
**[scripts/setup-google-oauth.sh](scripts/setup-google-oauth.sh)**
```bash
bash scripts/setup-google-oauth.sh
```
Интерактивный скрипт для автоматической настройки

### Документация скриптов
**[scripts/README.md](scripts/README.md)**
- Описание всех скриптов
- Примеры использования
- Как создавать свои скрипты

---

## 📖 Дополнительные ресурсы

### Общие инструкции
**[SETUP_INSTRUCTIONS.md](SETUP_INSTRUCTIONS.md)**
- Общая информация по настройке RAGFlow
- Docker deployment
- Конфигурация

### Основной README
**[README.md](README.md)**
- Информация о RAGFlow
- Установка и запуск
- Общая документация

---

## 🗂️ Структура документации

```
📁 RAGFlow/
│
├── 📄 START_HERE_RU.md                    ⭐ Начните здесь!
├── 📄 GOOGLE_OAUTH_SETUP_RU.md            🚀 Быстрый старт (5 мин)
├── 📄 OAUTH_IMPLEMENTATION_SUMMARY.md     🔧 Технический обзор
├── 📄 SETUP_INSTRUCTIONS.md               📋 Общие инструкции
├── 📄 GOOGLE_OAUTH_README.md              📚 Этот файл (навигация)
│
├── 📁 docs/
│   └── 📁 guides/
│       └── 📄 google-oauth-setup.md       📘 Полное руководство
│
├── 📁 scripts/
│   ├── 📄 setup-google-oauth.sh           🛠️ Автоматическая настройка
│   └── 📄 README.md                       📖 Документация скриптов
│
├── 📁 conf/
│   └── 📄 service_conf.yaml               ⚙️ Конфигурация (обновлена)
│
└── 📁 docker/
    ├── 📄 .env                            🔐 Переменные окружения (создайте)
    └── 📄 service_conf.yaml.template      📝 Шаблон конфигурации
```

---

## ⚡ Быстрый старт

### Вариант 1: Автоматический (Рекомендуется)
```bash
# 1. Получите Client ID и Client Secret из Google Cloud Console
# 2. Запустите скрипт
bash scripts/setup-google-oauth.sh
```

### Вариант 2: Ручной
```bash
# 1. Создайте docker/.env с OAuth credentials
# 2. Перезапустите контейнеры
cd docker
docker compose down && docker compose up -d
```

---

## ✅ Что реализовано?

RAGFlow **полностью поддерживает** Google OAuth:

- ✅ **Backend**
  - OAuth 2.0 endpoints
  - Authorization code flow
  - Token exchange
  - User info retrieval
  - Автоматическая регистрация

- ✅ **Frontend**
  - OAuth кнопки
  - Динамическое отображение каналов
  - Google иконка
  - Redirect flow

- ✅ **Database**
  - User model с OAuth support
  - Login channel tracking
  - Avatar storage

- ✅ **Документация**
  - Полные руководства
  - Автоматические скрипты
  - Примеры конфигурации

---

## 🎯 Какой документ читать?

### Я хочу быстро настроить (5 минут)
➡️ **[START_HERE_RU.md](START_HERE_RU.md)**

### Я хочу понять, как это работает
➡️ **[docs/guides/google-oauth-setup.md](docs/guides/google-oauth-setup.md)**

### Я разработчик и хочу понять архитектуру
➡️ **[OAUTH_IMPLEMENTATION_SUMMARY.md](OAUTH_IMPLEMENTATION_SUMMARY.md)**

### У меня проблема с настройкой
➡️ **[GOOGLE_OAUTH_SETUP_RU.md](GOOGLE_OAUTH_SETUP_RU.md#-отладка)**

### Я хочу автоматизировать настройку
➡️ **[scripts/README.md](scripts/README.md)**

---

## 🔍 Проверка установки

После настройки выполните:

```bash
# 1. Проверить OAuth endpoints
curl https://swipies.app/v1/user/login/channels

# 2. Проверить переменные окружения
docker exec ragflow-server env | grep OAUTH

# 3. Проверить логи
docker compose -f docker/docker-compose.yml logs -f ragflow | grep -i oauth
```

---

## 📊 Статус

| Компонент | Статус | Версия |
|-----------|--------|--------|
| Backend OAuth | ✅ Реализовано | OAuth 2.0 |
| Frontend UI | ✅ Реализовано | React + TypeScript |
| Google Integration | ✅ Готово | Google OAuth 2.0 |
| Документация | ✅ Завершена | v1.0 |
| Автоматизация | ✅ Реализована | Bash скрипты |
| Production Ready | ✅ Да | - |

---

## 🔗 Внешние ресурсы

- [Google Cloud Console](https://console.cloud.google.com/)
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [RAGFlow Official Docs](https://ragflow.io/docs)
- [Docker Compose Docs](https://docs.docker.com/compose/)

---

## 💡 Полезные команды

```bash
# Создать .env файл автоматически
bash scripts/setup-google-oauth.sh

# Перезапустить контейнеры
cd docker && docker compose down && docker compose up -d

# Проверить OAuth каналы
curl https://swipies.app/v1/user/login/channels

# Посмотреть логи OAuth
docker compose logs -f ragflow | grep -i oauth

# Проверить переменные окружения
docker exec ragflow-server env | grep OAUTH

# Проверить статус контейнеров
docker compose ps
```

---

## 🆘 Поддержка

### Порядок действий при проблемах:

1. 📖 Прочитайте **[GOOGLE_OAUTH_SETUP_RU.md](GOOGLE_OAUTH_SETUP_RU.md#-отладка)** (раздел "Отладка")
2. 🔍 Проверьте логи: `docker compose logs -f ragflow`
3. ✅ Пройдите по checklist в **[START_HERE_RU.md](START_HERE_RU.md#-checklist)**
4. 📘 Изучите **[docs/guides/google-oauth-setup.md](docs/guides/google-oauth-setup.md)**

---

## 🎉 Результат

После настройки:

1. ✅ На странице входа появится кнопка "Sign in with Google"
2. ✅ Пользователи смогут войти через Google аккаунт
3. ✅ Новые пользователи автоматически регистрируются
4. ✅ Получаются email, имя и аватар из Google
5. ✅ Работает параллельно с обычным email/password входом

---

**Создано**: Ноябрь 2025  
**Автор**: RAGFlow Team  
**Версия документации**: 1.0  
**Статус**: ✅ Production Ready

---

## 📝 Обновления

### v1.0 (Ноябрь 2025)
- ✅ Полная реализация Google OAuth
- ✅ Комплексная документация
- ✅ Автоматические скрипты настройки
- ✅ Обновлена конфигурация для production
- ✅ Добавлены руководства на русском языке

