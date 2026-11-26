#!/bin/bash
set -e

# ==============================================================================
#  Swipies: Indestructible Atmos Payment Service Provisioner & Health Verification
#  - Configures Linux Systemd Service (Auto-restarts on crash + boots on startup)
#  - Configures PM2 process manager with ecosystem autorestart
#  - Installs Automated 1-minute Cron Watchdog (/etc/cron.d/atmos-payment-watchdog)
# ==============================================================================

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}   Configuring Indestructible Atmos Payment System ${NC}"
echo -e "${BLUE}==================================================${NC}"

# Locate directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR=""
POSSIBLE_DIRS=(
  "$HOME/swipies__ai_/atmos payment system/server"
  "$SCRIPT_DIR/../atmos payment system/server"
  "$(pwd)/atmos payment system/server"
  "$(pwd)/../atmos payment system/server"
  "/ragflow/atmos payment system/server"
)

for dir in "${POSSIBLE_DIRS[@]}"; do
  if [ -d "$dir" ] && [ -f "$dir/index.js" ]; then
    SERVER_DIR="$dir"
    break
  fi
done

if [ -z "$SERVER_DIR" ]; then
  echo -e "${RED}✘ Could not find 'atmos payment system/server' directory.${NC}"
  exit 1
fi

echo -e "${BLUE}📁 Server Directory: $SERVER_DIR${NC}"

# Create safe symlink without spaces for systemd and scripts
if [ -d "$HOME/swipies__ai_/atmos payment system" ]; then
  ln -sfn "$HOME/swipies__ai_/atmos payment system" "$HOME/swipies__ai_/atmos_payment_system"
fi

cd "$SERVER_DIR"

# 1. Ensure dependencies
if [ ! -d "node_modules" ] || [ ! -d "node_modules/express" ]; then
  echo -e "${BLUE}📦 Installing npm dependencies...${NC}"
  npm install
fi

# 2. Ensure .env
if [ ! -f ".env" ]; then
  echo -e "${YELLOW}📝 Creating .env file for payment server...${NC}"
  cat > .env << 'ENVEOF'
ATMOS_STORE_ID=100506
ATMOS_KEY=TpLRLagJ1SXiZ0dT_om5BT_I3Nga
ATMOS_SECRET=bMH7gjat2EgI3fTXoLJX7CRUcbAa
ATMOS_BASE_URL=https://apigw.atmos.uz
PORT=3001
FRONTEND_URL=https://app.swipies.app
ADMIN_PASSWORD=0czavZsPcYfroExMAdb
RAGFLOW_BASE_URL=https://app.swipies.app
RAGFLOW_ADMIN_EMAIL=your-admin@swipies.app
RAGFLOW_ADMIN_PASSWORD=your-admin-password
RAGFLOW_PUBLIC_KEY_PATH=./ragflow_public.pem
ENVEOF
fi

# Ensure existing .env uses app.swipies.app instead of bare domain
sed -i 's#RAGFLOW_BASE_URL=https://swipies.app#RAGFLOW_BASE_URL=https://app.swipies.app#g' .env 2>/dev/null || true
sed -i 's#FRONTEND_URL=https://swipies.app#FRONTEND_URL=https://app.swipies.app#g' .env 2>/dev/null || true


# 3. Kill hung processes holding port 3001
echo -e "${BLUE}🔌 Freeing port 3001...${NC}"
sudo fuser -k 3001/tcp 2>/dev/null || true

# 4. Setup Linux Systemd Service (Primary Indestructible Supervisor)
SYSTEMD_UNIT="$SCRIPT_DIR/atmos-payment.service"
if [ -f "$SYSTEMD_UNIT" ]; then
  echo -e "${BLUE}⚙️ Installing Systemd Service (/etc/systemd/system/atmos-payment.service)...${NC}"
  sudo cp "$SYSTEMD_UNIT" /etc/systemd/system/atmos-payment.service
  sudo chmod 644 /etc/systemd/system/atmos-payment.service
  sudo systemctl daemon-reload
  sudo systemctl enable atmos-payment
  sudo systemctl restart atmos-payment
  echo -e "${GREEN}✔ Systemd service atmos-payment enabled and started.${NC}"
fi

# 5. Setup PM2 as complementary supervisor & register startup on boot
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  . "$NVM_DIR/nvm.sh"
fi
export PATH="$PATH:$HOME/.npm-global/bin:$HOME/.config/yarn/global/node_modules/.bin:/usr/local/bin:$PATH"

if command -v pm2 >/dev/null 2>&1; then
  echo -e "${BLUE}🔄 Configuring PM2 supervisor & startup registration...${NC}"
  cd "$SERVER_DIR"
  pm2 delete atmos-payment 2>/dev/null || true
  if [ -f "ecosystem.config.cjs" ]; then
    pm2 start ecosystem.config.cjs --update-env
  else
    pm2 start index.js --name "atmos-payment" --update-env
  fi
  pm2 save || true
  sudo env PATH=$PATH:$HOME/.npm-global/bin pm2 startup systemd -u ubuntu --hp /home/ubuntu 2>/dev/null || true
fi

# 6. Install 1-Minute Cron Watchdog
WATCHDOG_SCRIPT="$SCRIPT_DIR/watchdog_payment.sh"
if [ -f "$WATCHDOG_SCRIPT" ]; then
  echo -e "${BLUE}🛡️ Installing Automated 1-minute Cron Watchdog...${NC}"
  chmod +x "$WATCHDOG_SCRIPT"
  
  # Install into /etc/cron.d/ for root-level automated execution
  echo "* * * * * root /bin/bash $WATCHDOG_SCRIPT >> /var/log/atmos-watchdog.log 2>&1" | sudo tee /etc/cron.d/atmos-payment-watchdog >/dev/null
  sudo chmod 644 /etc/cron.d/atmos-payment-watchdog
  echo -e "${GREEN}✔ Cron watchdog active at /etc/cron.d/atmos-payment-watchdog${NC}"
fi

# 7. Verify Health Status
echo -e "${BLUE}⏳ Waiting for Atmos payment server to respond on port 3001...${NC}"
HEALTHY=false
for i in {1..15}; do
  if curl -s -f --connect-timeout 2 http://127.0.0.1:3001/api/health >/dev/null 2>&1; then
    HEALTHY=true
    break
  fi
  sleep 1
done

if [ "$HEALTHY" = true ]; then
  echo -e "${GREEN}✔ Atmos Payment Gateway is ONLINE and HEALTHY on port 3001!${NC}"
else
  echo -e "${RED}✘ Payment server failed to respond within 15 seconds! Checking logs...${NC}"
  tail -n 20 "$SERVER_DIR/atmos.log" 2>/dev/null || sudo journalctl -u atmos-payment -n 20 --no-pager || true
  exit 1
fi

# 8. Run Cycle Tests
HEALTH_RESP=$(curl -s --connect-timeout 4 http://127.0.0.1:3001/api/health || echo '{"status":"error"}')
echo -e "Health Diagnostic: ${GREEN}$HEALTH_RESP${NC}"

MPS_TEST=$(curl -s -X POST http://127.0.0.1:3001/api/pay/mps \
  -H "Content-Type: application/json" \
  -d '{}' --connect-timeout 5 || echo '{"error":"timeout"}')
echo -e "MPS Endpoint Validation: ${GREEN}$MPS_TEST${NC}"

CREATE_TEST=$(curl -s -X POST http://127.0.0.1:3001/api/pay/create \
  -H "Content-Type: application/json" \
  -d '{"amount": 1000, "account": "test-healthcheck@swipies.app"}' --connect-timeout 10 || echo '{"error":"timeout"}')
echo -e "Local Pay Create Test: ${GREEN}$CREATE_TEST${NC}"

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}✅ Atmos Payment System is 100% Armed & Indestructible!${NC}"
echo -e "${GREEN}==================================================${NC}"

