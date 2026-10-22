# Передача контекста: CRM v1, Защита секретов и База знаний

- **Дата фиксации:** 15 октября 2026 года
- **Автор передачи:** Sardor (<albakiev.sardorbek@gmail.com>) / Antigravity AI
- **Рабочая директория:** `D:\ragflow\swipies_25\ragflow`
- **Текущая ветка:** `test`
- **Текущий коммит:** `a9b3e9f28` (`sync test with swipies_ai/test`)
- **Базовый коммит upstream:** `c4d9f3e3c` / `a024bea0c` (RAGFlow v0.27.2)

---

## 1. Краткое резюме проделанной работы

За текущую рабочую сессию были выполнены следующие ключевые инженерные задачи:

1. **Решение проблем криптографии и безопасности ключей (Fail-Closed Keyring):**
   - Устранен дефолтный ключ `ragflow_single_global_instance_master_secret_2026` из боевой конфигурации.
   - Внедрена связка ключей (Keyring) с алгоритмом AES-256-GCM и RFC 5869 HKDF в [api/utils/key_crypto.py](../../api/utils/key_crypto.py) и [internal/utility/crypto.go](../../internal/utility/crypto.go).
   - Запрещено шифрование данных на дефолтных ключах (`InsecureKeyError`), при этом сохранена возможность расшифрования архивных данных через `RAGFLOW_SECRET_KEYS_ROTATION`.
   - Создан безопасный шаблон конфигурации [docker/.env.example](../../docker/.env.example).
2. **Исследование кодовой базы и связности Swipies Ads:**
   - Выявлено 36 таблиц рекламы в [api/db/db_models.py](../../api/db/db_models.py) и 14 вкладок в `web/src/pages/ads/`.
   - Обнаружена уязвимость открытого хранения секретов в `UserCanvas.dsl` и `MCPServer.headers`.
   - Принято решение не использовать открытый Canvas DSL для корпоративных CRM-кредов.
3. **Реализация подсистемы CRM v1 (amoCRM, Bitrix24, 1С, HubSpot):**
   - Добавлены изолированные модели БД: `TenantCRMConfig`, `CRMOutboxTask`, `CRMAuditLog` ([api/db/db_models.py#L1250-L1350](../../api/db/db_models.py)).
   - Реализована двухстадийная схема:
     - **Live Read:** Синхронный инструмент [agent/tools/crm_stock_check.py](../../agent/tools/crm_stock_check.py) с таймаутом 3.0с, Circuit Breaker (3 ошибки / 30с) и вежливым fallback.
     - **Transactional Outbox:** Инструмент [agent/tools/crm_lead_create.py](../../agent/tools/crm_lead_create.py) валидирует лид и атомарно записывает задачу в БД за 10 мс.
     - **Outbox Worker:** Фоновый обработчик [api/crm/tasks/outbox_worker.py](../../api/crm/tasks/outbox_worker.py) с дедупликацией по idempotency key, экспоненциальным backoff и Leaky Bucket rate limiter (2 req/s для Bitrix24).
   - Все 23 модульных теста (`test/test_crm_system.py`) проходят со статусом `OK`.
4. **Создание всеобъемлющей инженерной базы знаний (Knowledge Base):**
   - Написаны корневой регламент [AGENTS.md](../../AGENTS.md), карты репозитория, архитектурные диаграммы, описания интеграций, реестр проблем, ADRs и шаблоны.

---

## 2. Карта созданных и модифицированных файлов

| Файл | Описание изменений |
|---|---|
| [AGENTS.md](../../AGENTS.md) | Регламент работы автономных AI-агентов и разработчиков |
| [docker/.env.example](../../docker/.env.example) | Безопасный шаблон конфигурации окружения |
| [api/utils/key_crypto.py](../../api/utils/key_crypto.py) | Fail-Closed Keyring (AES-256-GCM + HKDF) |
| [internal/utility/crypto.go](../../internal/utility/crypto.go) | Go-реализация совместимого шифрования |
| [api/db/db_models.py](../../api/db/db_models.py) | Таблицы `TenantCRMConfig`, `CRMOutboxTask`, `CRMAuditLog` |
| [agent/tools/crm_lead_create.py](../../agent/tools/crm_lead_create.py) | Агентский инструмент создания сделок |
| [agent/tools/crm_stock_check.py](../../agent/tools/crm_stock_check.py) | Агентский инструмент проверки остатков 1С |
| [api/crm/tasks/outbox_worker.py](../../api/crm/tasks/outbox_worker.py) | Асинхронный воркер доставки сделок |
| [api/crm/adapters/](../../api/crm/adapters/) | Сетевые адаптеры amoCRM, Bitrix24, 1С, HubSpot |
| [test/test_crm_system.py](../../test/test_crm_system.py) | Набор из 23 тестов CRM-подсистемы |
| [test/test_ai_infrastructure.py](../../test/test_ai_infrastructure.py) | Набор тестов безопасности и ротации крипто-ключей |
| `docs/knowledge-base/*` | Полная инженерная база знаний и архитектурные решения (ADRs) |

---

## 3. Команды проверки работоспособности

Все команды выполняются в директории `D:\ragflow\swipies_25\ragflow`:

```bash
# 1. Запуск тестов CRM-системы (23 теста: Rate Limiting, Circuit Breaker, Outbox, Encryption)
python -m unittest test/test_crm_system.py -v

# 2. Запуск тестов криптографии и ротации ключей
python -m unittest test/test_ai_infrastructure.py -v

# 3. Проверка статуса Git
git status
```

---

## 4. Ограничения и запрещенные действия

1. **Запрещены:** `git push`, автоматический деплой, применение боевых миграций (`--apply`).
2. **Запрещена:** публикация или печать открытых значений секретов (только маскированный вид `3113...bbd` или `[REDACTED]`).
3. **Автор коммитов строго:** `Sardor <albakiev.sardorbek@gmail.com>`.

---

## 5. Задачи для следующей сессии (Что делать дальше)

1. **Реализация REST Webhook Receiver для Bitrix24 / amoCRM:**
   - Добавить контроллер в `api/apps/crm_app.py` для приема входящих статусов сделок из CRM и обновления контекста диалогов.
2. **Шифрование Canvas DSL и MCP Server:**
   - Наложить сериализатор `encrypt_field_for_tenant` на поле `UserCanvas.dsl` и `MCPServer.headers`, чтобы закрыть найденный upstream security risk (Issue #002).
3. **Фронтенд-компоненты настроек CRM:**
   - Разработать интерфейс настройки коннекторов CRM в веб-панели управления (`web/src/pages/workspace/crm/`).
