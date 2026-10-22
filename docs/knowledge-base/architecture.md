# Архитектура платформы Swipies (Architecture Specification)

> **Статус документа:** Актуален  
> **Дата последней проверки:** 2026-10-15  
> **Первоисточники:** [`SWIPIES_ARCHITECTURE.md`](../../SWIPIES_ARCHITECTURE.md), [`specs/003-crm-v1-integration/spec.md`](../../specs/003-crm-v1-integration/spec.md), [`api/ragflow_server.py`](../../api/ragflow_server.py)

---

## 1. Системная архитектура (System Topology)

Платформа Swipies построена на принципах микросервисной и модульной архитектуры, разделенной на пять функциональных уровней:

```mermaid
flowchart TD
    subgraph Presentation_Tier ["1. Уровень представления (Presentation Layer)"]
        WebUI["Web UI (React 18 / TypeScript / Vite / Tailwind)"]
        ExternalWidgets["Встраиваемые чат-виджеты (Embed SDK)"]
        API_Consumers["Внешние REST / SSE клиенты"]
    end

    subgraph Gateway_Tier ["2. Уровень шлюза и API (API & Gateway Layer)"]
        Nginx["Nginx Reverse Proxy & SSL Termination"]
        QuartServer["Async API Server (Quart / Python 3.13)"]
        AuthMiddleware["Auth & RBAC Middleware (JWT / API Token)"]
        TenantContext["Tenant Context Scoper (tenant_id)"]
    end

    subgraph Intelligence_Tier ["3. Уровень интеллекта и RAG (Intelligence & Agent Layer)"]
        CanvasEngine["Agent Canvas Directed Graph Runtime"]
        HybridRetriever["Hybrid Search Engine (Dense Vector + BM25)"]
        DeepDoc["DeepDoc Vision Parser & OCR Engine"]
        Reranker["Cross-Encoder Reranker"]
        LLMGateway["Centralized LLM Gateway & Policy Engine"]
    end

    subgraph Worker_Tier ["4. Фоновые распределенные воркеры (Background Processing)"]
        TaskExecutor["Doc Parsing & Embedding Workers (rag/svr/task_executor.py)"]
        SyncWorker["Data Source Sync Worker (rag/svr/sync_data_source.py)"]
        CRMOutboxWorker["CRM Outbox Supervisor (rag/svr/crm_outbox_worker.py)"]
    end

    subgraph Persistence_Tier ["5. Хранилища данных (Polyglot Persistence Layer)"]
        RelationalDB[("MySQL / MariaDB<br/>Метаданные, пользователи, CRM, Ads")]
        VectorDB[("Elasticsearch / Infinity<br/>Векторы и BM25 индекс")]
        RedisStore[("Redis<br/>Кэш, очереди, Distributed Locks")]
        ObjectStore[("MinIO / S3<br/>Исходные файлы и чанки документов")]
    end

    WebUI --> Nginx
    ExternalWidgets --> Nginx
    API_Consumers --> Nginx
    Nginx --> QuartServer
    QuartServer --> AuthMiddleware --> TenantContext
    TenantContext --> CanvasEngine
    TenantContext --> HybridRetriever
    TenantContext --> LLMGateway
    CanvasEngine --> Worker_Tier
    HybridRetriever --> VectorDB
    DeepDoc --> ObjectStore
    Worker_Tier --> RelationalDB
    Worker_Tier --> RedisStore
    Worker_Tier --> VectorDB
    Worker_Tier --> ObjectStore
```

---

## 2. Подсистемы и их взаимодействие

### 2.1. Ядро RAG (DeepDoc + Retrieval)
1. **Загрузка и парсинг:** Документ загружается в MinIO/S3, создаётся задача в очереди Redis.
2. **Экзекутор (`rag/svr/task_executor.py`):** Забирает задачу, пропускает через OCR/Layout анализатор DeepDoc, нарезает на чанки по правилам выбранного парсера.
3. **Эмбеддинг и индексация:** Текст чанка отправляется в embedding-модель, dense-вектор и текст сохраняются в Infinity или Elasticsearch.
4. **Поиск (Query Phase):** Запрос пользователя обогащается через эмбеддинг, выполняется параллельный dense + sparse поиск, результаты объединяются через RRF (Reciprocal Rank Fusion) и переранжируются через Cross-Encoder.

### 2.2. Агентский рантайм (Agent Canvas)
- Описан в [`agent/canvas.py`](../../agent/canvas.py) и [`agent/component/`](../../agent/component/).
- Граф исполнения состоит из узлов:
  - `Begin`: точка входа (чат, вебхук, триггер).
  - `Agent` / `AgentWithTools` ([`agent/component/agent_with_tools.py`](../../agent/component/agent_with_tools.py)): LLM с привязанными инструментами function calling.
  - `Retrieval`: выборка из конкретных баз знаний.
  - `Switch`, `Loop`, `Iteration`: управляющие конструкции.
  - `Message`: форматирование ответа пользователю со ссылками на первоисточники.

---

## 3. Потоки данных CRM: Live-запрос и Outbox-запись

Для сценария работы с клиентом разработана двухконтурная схема: **синхронная проверка остатков** и **асинхронная гарантированная запись сделки через Outbox**.

```mermaid
sequenceDiagram
    autonumber
    actor User as Клиент в чате
    participant Agent as Agent Canvas (LLM)
    participant StockTool as Tool: check_stock
    participant OneC as 1C:Enterprise (OData)
    participant LeadTool as Tool: create_incoming_lead
    participant DB as MySQL (CRMOutboxLead)
    participant Worker as CRM Outbox Worker
    participant Amo as amoCRM / Bitrix24 API

    User->>Agent: "Есть ли товар X и запишите меня, Иван +79991234567"
    Note over Agent: Шаг 1: Проверка остатков в реальном времени
    Agent->>StockTool: check_stock(sku="X")
    StockTool->>OneC: HTTPS GET /odata/standard.odata/AccumulationRegister_Остатки
    OneC-->>StockTool: JSON {Balance: 14 шт}
    StockTool-->>Agent: "Товар X в наличии: 14 шт."

    Note over Agent: Шаг 2: Создание лида (Least Privilege)
    Agent->>LeadTool: create_incoming_lead(name="Иван", phone="+79991234567")
    LeadTool->>DB: INSERT CRMOutboxLead (status="pending", idempotency_key=sha256(...))
    DB-->>LeadTool: outbox_id (201 Created)
    LeadTool-->>Agent: "Заявка #123 принята в обработку"
    Agent-->>User: "Товар в наличии (14 шт). Заявка принята, менеджер свяжется с вами!"

    Note over Worker: Шаг 3: Асинхронная доставка сделки воркером
    loop Каждые 2 секунды
        Worker->>DB: SELECT FOR UPDATE с арендой (lease_until)
        Worker->>Amo: POST /api/v4/leads (с авторотацией токена)
        Amo-->>Worker: 201 Created (lead_id=777888)
        Worker->>DB: UPDATE CRMOutboxLead (status="delivered", remote_lead_id="777888")
    end
```

---

## 4. Криптографическая модель коннекторов

Учётные данные внешних систем (Data Sources, CRM-коннекторы, токены AI-моделей) защищены криптографическим контуром:

```mermaid
flowchart LR
    subgraph Input ["Входные данные"]
        SecretKey["RAGFLOW_SECRET_KEY (>32 символов)"]
        RotationKeys["RAGFLOW_SECRET_KEYS_ROTATION"]
        PlainCreds["Прямой токен / пароль"]
    end

    subgraph Derivation ["Деривация ключей"]
        HKDF["RFC 5869 HKDF-SHA256<br/>info='ragflow-connector-credentials-v2'"]
    end

    subgraph Encryption ["Шифрование AES-256-GCM"]
        IV["12-байтный криптостойкий IV"]
        GCM["AES-256-GCM Encrypt"]
        Tag["16-байтный Auth Tag"]
    end

    subgraph Output ["Хранение и выдача"]
        Ciphertext["enc:v2:base64(iv + ciphertext + tag)"]
        MaskedOutput["HTTP Response: ********"]
    end

    SecretKey --> HKDF
    HKDF --> GCM
    PlainCreds --> GCM
    IV --> GCM
    GCM --> Tag
    GCM --> Ciphertext
    Ciphertext --> MaskedOutput
```

* **Чтение устаревших данных (`enc:v1:`):** Поддерживается дешифрование легаси-полезных нагрузок через fallback HMAC/CTR.
* **Дефолтные ключи ротации:** Если ключ указан в `RAGFLOW_SECRET_KEYS_ROTATION`, он принимается **исключительно на чтение (decrypt-only)**. Попытка зашифровать новые данные дефолтным ключом жестко блокируется (fail-closed).
