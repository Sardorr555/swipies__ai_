<!-- Шаблон Pull Request в репозиторий Swipies RAGFlow -->

## Описание изменений
Кратко опишите суть предлагаемых изменений, решаемую проблему или добавляемую фичу:
- Что изменено:
- Почему это необходимо:
- Ссылки на связанные задачи / issues / ADR:

## Тип изменений
- [ ] Исправление ошибки (Bug fix)
- [ ] Новая функциональность (Feature)
- [ ] Оптимизация производительности (Performance improvement)
- [ ] Безопасность и криптография (Security hardening)
- [ ] Рефакторинг (Refactoring)
- [ ] Обновление документации (Documentation)

## Чеклист проверки кода и безопасности
- [ ] **Безопасность секретов:** Код **НЕ содержит** открытых API-ключей, токенов, паролей или статических дефолтных секретов. Все учетные данные маскируются в логах.
- [ ] **Криптография:** Чувствительные поля используют `api/utils/key_crypto.py` (AES-256-GCM + HKDF) и соответствуют [ADR-001](docs/knowledge-base/decisions/ADR-001-connector-cryptography-fail-closed.md).
- [ ] **Изоляция B2B/Ads:** Новые бизнес-сущности и коннекторы CRM изолированы от Swipies Ads ([ADR-002](docs/knowledge-base/decisions/ADR-002-crm-subsystem-isolation.md), [ADR-003](docs/knowledge-base/decisions/ADR-003-ads-subsystem-decoupling.md)).
- [ ] **Тестирование:** Добавлены модульные тесты. Все локальные тесты проходят успешно (`test/test_crm_system.py`, `test/test_ai_infrastructure.py`).
- [ ] **Обновление Базы Знаний:**
  - [ ] Обновлен соответствующий раздел в `docs/knowledge-base/` (если затронута архитектура, API или интеграции).
  - [ ] Создан ADR в `docs/knowledge-base/decisions/` (если принято новое архитектурное решение).
  - [ ] Добавлен Handoff в `docs/knowledge-base/handoffs/` (если передается эстафета следующему исполнителю).
  - [ ] Обновлен статус в `docs/knowledge-base/current-state.md` или `roadmap.md`.
