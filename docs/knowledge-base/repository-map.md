# Карта репозитория (Repository Map)

> **Статус документа:** Актуален  
> **Дата последней проверки:** 2026-10-15  
> **Основная ветка:** `test`

---

## 1. Общая структура каталогов верхнего уровня

```text
D:/ragflow/swipies_25/ragflow/
├── admin/                 # Админ-сервер и дополнительные маршруты администрирования
├── agent/                 # Ядро автономных агентов и визуального Canvas (Python)
├── api/                   # REST API бэкенд на Quart (контроллеры, сервисы, БД, CRM)
├── common/                # Общие утилиты, коннекторы внешних систем, настройки
├── docker/                # Dockerfiles, docker-compose, скрипты развертывания
├── docs/                  # Документация проекта и инженерная база знаний
│   └── knowledge-base/    # Единая база знаний для команды и ИИ-агентов
├── internal/              # Go-реализация ядра RAGFlow (микросервисы, DAO, парсеры)
├── mcp/                   # Клиент и сервер Model Context Protocol (MCP)
├── rag/                   # Алгоритмы RAG, DeepDoc, воркеры фоновых задач, LLM-клиенты
├── specs/                 # Спецификации функционала (001 Model Access, 002 Ads, 003 CRM)
├── test/                  # Комплексный набор тестов (Python юнит- и интеграционные тесты)
├── web/                   # Фронтенд на React 18, Vite, TypeScript, Ant Design, Tailwind
├── pyproject.toml         # Манифест Python-зависимостей (версия 0.27.2)
├── go.mod                 # Манифест Go-модулей (go 1.26.4)
└── AGENTS.md              # Главные инструкции для разработчиков и ИИ-агентов
```

---

## 2. Детальный разбор ключевых модулей

### 2.1. `api/` — Сервер приложений (Quart Async Backend)
* [`api/ragflow_server.py`](../../api/ragflow_server.py): Главная точка входа backend-сервера. Инициализирует таблицы БД, регистрирует роуты, запускает фоновый таймер прогресса задач и стартует Quart ASGI сервер.
* [`api/apps/`](../../api/apps/): Контроллеры и HTTP-эндпоинты.
  * [`api/apps/__init__.py`](../../api/apps/__init__.py): Динамический автодискаверинг и регистрация блюпринтов (`*_app.py` и `restful_apis/*.py`).
  * [`api/apps/ad_app.py`](../../api/apps/ad_app.py): Контроллер рекламного движка Swipies Ads (3255 строк).
  * [`api/apps/ai_management_app.py`](../../api/apps/ai_management_app.py): Контроллер управления политиками AI-моделей и BYOK.
  * [`api/apps/payment_app.py`](../../api/apps/payment_app.py): Контроллер платежей Atmos и биллинга.
  * [`api/apps/telemetry_app.py`](../../api/apps/telemetry_app.py): Публичный/авторизованный приемник батчей телеметрии поведения пользователей (`POST /v1/telemetry/events`).
  * [`api/apps/user_activity_app.py`](../../api/apps/user_activity_app.py): Административный API аналитики использования платформы (`GET /v1/admin/user-activity/*`: overview, modules, clicks, users, timeline, events, features).
  * [`api/apps/restful_apis/agent_api.py`](../../api/apps/restful_apis/agent_api.py): REST API для создания, версионирования и исполнения Canvas-агентов.
  * [`api/apps/restful_apis/connector_api.py`](../../api/apps/restful_apis/connector_api.py): Управление коннекторами с маскированием учетных данных `********`.
  * [`api/apps/restful_apis/mcp_api.py`](../../api/apps/restful_apis/mcp_api.py): Управление серверами MCP.
* [`api/crm/`](../../api/crm/): Изолированная CRM-подсистема (amoCRM, Bitrix24, 1С, HubSpot).
  * [`api/crm/base.py`](../../api/crm/base.py): Абстрактный контракт `CRMProviderBase`.
  * [`api/crm/transport.py`](../../api/crm/transport.py): Безопасный HTTP-транспорт с SSRF-защитой, DNS-pinning и ретраями.
  * [`api/crm/license_gate.py`](../../api/crm/license_gate.py): Fail-closed лицензионный гейт (`features: ["crm"]`).
  * [`api/crm/clients/`](../../api/crm/clients/): Реализации клиентов для `amocrm.py`, `bitrix24.py`, `one_c.py`, `hubspot.py`.
* [`api/db/`](../../api/db/): Слой баз данных и ORM Peewee.
  * [`api/db/db_models.py`](../../api/db/db_models.py): Модели БД ядра RAGFlow и рекламной подсистемы.
  * [`api/db/crm_models.py`](../../api/db/crm_models.py): Изолированные модели CRM (`TenantCRMConfig`, `CRMOutboxLead`, `CRMRecordCache`).
  * [`api/db/telemetry_models.py`](../../api/db/telemetry_models.py): Модель аудита и поведения пользователей `UserActivityEvent` (сессии, клики, время пребывания, фичи, модули).
  * [`api/db/services/`](../../api/db/services/): Сервисный слой работы с БД (`connector_service.py`, `crm_service.py`, `ad_engine_service.py`, `telemetry_service.py`, `user_service.py`).
* [`api/utils/key_crypto.py`](../../api/utils/key_crypto.py): Криптографический модуль AES-256-GCM + RFC 5869 HKDF для защиты кредов.

### 2.2. `agent/` — Агентский рантайм и инструменты Canvas
* [`agent/canvas.py`](../../agent/canvas.py): Движок исполнения графов Canvas. Управляет состоянием сессий, переменными и передачей данных между узлами.
* [`agent/component/`](../../agent/component/): Компоненты графа.
  * [`agent/component/agent_with_tools.py`](../../agent/component/agent_with_tools.py): Узел LLM-агента с поддержкой function calling tools и MCP-серверов.
  * [`agent/component/invoke.py`](../../agent/component/invoke.py): Универсальный HTTP-клиент вызова внешних API.
* [`agent/tools/`](../../agent/tools/): Инструменты, доступные агенту:
  * [`agent/tools/check_stock.py`](../../agent/tools/check_stock.py): Онлайн-проверка остатков на складе 1С.
  * [`agent/tools/create_incoming_lead.py`](../../agent/tools/create_incoming_lead.py): Создание сделки в Outbox очереди.
  * [`agent/tools/query_crm_records.py`](../../agent/tools/query_crm_records.py): Text-to-SQL поиск по CRM-записям.
  * `tavily.py`, `github.py`, `deepl.py`, `email.py`, `exesql.py`.
* [`agent/templates/`](../../agent/templates/): Готовые DSL-шаблоны агентов (например, `crm_sales_intelligence_agent.json`).

### 2.3. `rag/` — Поисково-генеративное ядро и фоновые процессы
* [`rag/svr/task_executor.py`](../../rag/svr/task_executor.py): Воркер извлечения текста и чанкинга документов из очереди Redis.
* [`rag/svr/sync_data_source.py`](../../rag/svr/sync_data_source.py): Воркер фоновой синхронизации данных из сторонних коннекторов в базы знаний.
* [`rag/svr/crm_outbox_worker.py`](../../rag/svr/crm_outbox_worker.py): Outbox воркер гарантированной доставки лидов в amoCRM и Bitrix24.
* [`rag/intelligence/`](../../rag/intelligence/): Слой анализа диалогов (извлечение сущностей, тональности, решений).

### 2.4. `common/` — Общие компоненты и коннекторы
* [`common/data_source/`](../../common/data_source/): Драйверы коннекторов данных для Jira, Confluence, S3, Salesforce, amoCRM, Bitrix24, 1С, HubSpot.
* [`common/ssrf_guard.py`](../../common/ssrf_guard.py): Защита от обращения к внутренним подсетям и SSRF.
* [`common/settings.py`](../../common/settings.py): Загрузка и валидация конфигурации окружения.

### 2.5. `internal/` — Стек на языке Go
* [`internal/dao/`](../../internal/dao/), [`internal/service/`](../../internal/service/), [`internal/handler/`](../../internal/handler/): Go-порты сервисов авторизации, пользователей и коннекторов.
* [`internal/utility/crypto.go`](../../internal/utility/crypto.go): Кросс-языковая реализация AES-256-GCM дешифрования коннекторов, синхронизированная с Python.

### 2.6. `web/` — Пользовательский интерфейс (React Frontend)
* [`web/src/utils/telemetry.ts`](../../web/src/utils/telemetry.ts): Автономный SDK сбора телеметрии (Dwell time, делегированный перехват кликов, семантический парсер иконок, API feature mapping, sendBeacon flush).
* [`web/src/pages/admin/user-activity/`](../../web/src/pages/admin/user-activity/): Дашборд аналитики активности и метрик пользователей (KPI, графики Recharts, матрица фичей, аудит-лог).
* [`web/src/pages/agent/canvas/`](../../web/src/pages/agent/canvas/): Визуальный редактор агентских графов.
* [`web/src/pages/user-setting/data-source/`](../../web/src/pages/user-setting/data-source/): Подключение и настройка коннекторов данных (CRM, Cloud, Wikis).
* [`web/src/pages/ads/`](../../web/src/pages/ads/): Панель управления рекламными кампаниями и статистикой.
* [`web/src/pages/admin/dashboard/`](../../web/src/pages/admin/dashboard/): Панель суперпользователя и аналитика платформы.
