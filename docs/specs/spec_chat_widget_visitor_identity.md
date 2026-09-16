# SPECIFY: Chat Widget — Visitor Identity, история сессий, навигация Messages

## WHY
Виджет чат-бота на базе RAGFlow (iframe-встройка на сайтах клиентов) терял историю диалога посетителя при перезагрузке страницы и не давал доступа к прошлым обращениям. Параллельно была обнаружена дыра изоляции данных между посетителями, закрытая принципом Deny-by-Default.

Цель — поднять UX виджета до уровня современных support-виджетов (паттерны навигации Intercom Messenger: сразу открытый диалог → выход в список чатов Messages → переключение между сессиями → "+ New Conversation") с гарантией строгой изоляции данных.

---

## ACCEPTANCE CRITERIA (AC)

### AC1: Visitor Identity
- Генерация криптографически стойкого UUIDv4 через `crypto.getRandomValues`.
- Сохранение в `localStorage` iframe под ключом `swipies_visitor_id`.
- Никакой передачи `visitor_id` через URL query-параметры или Referer.
- Fallback при блокировке хранилища (Safari ITP / Incognito): in-memory ID на время сессии страницы + ненавязчивый закрываемый баннер-предупреждение (`StorageWarningBanner`).

### AC2: Backend Sessions & Zero-Leakage Isolation
- Эндпоинт `GET /api/v1/chatbots/<dialog_id>/sessions`.
- Жёсткая валидация заголовка `X-Visitor-Id` по regex UUIDv4: отсутствие или невалидный формат → **HTTP 200 с `{"code": 101 (ARGUMENT_ERROR), "data": null}`**, по единому паттерну с остальными эндпоинтами RAGFlow REST API. Фронтенд обязан проверять `json.code === 0`, а не `response.status`/`response.ok`.
- Фильтрация сессий строго по `user_id == visitor_id`.
- В эндпоинте `chatbot_completions`: `if conv.user_id != visitor_id: raise AssertionError("Session does not belong to this visitor")`. Легаси-сессии без `user_id` (`None`) и сессии других посетителей недоступны.

### AC3: Navigation Structure (Active Chat ↔ Messages) & Relative Time Formatting
- **Экран Active Chat**:
  - Кнопка перехода к списку диалогов «Messages» (`ChevronLeft` / иконка сообщений с лейблом).
  - Аватар + заголовок бота + подзаголовок.
  - Кнопка быстрого старта новой беседы `+` (New conversation).
  - Кнопки свернуть/закрыть.
- **Экран Messages**:
  - Заголовок "Messages" / "Сообщения".
  - Список сессий в виде карточек: заголовок/сниппет, относительное время ("Just now", "Xm ago", "Xh ago", "Yesterday", либо дата "MMM D"), бейдж "Active" для текущей сессии, количество сообщений.
  - Кнопка "+ New conversation" (крупная, заметная).
  - Empty state при отсутствии предыдущих сессий.
- **Поведение переключения**:
  - Клик по сессии: загрузка истории этой сессии и возврат в Active Chat без перезагрузки страницы.
  - Клик "+ New conversation": сброс активной сессии, очистка экрана сообщений, переход в Active Chat.

### AC4: Обратная совместимость (Backward Compatibility)
- Существующие embed-сниппеты на сайтах клиентов продолжают работать без каких-либо изменений на стороне клиентского HTML — вся логика `visitor_id`/заголовков инкапсулирована внутри iframe-виджета.
- Regression-тест: запрос **без** заголовка `X-Visitor-Id` к `POST /api/v1/chatbots/<dialog_id>/completions` (как stream, так и non-stream) не возвращает `400` / `101` и успешно отдаёт ответ бота. Жёсткая валидация `X-Visitor-Id` применяется строго к новому эндпоинту списка сессий `GET /sessions`.

### AC5: Polished Transitions & Animations (Intercom-style)
- Плавная смена экранов между Active Chat и Messages: двухпанельный горизонтальный слайдер (`200%` ширина, `250ms cubic-bezier(0.16, 1, 0.3, 1)`, сдвиг `translateX(0%)` $\leftrightarrow$ `translateX(-50%)`).
- Кросс-фейд шапки (`200ms ease-out`).
- Микро-интеракции на карточках сессий (`active:scale-[0.98] transition-all duration-150 ease-out`) и кнопках (`active:scale-95`).
- Zero Layout Shift (CLS = 0) и отсутствие мерцания высоты: виджет зафиксирован на `380px` $\times$ `500px`, обе панели постоянно смонтированы в DOM, неактивная изолирована через `pointer-events-none`.
- Визуальное подтверждение: записанный видео- и GIF-превью через Playwright (`preview_chat_transitions.gif`, `preview_chat_transitions.webm`).
