# Текущее состояние системы (Current State)

> **Статус документа:** Актуален  
> **Дата последней проверки:** 2026-10-15  
> **Основная ветка:** `test` (commit `a9b3e9f28`)

---

## 1. Сводная матрица готовности компонентов

| Подсистема / Компонент | Статус реализации | Статус тестов | Ограничения и особенности |
| :--- | :---: | :---: | :--- |
| **Криптография коннекторов** | **Завершено** | 100% PASS (15/15) | AES-256-GCM + HKDF, ротация keyring, decrypt-only для дефолтов |
| **Маскирование в API** | **Завершено** | 100% PASS (мутация проверена) | Защита GET/POST/PATCH коннекторов от утечки в тело ответа |
| **CLI миграции учетных данных** | **Завершено** | Проверено `--dry-run` | `api/scripts/migrate_connector_credentials.py` |
| **CRM Ядро и Лицензионный гейт** | **Завершено** | 100% PASS | Требует `features: ["crm"]` в лицензии, fail-closed |
| **amoCRM / Kommo Адаптер** | **Завершено** | 100% PASS | OAuth2 с фехтованием версий `token_version` и Redis-локом |
| **Bitrix24 Адаптер** | **Завершено** | 100% PASS | Входящие вебхуки, 2 req/s лимитер, маскирование пути токена |
| **1С:Предприятие (Остатки)** | **Завершено** | 100% PASS | OData v3/v4, read-only вызовы баланса номенклатуры |
| **CRM Outbox Worker** | **Завершено** | 100% PASS | Лизинг записей, экспоненциальный бэкофф, дедупликация |
| **Агентские CRM-тулы** | **Завершено** | 100% PASS | `check_stock`, `create_incoming_lead`, `query_crm_records` |
| **CRM как Data Source (RAG)** | **Завершено** | 100% PASS | Индексация лидов, контактов, сделок в базы знаний |
| **Пользовательская телеметрия & Аналитика активности** | **Завершено** | 100% PASS | Сбор кликов, времени в модулях, DAU, отдельный раздел в админке |
| **Swipies Ads Engine** | **Завершено** | Проверено | 36 таблиц БД, 14 вкладок UI, спонсорские промпты для Free |
| **Atmos Payment & Billing** | **Завершено** | Проверено | Подписки, промокоды, DEV merchant (store_id 10577) |
| **Go-стек (`internal/`)** | **Частично** | CGO=0 PASS | Go-ветка требует `CGO_ENABLED=0` из-за багов CGO в upstream |
| **Защита Canvas DSL** | **Ограничение** | Требует внимания | DSL Canvas по-прежнему хранит обычные параметры нод в plaintext |

---

## 2. Подробный статус реализованных решений

### 2.1. Криптография и безопасность коннекторов (Commits `782f74d46`, `c407eb409`, `3bb88c257`)
- **Статус:** Полностью реализовано и влито в ветку `test`.
- **Файлы:** [`api/utils/key_crypto.py`](../../api/utils/key_crypto.py), [`internal/utility/crypto.go`](../../internal/utility/crypto.go), [`api/scripts/migrate_connector_credentials.py`](../../api/scripts/migrate_connector_credentials.py).
- **Результаты проверки:** Все 15 тестов в [`test/test_connector_security.py`](../../test/test_connector_security.py) проходят успешно.
- **Подтверждённые инварианты:**
  - Шифрование с незаданным, коротким (<32 символов) или дефолтным ключом немедленно прерывается (`InsecureSecretKeyError` / `ErrInsecureSecretKey`).
  - Чтение старых шифротекстов `enc:v1:` поддерживается без потерь.
  - Дефолтные тестовые ключи в переменной `RAGFLOW_SECRET_KEYS_ROTATION` работают исключительно на расшифровку исторических данных.
  - При отправке маскированного значения `********` в PATCH-запросе существующий секрет сохраняется в базе без перезаписи.

### 2.2. CRM v1 Интеграция (Commits `4612f87b4` — `6a35606d0`)
- **Статус:** Ядро, адаптеры, воркер и инструменты завершены и покрыты тестами.
- **Файлы:**
  - Модели: [`api/db/crm_models.py`](../../api/db/crm_models.py) (`TenantCRMConfig`, `CRMOutboxLead`, `CRMRecordCache`).
  - Сервис: [`api/db/services/crm_service.py`](../../api/db/services/crm_service.py).
  - Адаптеры: [`api/crm/clients/amocrm.py`](../../api/crm/clients/amocrm.py), [`bitrix24.py`](../../api/crm/clients/bitrix24.py), [`one_c.py`](../../api/crm/clients/one_c.py), [`hubspot.py`](../../api/crm/clients/hubspot.py).
  - Инструменты агента: [`agent/tools/check_stock.py`](../../agent/tools/check_stock.py), [`create_incoming_lead.py`](../../agent/tools/create_incoming_lead.py), [`query_crm_records.py`](../../agent/tools/query_crm_records.py).
  - Коннекторы баз знаний: [`common/data_source/amocrm_connector.py`](../../common/data_source/amocrm_connector.py), [`bitrix24_connector.py`](../../common/data_source/bitrix24_connector.py), [`onec_connector.py`](../../common/data_source/onec_connector.py), [`hubspot_connector.py`](../../common/data_source/hubspot_connector.py).
  - Воркер Outbox: [`rag/svr/crm_outbox_worker.py`](../../rag/svr/crm_outbox_worker.py).
- **Результаты проверки:**
  - `test_crm_foundations.py`: PASS.
  - `test_crm_amocrm.py`: PASS (эмуляция гонки обновления токенов с проверкой `token_version`).
  - `test_crm_bitrix24.py`: PASS (блокировка SSRF, DNS-pinning, ретраи при 429).
  - `test_crm_1c.py`: PASS (парсинг OData XML/JSON, маскирование базовой авторизации).
  - `test_crm_tool_and_outbox.py`: PASS (проверка лизинга и дедупликации).

### 2.3. Телеметрия и Аналитика активности пользователей (User Activity & Platform Telemetry)
- **Статус:** Полностью реализовано (Backend + Frontend SDK + Admin Panel Dashboard).
- **Файлы:**
  - Модель данных: [`api/db/telemetry_models.py`](../../api/db/telemetry_models.py) (`UserActivityEvent`).
  - Сервис агрегации: [`api/db/services/telemetry_service.py`](../../api/db/services/telemetry_service.py).
  - API эндпоинты: [`api/apps/telemetry_app.py`](../../api/apps/telemetry_app.py) (сбор), [`api/apps/user_activity_app.py`](../../api/apps/user_activity_app.py) (админка).
  - Frontend SDK: [`web/src/utils/telemetry.ts`](../../web/src/utils/telemetry.ts).
  - Admin Panel Dashboard: [`web/src/pages/admin/user-activity/index.tsx`](../../web/src/pages/admin/user-activity/index.tsx).
  - Маршрут: `/admin/user-activity` (пункт меню "Foydalanuvchilar Faoliyati & Telemetriya").
- **Результаты проверки:**
  - Тесты [`test/test_user_activity_telemetry.py`](../../test/test_user_activity_telemetry.py): 5/5 PASS.
  - Oxlint проверка TypeScript кода: 0 errors, 0 warnings.
- **Подтверждённые возможности:**
  - Автоматический учет времени пребывания в каждом модуле (Dwell time) и переходов между страницами.
  - Автоматический сбор кликов по кнопкам и интерактивным элементам с их метками.
  - Защита данных: автоматическое вырезание паролей, токенов и секретов из метаданных.
  - Дашборд в админ-панели: DAU, распределение времени по модулям (Donut Chart), рейтинг самых нажимаемых кнопок (Bar Chart), таблица активности пользователей, 24-часовой график активности и живая лента событий.

---

## 3. Известные ограничения и технический долг

1. **Открытый текст в Canvas DSL и MCP Server:**
   - Модели `UserCanvas.dsl` ([`api/db/db_models.py:1641`](../../api/db/db_models.py#L1641)) и `MCPServer.headers` ([`api/db/db_models.py:1682`](../../api/db/db_models.py#L1682)) хранят конфигурацию нод в нешифрованном виде.
   - **Решение в CRM:** Мы целенаправленно обошли эту уязвимость: секреты CRM не хранятся в нодах Canvas, а извлекаются на лету из зашифрованной таблицы `TenantCRMConfig` по `tenant_id`.
2. **Go Upstream Build:**
   - upstream репозиторий `infiniflow/ragflow` v0.27.2 содержит ошибки компиляции Go в `internal/dao/tenant_model_provider.go` и `internal/service/user.go`. В ветке `test` они исправлены локально, но сборка полного бинарника требует CGO и проприетарных библиотек `office_oxide`. Разработка бизнес-логики продолжается на Python.
3. **Bitrix24 OAuth:**
   - Для v1 интеграция с Битрикс24 работает через входящие вебхуки (`inbound webhooks`). Полноценное OAuth-приложение для коробочных порталов отложено на CRM v2.

## 2026-10-26 — external agent access on swipies_26

Added a Python MCP facade, authenticated operation discovery, isolated Free service-account bootstrap and a stdio client that registers/reconnects without a browser. Branding omission requires an active persisted Plus/Pro subscription. See [implementation and release conditions](agent-access.md). After the owner updated the server, a repeat live audit confirmed the model-type correction: chatbot inference, document parsing to DONE with a chunk, embedding retrieval, and a document-grounded RAG reply with references all passed. MCP CRUD, repeated uploads, Free attribution, persisted agent attribution, tenant isolation and both official-SDK transports also passed. The run logged 94 successful assertions and no failures; test resources were deleted. See [repeat live audit](handoffs/2026-10-26-live-recheck.md). Paid-account runtime attribution and actual external database/OAuth connections remain untested. No schema migration or Go implementation was added.
