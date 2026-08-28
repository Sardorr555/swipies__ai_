#!/usr/bin/env bash
set -e

echo "=================================================="
echo "🚀 Swipies AI 1-Command Automatic Installer"
echo "=================================================="

# 1. Install prerequisite utilities
echo "📦 Installing prerequisites..."
sudo apt-get update -y
sudo apt-get install -y curl git ca-certificates lsb-release

# 2. Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER || true
fi

# 3. Install Docker Compose if not present
if ! docker compose version &> /dev/null; then
    echo "⚙️ Installing Docker Compose..."
    sudo apt-get install -y docker-compose-plugin
fi

# 4. Check if local repository exists on server
if [ -d "$HOME/swipies__ai_/docker" ]; then
    echo "⚙️ Found local Swipies repository at ~/swipies__ai_! Launching local stack..."
    cd "$HOME/swipies__ai_"
    git fetch origin licence_v || true
    git reset --hard origin/licence_v || true
    cd docker
    sudo docker rm -f $(sudo docker ps -a -q --filter name=swipies-) 2>/dev/null || true
    sudo docker compose build
    sudo docker compose up -d --remove-orphans
    sleep 10
    sudo docker exec -i swipies-mysql mysql -uroot -p0czavZsPcYfroExMAdb -D rag_flow -e "UPDATE user SET is_superuser = 1;" 2>/dev/null || true
    SERVER_IP=$(curl -s ifconfig.me || echo "localhost")
    echo "=================================================="
    echo "✅ Swipies AI successfully installed and running!"
    echo "🌐 Access your app at: http://${SERVER_IP}/"
    echo "=================================================="
    exit 0
fi

# 5. Remote installation directory for clean client servers
INSTALL_DIR="$HOME/swipies_app"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

echo "📥 Generating Swipies release configurations..."

# Create .env
cat << 'EOF' > .env
DOC_ENGINE=elasticsearch
DEVICE=cpu
COMPOSE_PROFILES=elasticsearch,cpu
STACK_VERSION=8.11.3
ES_HOST=es01
ES_PORT=1200
ELASTIC_PASSWORD=0czavZsPcYfroExMAdb
MEM_LIMIT=8073741824
MYSQL_PASSWORD=0czavZsPcYfroExMAdb
MYSQL_PORT=3306
MYSQL_DBNAME=rag_flow
REDIS_PASSWORD=0czavZsPcYfroExMAdb
REDIS_PORT=6379
MINIO_USER=ragflow
MINIO_PASSWORD=0czavZsPcYfroExMAdb
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001
SVR_HTTP_PORT=9380
ADMIN_SVR_HTTP_PORT=9381
SVR_MCP_PORT=9382
RAGFLOW_IMAGE=ghcr.io/sardorr555/swipies-backend:licence_v
FRONTEND_IMAGE=ghcr.io/sardorr555/swipies-frontend:licence_v
EOF

# Create docker-compose.yml
cat << 'EOF' > docker-compose.yml
services:
  es01:
    container_name: swipies-es01
    image: elasticsearch:8.11.3
    volumes:
      - esdata01:/usr/share/elasticsearch/data
    tmpfs:
      - /tmp:mode=1777,size=512m
    ports:
      - 127.0.0.1:1200:9200
    env_file: .env
    environment:
      - node.name=es01
      - ELASTIC_PASSWORD=0czavZsPcYfroExMAdb
      - bootstrap.memory_lock=false
      - discovery.type=single-node
      - xpack.security.enabled=true
      - xpack.security.http.ssl.enabled=false
      - xpack.security.transport.ssl.enabled=false
      - cluster.routing.allocation.disk.watermark.low=5gb
      - cluster.routing.allocation.disk.watermark.high=3gb
      - cluster.routing.allocation.disk.watermark.flood_stage=2gb
    mem_limit: 8073741824
    healthcheck:
      test: ["CMD-SHELL", "curl http://localhost:9200"]
      interval: 10s
      timeout: 10s
      retries: 120
    networks:
      - ragflow
    restart: unless-stopped

  mysql:
    container_name: swipies-mysql
    image: mysql:8.0.39
    environment:
      - MYSQL_ROOT_PASSWORD=0czavZsPcYfroExMAdb
      - MYSQL_DATABASE=rag_flow
    command:
      - --max_connections=1000
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_general_ci
      - --default-authentication-plugin=mysql_native_password
      - --tls-version=TLSv1.2,TLSv1.3
    ports:
      - 127.0.0.1:3306:3306
    volumes:
      - mysql_data:/var/lib/mysql
    networks:
      - ragflow
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-u", "root", "-p0czavZsPcYfroExMAdb"]
      interval: 10s
      timeout: 10s
      retries: 120
    restart: unless-stopped

  minio:
    container_name: swipies-minio
    image: minio/minio:RELEASE.2023-12-23T07-19-11Z
    command: minio server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=ragflow
      - MINIO_ROOT_PASSWORD=0czavZsPcYfroExMAdb
    ports:
      - 127.0.0.1:9000:9000
      - 127.0.0.1:9001:9001
    volumes:
      - minio_data:/data
    networks:
      - ragflow
    restart: unless-stopped

  redis:
    container_name: swipies-redis
    image: redis:7.2.4
    command: redis-server --requirepass 0czavZsPcYfroExMAdb --maxmemory 128mb --maxmemory-policy allkeys-lru
    ports:
      - 127.0.0.1:6379:6379
    volumes:
      - redis_data:/data
    networks:
      - ragflow
    restart: unless-stopped

  ragflow-cpu:
    container_name: swipies-cpu
    depends_on:
      mysql:
        condition: service_healthy
    image: ghcr.io/sardorr555/swipies-backend:licence_v
    command:
      - --enable-adminserver
      - --init-model-provider-tables
    ports:
      - 0.0.0.0:9380:9380
      - 0.0.0.0:9381:9381
      - 0.0.0.0:5678:5678
      - 0.0.0.0:5679:5679
      - 0.0.0.0:9382:9382
    volumes:
      - ./ragflow-logs:/ragflow/logs
    env_file: .env
    networks:
      - ragflow
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"

  frontend:
    container_name: swipies-frontend
    image: ghcr.io/sardorr555/swipies-frontend:licence_v
    environment:
      - RAGFLOW_BACKEND=http://swipies-cpu:9380
      - RAGFLOW_ADMIN_BACKEND=http://swipies-cpu:9381
      - NGINX_ENVSUBST_FILTER=RAGFLOW_BACKEND|RAGFLOW_ADMIN_BACKEND
    ports:
      - "0.0.0.0:80:80"
    networks:
      - ragflow
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"

volumes:
  esdata01:
    driver: local
  mysql_data:
    driver: local
  minio_data:
    driver: local
  redis_data:
    driver: local

networks:
  ragflow:
    driver: bridge
EOF

# 6. Pull prebuilt docker images
echo "🚚 Pulling prebuilt Swipies Docker containers..."
sudo docker rm -f $(sudo docker ps -a -q --filter name=swipies-) 2>/dev/null || true
if ! sudo docker compose pull; then
    echo "❌ Failed to pull docker images from GitHub Container Registry."
    echo "Please verify your internet connection and try running: sudo docker compose pull"
    exit 1
else
    echo "🚀 Starting Swipies AI stack..."
    sudo docker compose up -d
fi

echo "⏳ Waiting 15 seconds for services to initialize..."
sleep 15

# 7. Grant superuser permissions to initial admin accounts
sudo docker exec -i swipies-mysql mysql -uroot -p0czavZsPcYfroExMAdb -D rag_flow -e "UPDATE user SET is_superuser = 1;" 2>/dev/null || true

SERVER_IP=$(curl -s ifconfig.me || echo "localhost")

echo "=================================================="
echo "✅ Swipies AI successfully installed and running!"
echo "🌐 Access your app at: http://${SERVER_IP}/"
echo "=================================================="
