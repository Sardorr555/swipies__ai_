# Настройка окружения и локальная разработка (Setup & Development)

> **Статус документа:** Актуален  
> **Дата последней проверки:** 2026-10-15  
> **Основная ветка:** `test`

---

## 1. Системные требования

* **Операционная система:** Linux (Ubuntu 22.04 / 24.04), macOS, Windows 11 через WSL2 (Ubuntu).
* **Python:** 3.13 (строго `>=3.13, <3.14` согласно [`pyproject.toml`](../../pyproject.toml)).
* **Go:** 1.25.4+ или 1.26.4 (для модулей в `internal/` согласно [`go.mod`](../../go.mod)).
* **Node.js:** 20+ и пакетный менеджер `npm` (для фронтенда в `web/`).
* **Инфраструктурные сервисы:**
  * **MySQL** 8.0+ / MariaDB 10.6+
  * **Redis** 7.0+ (поддержка Pub/Sub, Distributed Locks)
  * **MinIO** / S3-совместимое объектное хранилище
  * **Elasticsearch** 8.x или **Infinity** (векторный движок RAGFlow)

---

## 2. Переменные окружения (Environment Variables)

> [!IMPORTANT]
> **ПРАВИЛО БЕЗОПАСНОСТИ:** Никогда не коммитьте значения боевых паролей и приватных ключей. Все боевые креды задаются через `.env` или менеджер секретов.

### Ключевые переменные ядра и криптографии:
- `RAGFLOW_SECRET_KEY`: **Обязателен**. Строка длиной не менее 32 символов (или 64-значный hex). Служит мастер-ключом для деривации HKDF ключей AES-256-GCM. Запрещено использовать дефолтные тестовые строки (fail-closed).
- `RAGFLOW_SECRET_KEYS_ROTATION`: Список ключей через запятую для бесшовного дешифрования старых данных (keyring decrypt-only).
- `QUART_RESPONSE_TIMEOUT`: Таймаут ответа HTTP-сервера (по умолчанию 600 сек).
- `QUART_BODY_TIMEOUT`: Таймаут чтения тела запроса (по умолчанию 600 сек).

### Переменные базы данных и инфраструктуры:
- `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB`: Параметры реляционной БД.
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`: Параметры подключения к Redis.
- `MINIO_HOST`, `MINIO_PORT`, `MINIO_USER`, `MINIO_PASSWORD`: Параметры хранилища файлов.
- `DOC_ENGINE`: Движок векторного поиска (`infinity` или `elasticsearch`).

### Переменные CRM-подсистемы:
- `RAGFLOW_CRM_B24_ZONES`: Разрешенные зоны для облачного Битрикс24 (по умолчанию: `ru,com,by,kz,uz,eu,de,es,fr,it,pl,in,cn,jp,id,vn,ae,mx,uk,com.tr`).
- `RAGFLOW_CRM_PRIVATE_ALLOWLIST_CIDR`: Список доверенных приватных IP-диапазонов для коробочного Битрикс24 (`bitrix24_onprem`).

---

## 3. Установка и запуск бэкенда (Python)

### Шаг 1: Подготовка виртуального окружения
```bash
# Клонирование и переход в проект
cd D:/ragflow/swipies_25/ragflow

# Создание виртуального окружения Python 3.13
python -m venv .venv

# Активация окружения (Windows PowerShell)
.venv\Scripts\Activate.ps1
# Или в Linux/WSL:
# source .venv/bin/activate

# Установка зависимостей проекта
pip install --upgrade pip
pip install -r requirements.txt
```

### Шаг 2: Инициализация базы данных и запуск сервера
```bash
# Экспорт обязательного крипто-ключа для локальной разработки
export RAGFLOW_SECRET_KEY="local-development-secret-key-32bytes-ok!"

# Запуск основного API-сервера
python api/ragflow_server.py
```
*Сервер запустится на `http://0.0.0.0:9380`.*

### Шаг 3: Запуск фоновых воркеров
В отдельных терминалах запускаются воркеры задач:
```bash
# Воркер парсинга и эмбеддинга документов
python rag/svr/task_executor.py

# Воркер синхронизации внешних Data Sources
python rag/svr/sync_data_source.py

# Воркер очередей Outbox для CRM (amoCRM/Bitrix24)
python rag/svr/crm_outbox_worker.py
```

---

## 4. Установка и запуск фронтенда (React / Web)

```bash
cd web

# Установка зависимостей
npm install

# Запуск сервера разработки с HMR
npm run dev
```
*Фронтенд доступен по адресу `http://localhost:5173`.*

---

## 5. Сборка и тестирование стека Go

Для работы с Go-компонентами в `internal/` учитывайте, что полный production-билд требует внешних нативных C-библиотек DeepDoc (`office_oxide.h`, `pdfium`). Для локальной разработки, валидации типов и прогона юнит-тестов сборка запускается в режиме `CGO_ENABLED=0`:

```bash
# Typecheck сервисов, хэндлеров и синкера без CGO-зависимостей
wsl bash -c "cd /mnt/d/ragflow/swipies_25/ragflow && CGO_ENABLED=0 go build -gcflags=-e ./internal/service/... ./internal/handler/... ./internal/syncer/..."

# Запуск юнит-тестов криптографии и маскирования
wsl bash -c "cd /mnt/d/ragflow/swipies_25/ragflow && go test -count=1 -v -run TestCrypto ./internal/utility/..."
wsl bash -c "cd /mnt/d/ragflow/swipies_25/ragflow && CGO_ENABLED=0 go test -v -run TestConnectorHandler_CredentialMaskingRealHandler ./internal/handler/..."
```

---

## 6. Запуск полного набора проверочных тестов

```bash
# 1. Тесты безопасности и криптографии коннекторов (15 тестов)
python -m unittest test.test_connector_security

# 2. Тесты CRM подсистемы (все модули)
python -m unittest test.test_crm_foundations
python -m unittest test.test_crm_amocrm
python -m unittest test.test_crm_bitrix24
python -m unittest test.test_crm_1c
python -m unittest test.test_crm_tool_and_outbox
python -m unittest test.test_crm_data_source_connectors

# 3. Тесты изоляции MCP
python -m unittest test.test_mcp_security
```
