# Реестр архитектурных решений (Architecture Decision Records)

**Текущее состояние базы знаний:** актуально на **15 октября 2026 года**  
**Базовая ветка:** `test` (`a9b3e9f28`)  

---

## 1. Назначение и формат

Каждое фундаментальное архитектурное, инфраструктурное решение или изменение в области безопасности фиксируется в виде Architecture Decision Record (ADR). ADR документирует контекст, рассмотренные альтернативы, принятое решение и его последствия для кодовой базы.

Для оформления новых решений используйте [Шаблон ADR](../templates/decision-template.md).

---

## 2. Индекс принятых решений

| ID | Название решения | Статус | Дата | Автор | Область воздействия |
|---|---|---|---|---|---|
| [ADR-001](ADR-001-connector-cryptography-fail-closed.md) | **Fail-Closed криптография коннекторов и связка ключей (Keyring)** | Принято | 2026-10-14 | Swipies Security / Sardor | `api/utils/key_crypto.py`, `internal/utility/crypto.go` |
| [ADR-002](ADR-002-crm-subsystem-isolation.md) | **Изоляция подсистемы CRM и двухстадийная доставка через Outbox** | Принято | 2026-10-15 | Swipies Architecture / Sardor | `api/db/db_models.py`, `agent/tools/crm_*`, `api/crm/` |
| [ADR-003](ADR-003-ads-subsystem-decoupling.md) | **Архитектурное отделение рекламной подсистемы Swipies Ads от ядра B2B** | Принято | 2026-10-15 | Swipies Architecture / Sardor | `api/db/db_models.py`, `api/plugins/swipies_ads/` |
| [ADR-004](ADR-004-python-over-go-for-business-modules.md) | **Выбор Python вместо Go для реализации бизнес-модулей CRM и агентов** | Принято | 2026-10-15 | Swipies Tech Lead / Sardor | `agent/`, `api/crm/`, `internal/` |

---

## 3. Жизненный цикл архитектурного решения

- **Предложено (Proposed):** Черновик решения обсуждается командой.
- **Принято (Accepted):** Решение утверждено и обязательно для следования всеми разработчиками и AI-агентами.
- **Заменено (Superseded):** Решение утратило актуальность и заменено более новым ADR (со ссылкой на новый документ).
- **Отклонено (Rejected):** Решение отклонено после анализа рисков.
