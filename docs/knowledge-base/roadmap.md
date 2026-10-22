# Дорожная карта развития (Roadmap) Swipies RAGFlow

**Текущее состояние базы знаний:** актуально на **15 октября 2026 года**  
**Базовая ветка:** `test` (`a9b3e9f28`)  
**Базовый upstream:** `v0.27.2` (`a024bea0c`)

---

## 1. Стратегическое видение

Развитие платформы Swipies RAGFlow разделено на два параллельных трека:
1. **Core / B2B AI Enterprise Platform:** многофункциональный RAG + диалоговые AI-агенты с интеграцией в корпоративные контуры (CRM, ERP, складские системы), строгой криптографической защитой секретов и поддержкой On-Premise/Private Cloud развертывания без рекламной подсистемы.
2. **Swipies Ad-Network Edition:** специализированная редакция для монетизации трафика и работы с кампаниями Swipies Ads (in-chat promo, fraud detection, clickhouse analytics, web tracking).

Главный архитектурный приоритет — **полная изоляция Swipies Ads от бизнес-ядра** (ADR-002, ADR-003), что позволит собирать лицензионную B2B-версию простым переключением feature-флагов без кодовых форков.

---

## 2. Краткосрочные задачи (Текущий спринт / Q4 2026)

### 2.1. CRM Subsystem: Завершение фазы v1.1
- [x] **Архитектурный каркас CRM v1:** выделенные таблицы `TenantCRMConfig`, `CRMOutboxTask`, `CRMAuditLog` ([api/db/db_models.py#L1250-L1350](../../api/db/db_models.py)).
- [x] **Криптографическая изоляция кредов:** хранение токенов amoCRM/Bitrix24/1C через AES-256-GCM + HKDF (`api/utils/key_crypto.py`).
- [x] **Live-проверка остатков 1С:** OData v4 клиент со строгим таймаутом (3.0 сек), circuit breaker и circuit fallback.
- [x] **Асинхронный Outbox Worker:** надежная доставка сделок с экспоненциальным backoff и дедупликацией по idempotency key (`api/crm/tasks/outbox_worker.py`).
- [x] **Тестовое покрытие ядра CRM:** 23 модульных теста (`test/test_crm_system.py`) проходят со статусом OK.
- [ ] **Доработка Webhook Receiver для Bitrix24/amoCRM:**
  - Реализация endpoint'ов обратной связи (`/v1/crm/webhook/bitrix24`, `/v1/crm/webhook/amocrm`) для обновления статусов сделок внутри сессий диалогов.
  - Проверка входящих подписей webhook (HMAC-SHA256) для предотвращения подделки событий.
- [ ] **UI-компоненты настроек CRM в веб-интерфейсе:**
  - Добавление вкладки CRM в настройки рабочего пространства (`web/src/pages/workspace/crm/`).
  - Формы ввода учетных данных с маскированием и проверкой связи на лету (`/v1/crm/config/test`).

### 2.2. Устранение технических долгов безопасности
- [ ] **Миграция Canvas DSL и MCP Server:**
  - Перевод открытых секретов из `UserCanvas.dsl` и `MCPServer.headers` на единый механизм шифрования `encrypt_field_for_tenant`.
  - Добавление проверки API-ключей в REST-ручках агентов перед сохранением в БД.
- [ ] **Bitrix24 SSRF / Zone Restriction:**
  - Усиление валидации домена входящего webhook (`*.bitrix24.ru`, `*.bitrix24.com`, `*.bitrix24.by`, `*.bitrix24.kz` или валидированный кастомный FQDN с On-Premise лицензией).

---

## 3. Среднесрочные задачи (Q1 2027)

### 3.1. Двусторонняя синхронизация CRM (v2)
- **Коннекторы реального времени:**
  - Поддержка WebSocket/Long-polling уведомлений от amoCRM и Bitrix24.
  - Автоматическое обогащение клиентского профиля в векторной базе (Knowledge Graph) при закрытии этапов воронки в CRM.
- **Поддержка сложных номенклатур 1C:**
  - Парсинг характеристик, серийных номеров, складов резервирования и динамических цен через 1C Web Services (SOAP / HTTP Services вместо базового OData).
  - Локальное LRU/Redis-кэширование остатков высокой частоты с TTL = 15 секунд для снижения нагрузки на сервер 1С.

### 3.2. Архитектурная изоляция Swipies Ads
- **Модуляризация пакета `api/db/db_models.py`:**
  - Вынос 36 рекламных моделей (`AdCampaign`, `AdFraud`, `AdCreative`, `SwipiesClickTrack` и др.) в подключаемый плагин `api/plugins/swipies_ads/models.py`.
  - Очистка базового файла моделей до состояния чистого upstream RAGFlow.
- **Разделение миграций базы данных:**
  - Изоляция версий Peewee/Alembic: миграции рекламных таблиц выносятся в отдельную директорию `api/plugins/swipies_ads/migrations/`.
  - Запуск платформы в режиме `SWIPIES_EDITION=core` не создает и не проверяет таблицы рекламы.
- **Инъекции в промпты:**
  - Полный перенос логики `inject_ad_into_prompt` из `api/db/services/llm_service.py` в промежуточный middleware/interceptor с проверкой лицензии тенанта.

### 3.3. Стабилизация и модульность Go Runtime
- **Разрешение upstream-проблем CGO:**
  - Создание чистых Go-заглушек (build tags `!cgo` или `-tags nocgo`) для библиотеки `office_oxide.h`.
  - Исправление сигнатур upstream в Go (`tenant_model_provider.go:62`, `user.go:150/156`), чтобы модули `internal/service/connector.go` и `internal/utility/crypto.go` компилировались штатно без локальных хаков.
- **Синхронизатор документов (Go Syncer):**
  - Подключение коннектора CRM-данных к Go Syncer для периодического создания векторных snapshot'ов каталогов товаров без блокировки Python GIL.

---

## 4. Долгосрочные инициативы (Q2-Q3 2027)

### 4.1. Enterprise On-Premise Bundle
- Упаковка платформы для изолированных контуров (Air-Gapped окружения):
  - Автономный Docker Compose / Helm Chart без внешних сетевых зависимостей.
  - Полная поддержка локальных LLM (через vLLM / Ollama / LocalAI) и векторных баз (Infinity / Elasticsearch On-Premise).
  - Поддержка аппаратных HSM-модулей и Vault для хранения мастер-ключа шифрования секретов тенантов.

### 4.2. Мульти-агентная оркестрация B2B
- Расширение движка Agent Canvas:
  - Поддержка вложенных подграфов выполнения (Sub-Agents / Hierarchical Multi-Agent Systems).
  - Специализированные системные агенты: Бухгалтер (1С), Менеджер продаж (amoCRM/Bitrix), Саппорт-инженер (Knowledge Base).
  - Распределенный трассировщик диалогов на базе OpenTelemetry с привязкой ID сделок CRM к трассировкам LLM-генераций.

---

## 5. Матрица версий и этапов реализации

| Фича / Модуль | Статус | Целевой релиз | Ответственный слой | Ключевые файлы |
|---|---|---|---|---|
| **Fail-Closed Crypto Keyring** | Завершено | v0.27.2-sec1 | Python + Go Core | `api/utils/key_crypto.py`, `internal/utility/crypto.go` |
| **CRM Core: outbox, audit, configs** | Завершено | v0.28.0-crm1 | Python Backend | `api/db/db_models.py`, `api/crm/tasks/outbox_worker.py` |
| **1C Stock Check OData Tool** | Завершено | v0.28.0-crm1 | Agent Tools | `agent/tools/crm_stock_check.py` |
| **amoCRM / Bitrix24 Lead Tool** | Завершено | v0.28.0-crm1 | Agent Tools | `agent/tools/crm_lead_create.py` |
| **Bitrix24 Incoming Webhooks** | Запланировано | v0.28.1 | REST API | `api/apps/crm_app.py` |
| **CRM Settings Web UI** | Запланировано | v0.28.1 | React Frontend | `web/src/pages/workspace/crm/` |
| **Ads Models Plugin Extraction** | В разработке | v0.29.0 | Database/Plugin | `api/plugins/swipies_ads/` |
| **Canvas DSL Plaintext Fix** | Запланировано | v0.28.2 | Agent Core | `api/db/services/canvas_service.py` |
| **Go Syncer CGO Decoupling** | Запланировано | v0.29.0 | Go Backend | `internal/syncer/`, `internal/utility/` |
| **Air-Gapped Enterprise Helm** | Исследование | v0.30.0 | DevOps / Helm | `docker/helm/` |
