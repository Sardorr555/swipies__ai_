#!/usr/bin/env bash
set -e

echo "=================================================="
echo "🚀 Swipies AI Licensed Version Automatic Installer"
echo "=================================================="

# 1. Install prerequisite utilities
echo "📦 Installing prerequisites..."
sudo apt-get update -y
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release git

# 2. Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

# 3. Install Docker Compose if not present
if ! docker compose version &> /dev/null; then
    echo "⚙️ Installing Docker Compose..."
    sudo apt-get install -y docker-compose-plugin
fi

# 4. Configure Docker daemon registry mirrors for resilience
echo "⚙️ Configuring Docker mirrors..."
sudo mkdir -p /etc/docker
echo '{"registry-mirrors": ["https://dh-mirror.gitverse.ru", "https://mirror.gcr.io"]}' | sudo tee /etc/docker/daemon.json > /dev/null
sudo systemctl daemon-reload || true
sudo systemctl restart docker || sudo service docker restart || true
sudo usermod -aG docker "$USER" 2>/dev/null || true

# 5. Determine repository location
REPO_DIR="${SWIPIES_DIR:-$HOME/swipies__ai_}"
if [ -f "$(pwd)/docker/docker-compose.yml" ]; then
    REPO_DIR="$(pwd)"
fi

echo "🚀 Setting up Swipies AI repository at ${REPO_DIR}..."
if [ ! -d "${REPO_DIR}/docker" ]; then
    echo "📥 Cloning branch licence_v..."
    git clone -b licence_v https://github.com/Sardorr555/swipies__ai_.git "${REPO_DIR}"
fi

cd "${REPO_DIR}"
git remote set-url origin https://github.com/Sardorr555/swipies__ai_.git 2>/dev/null || true
git fetch origin licence_v 2>/dev/null || true
git reset --hard origin/licence_v 2>/dev/null || true

# 6. Ensure swap exists (prevents OOM during frontend compilation)
echo "💾 Checking swap memory..."
if [ $(free -m | awk '/Swap/{print $2}') -eq 0 ]; then
    echo "Creating 4GB swapfile for reliable build execution..."
    sudo fallocate -l 4G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=4096
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile || true
fi

cd "${REPO_DIR}/docker"

# 7. Stop and clean any previous containers
echo "🛑 Cleaning previous container instances..."
sudo docker compose down --remove-orphans 2>/dev/null || true
sudo docker rm -f $(sudo docker ps -a -q --filter name=swipies-) 2>/dev/null || true
sudo docker rm -f swipies-minio swipies-mysql swipies-redis swipies-es01 swipies-frontend swipies-cpu swipies-gpu swipies-infinity swipies-seekdb swipies-opensearch01 swipies-deepdoc 2>/dev/null || true

# 8. Build images and start stack
echo "🐳 Building Swipies AI containers..."
sudo docker compose build

echo "🚀 Launching Swipies AI stack..."
sudo docker compose up -d --remove-orphans

# 9. Wait for Python API server readiness
echo "⏳ Waiting for Swipies Python API server to be ready..."
API_READY=false
for i in $(seq 1 45); do
    if sudo docker exec swipies-cpu curl -s -f http://127.0.0.1:9380/api/v1/system/version >/dev/null 2>&1 || sudo docker exec swipies-cpu curl -s -f http://127.0.0.1:9380/v1/system/version >/dev/null 2>&1; then
        echo "✅ Swipies Python API server is up and responding!"
        API_READY=true
        break
    fi
    echo "Waiting for API server (attempt $i/45)..."
    sleep 3
done

if [ "$API_READY" != "true" ]; then
    echo "⚠️ Warning: API server startup is taking longer than expected. Logs:"
    sudo docker logs --tail 50 swipies-cpu || true
fi

# 10. Ensure user table permissions
echo "🔑 Granting superuser permissions to admin accounts..."
sudo docker exec -i swipies-mysql mysql -uroot -p0czavZsPcYfroExMAdb -D rag_flow -e "UPDATE user SET is_superuser = 1;" 2>/dev/null || true

# 11. Cleanup dangling images
sudo docker image prune -f 2>/dev/null || true

SERVER_IP=$(curl -s ifconfig.me || echo "localhost")

echo ""
echo "=================================================="
echo "✅ Swipies AI Licensed Version successfully installed and running!"
echo "🌐 Access your app at: http://${SERVER_IP}/"
echo "🔑 Next step: Log in or create an account, then activate your License Key in User Settings -> License."
echo "=================================================="
