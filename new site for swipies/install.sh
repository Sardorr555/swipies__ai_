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

# 4. Create installation directory
INSTALL_DIR="$HOME/swipies_app"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

echo "📥 Downloading Swipies release configurations..."
curl -fsSL -o docker-compose.yml https://swipies.app/docker-compose.release.yml 2>/dev/null || \
curl -fsSL -o docker-compose.yml https://raw.githubusercontent.com/Sardorr555/swipies__ai_/licence_v/docker/docker-compose.release.yml

curl -fsSL -o docker-compose-base.yml https://swipies.app/docker-compose-base.yml 2>/dev/null || \
curl -fsSL -o docker-compose-base.yml https://raw.githubusercontent.com/Sardorr555/swipies__ai_/licence_v/docker/docker-compose-base.yml

curl -fsSL -o service_conf.yaml.template https://swipies.app/service_conf.yaml.template 2>/dev/null || \
curl -fsSL -o service_conf.yaml.template https://raw.githubusercontent.com/Sardorr555/swipies__ai_/licence_v/docker/service_conf.yaml.template

curl -fsSL -o .env https://swipies.app/.env 2>/dev/null || \
curl -fsSL -o .env https://raw.githubusercontent.com/Sardorr555/swipies__ai_/licence_v/docker/.env

# 5. Pull prebuilt docker images
echo "🚚 Pulling prebuilt Swipies Docker containers..."
sudo docker compose pull || true

# 6. Start Swipies Services
echo "🚀 Starting Swipies AI stack..."
sudo docker compose up -d

echo "⏳ Waiting 15 seconds for services to initialize..."
sleep 15

# 7. Grant superuser permissions to initial admin accounts
sudo docker exec -i swipies-mysql mysql -uroot -p0czavZsPcYfroExMAdb -D rag_flow -e "UPDATE user SET is_superuser = 1;" || true

SERVER_IP=$(curl -s ifconfig.me || echo "localhost")

echo "=================================================="
echo "✅ Swipies AI successfully installed and running!"
echo "🌐 Access your app at: http://${SERVER_IP}/"
echo "=================================================="
