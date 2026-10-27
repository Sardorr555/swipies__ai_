# Руководство по развертыванию и эксплуатации (Deployment & Operations Guide)

**Текущее состояние базы знаний:** актуально на **15 октября 2026 года**  
**Базовая ветка:** `test` (`a9b3e9f28`)  
**Базовый upstream:** `v0.27.2` (`a024bea0c`)

> [!CAUTION]
> **ПРАВИЛО РАЗРАБОТКИ И БЕЗОПАСНОСТИ:**
> В текущей рабочей сессии любые прямые вызовы `git push`, автоматический деплой, применение боевых миграций (`--apply`) и печать секретных ключей **СТРОГО ЗАПРЕЩЕНЫ**. Развертывание в продуктивный контур осуществляется только уполномоченным DevOps-инженером после ручного ревью.

---

## 1. Архитектура и топология развертывания

Платформа Swipies RAGFlow разворачивается в контейнеризированном окружении через Docker Compose либо Kubernetes.

```mermaid
flowchart TD
    Client(["Клиенты / Web Browser / API"]) -->|HTTP 80 / HTTPS 443| Nginx["Nginx Reverse Proxy (docker/nginx)"]
    
    subgraph CoreServices ["Application Layer"]
        Nginx -->|/v1/*, /api/*| APIServer["Python RAGFlow API (port 9380)"]
        Nginx -->|/*| WebStatic["React Frontend (dist / static)"]
        TaskExec["Python Task Executor / OCR / Embedding"]
        OutboxExec["CRM Outbox Worker"]
    end

    subgraph DataLayer ["Data & State Layer"]
        MySQL[("MySQL 8.0 / MariaDB (port 3306)")]
        Redis[("Redis 7.0 (port 6379)")]
        MinIO[("MinIO Object Storage (port 9000/9001)")]
        VectorStore[("Infinity (23817) / Elasticsearch (9200)")]
    end

    APIServer --> MySQL
    APIServer --> Redis
    APIServer --> MinIO
    APIServer --> VectorStore
    
    TaskExec --> MySQL
    TaskExec --> Redis
    TaskExec --> MinIO
    TaskExec --> VectorStore

    OutboxExec --> MySQL
    OutboxExec --> Redis
```

---

## 2. Конфигурационные файлы Docker Compose

В каталоге `docker/` проекта содержатся готовые сценарии оркестрации:
- [docker/docker-compose.yml](../../docker/docker-compose.yml) — основной стек сервисов (API, UI, Nginx, Infinity, MySQL, Redis, MinIO).
- [docker/docker-compose-base.yml](../../docker/docker-compose-base.yml) — минимальный базовый стек инфраструктуры для локальной разработки.
- `docker/docker-compose-gpu.yml` — профиль запуска с поддержкой аппаратного ускорения NVIDIA CUDA для локальных моделей OCR/LLM.
- `docker/docker-compose-cpu.yml` — оптимизированный профиль для работы на стандартных CPU без дискретных видеокарт.

---

## 3. Настройка переменных окружения (Environment Configuration)

Перед запуском контейнеров необходимо скопировать безопасный шаблон конфигурации:
```bash
cp docker/.env.example docker/.env
```

### Критически важные параметры безопасности:
1. `RAGFLOW_SECRET_KEY`:
   - Основной 256-битный мастер-ключ шифрования.
   - **Генерация:** `openssl rand -hex 32` (строго 64 hex-символа или 32 байта).
   - При пустом ключе или попытке использовать дефолтный ключ upstream (`ragflow_single_global...`) запуск сервера будет заблокирован (Fail-Closed).
2. `RAGFLOW_SECRET_KEYS_ROTATION`:
   - Список старых/исторических ключей через запятую для расшифрования ранее сохраненных данных:
   - `RAGFLOW_SECRET_KEYS_ROTATION=<old_key_1>,<old_key_2>`
3. `MYSQL_PASSWORD`:
   - Пароль учетной записи пользователя MySQL базы данных.
4. `MINIO_SECRET_KEY`:
   - Секретный ключ для доступа к MinIO S3-хранилищу.

---

## 4. Порядок ручного развертывания (Production Runbook)

### Шаг 1. Предварительная проверка окружения
- Убедиться, что на целевом сервере установлены `docker` (>= 24.0) и `docker compose` (>= 2.20).
- Проверить наличие свободного места на диске (минимум 30 ГБ под Docker-образы и векторные индексы).
- Проверить доступность необходимых портов: `80`, `443`, `9380` (внутренний), `3306`, `6379`.

### Шаг 2. Запуск инфраструктурного слоя
```bash
cd docker
docker compose up -d mysql redis minio infinity
```
- Дождаться прохождения Healthcheck'ов базы данных:
  ```bash
  docker compose ps
  ```

### Шаг 3. Инициализация и миграции базы данных
- При первичном запуске база данных автоматически инициализируется скриптами `docker/init.sql`.
- Миграции ORM Peewee выполняются при старте API-сервера.

### Шаг 4. Запуск бэкенда и фоновых обработчиков
```bash
docker compose up -d ragflow-server ragflow-task-executor
```

### Шаг 5. Запуск CRM Outbox Worker (Фоновый процесс)
Для включения надежной доставки лидов в CRM запускается отдельный воркер:
```bash
python -m api.crm.tasks.outbox_worker
```
*(В Docker Compose оформляется как отдельный сервис или запускается супервизором внутри основного контейнера).*

---

## 5. Мониторинг, Healthchecks и логи

### Проверка работоспособности сервисов:
- **API Health Endpoint:** `GET http://localhost:9380/v1/api/health` -> `{"code": 0, "status": "ok"}`
- **Логи API:** `docker logs -f ragflow-server`
- **Логи фонового обработчика:** `docker logs -f ragflow-task-executor`
- **Логи Nginx:** `docker logs -f ragflow-nginx`

### Диагностика утечек секретов в логах:
Все логи платформы фильтруются на уровне логгеров. URL вебхуков Bitrix24 и токены авторизации маскируются (`[REDACTED_WEBHOOK]`, `3113...bbd`). Регулярно запускайте аудит логов:
```bash
grep -i "bearer" /var/log/ragflow/*.log
```
*(Вывод не должен содержать открытых токенов).*

---

## 6. Откат изменений (Rollback Procedure)

В случае нештатной ситуации при релизе:
1. Остановить сервисы: `docker compose stop ragflow-server ragflow-task-executor`
2. Переключить образ контейнера на предыдущий стабильный тег в `docker-compose.yml`.
3. Запустить сервисы: `docker compose up -d ragflow-server ragflow-task-executor`
4. Проверить целостность ключей шифрования: если ключи менялись, убедиться, что старый ключ указан в `RAGFLOW_SECRET_KEYS_ROTATION`.

## 2026-10-26 — authorized deployment preparation

The owner explicitly authorized commit, push to `swipies_26`, deployment and live verification. The main workflow now deploys the exact triggering commit, checks for tracked server edits, creates a private MySQL dump and code/image rollback references, builds before restarting only `ragflow-cpu` and `frontend`, and fails on a missing Agent Access manifest. Failures after checkout restore the previous code and (after restart) previous application images. Database dumps are retained privately for manual recovery; database restoration is deliberately not automatic while users may be writing data.

Removed all-container deletion/pruning, Docker daemon reconfiguration, unrelated payment changes, and secret replication from this deployment path. Existing `.env`, storage services, volumes and watchdog configuration are preserved. This script requires an existing running CPU/Elasticsearch installation; it is not an initial server provisioner. Other legacy deployment workflows are outside this release and have not been hardened.

Before push, the last existing main workflow run (`40239196160`, base `697aa5aee`) had already failed with `ssh.ParsePrivateKey: ssh: no key found` and an SSH authentication failure. Local saved SSH keys also did not authenticate to the most recent known host. Access repair and actual server verification remain required; a successful push alone does not establish a deployment.


### 2026-10-27 — SSH access repaired; deployment blocked by tracked edits

The owner replaced the SSH secret and explicitly authorized a manual workflow
dispatch on `swipies_26`. Run `40399935446` authenticated successfully, but the
server checkout contained tracked modifications. The deployment guard stopped
before database backup, checkout, image build or application restart.

The guard now prints staged/unstaged diff statistics and mode summaries so an
operator can identify the affected paths. It does not print file contents or
discard server changes. Inspect and preserve the actual server edits before
retrying deployment; do not use `git reset --hard` or automatic stash/pop to
silence this guard. Workflow success and live API verification remain required.


### Reviewed server configuration retained (2026-10-27)

Direct SSH inspection identified six intended server edits. They are now included
in `swipies_26`: bind application/admin/MCP/debug and frontend published ports to
loopback, remove the obsolete literal IP from four Nginx configurations, and
ensure the CRM worker's existing `phonenumbers` dependency before startup. The
full server patch is retained locally under Windows DPAPI. Before deployment,
the same edits are preserved in a server-local Git commit and a private patch;
the deployment rollback reference can therefore restore the existing settings.
No environment secrets are copied into Git. Deployment and public authenticated
verification must still finish before reporting this release as successful.


The first direct Compose precheck exposed a second deployment issue: the script
selected CPU and Elasticsearch but omitted MySQL's `metadata-mysql` profile,
making `ragflow-cpu` depend on an undefined service. Both the normal deployment
and rollback Compose invocations now explicitly include `metadata-mysql`. The
CPU/Elasticsearch/MySQL topology is intentional for this existing installation.
The two server checkout paths resolve to the same physical repository and the
same environment file; no environment file is replaced or copied into Git.


Run `40403556584` deployed commit `6f6c25ef1`, saved a private MySQL snapshot,
built the frontend, restarted only the two application containers, and passed
local API/frontend checks. The final public probe failed with Cloudflare HTTP
403 because `urllib` used its default User-Agent. The workflow probe now uses
`SwipiesAgent/1.0`, matching the already verified MCP client. HTTPS verification
and manifest/branding assertions remain enabled. A final workflow rerun and
authenticated live checks are required to close this release.


### Successful production deployment (2026-10-27)

GitHub Actions run [40404173859](https://github.com/Sardorr555/swipies__ai_/actions/runs/40404173859)
completed successfully, including the public HTTPS manifest check. SSH confirmed
deployed commit `1bf4ac518` and a clean checkout. The OpenAI-compatible API now
passes nonstream and SSE requests on production. The application verification
logged 111 passing checks after the application release and 12 passing smoke
checks after the final workflow correction; disposable resources were deleted.
The test account remains Pro with 512 credits. Existing server configuration was
preserved, MySQL's Compose profile is explicit for deploy/rollback, and the
public probe uses the verified SwipiesAgent User-Agent. The CRM worker is running;
real external CRM delivery and paid Ads delivery remain unverified. See the
[release report](handoffs/2026-10-27-successful-autodeploy.md).


### Public external AI discovery (2026-10-27)

The public cloud landing now documents external MCP/API control on EN/RU/UZ.
Start at https://swipies.app/llms.txt or the human guide
https://swipies.app/agents.html. Machine discovery and a gateway-only OpenAPI
contract are linked from the homepage; the stdio client is downloadable as
plaintext with save-as instructions. Eight static HTTPS assets are verified.
This release does not change platform runtime or expand its MCP scope. See the
[landing release report](handoffs/2026-10-27-agent-access-landing.md).
