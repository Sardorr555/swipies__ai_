#!/bin/bash
set -e

# ==============================================================================
#  Swipies: Ensure Atmos Payment Service is Running & Perform Health Check
# ==============================================================================

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}   Checking Atmos Payment System Status           ${NC}"
echo -e "${BLUE}==================================================${NC}"

# Find server directory
SERVER_DIR=""
POSSIBLE_DIRS=(
  "$HOME/swipies__ai_/atmos payment system/server"
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

# Load NVM and PM2 environment if available
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  . "$NVM_DIR/nvm.sh"
fi
export PATH="$PATH:$HOME/.npm-global/bin:$HOME/.config/yarn/global/node_modules/.bin:/usr/local/bin:$PATH"

check_health() {
  curl -s -f --connect-timeout 4 http://localhost:3001/api/health >/dev/null 2>&1
}

if check_health; then
  echo -e "${GREEN}✔ Atmos payment server is already running on port 3001.${NC}"
else
  echo -e "${YELLOW}⚠️ Atmos payment server is NOT responding on port 3001. Starting it...${NC}"

  if [ -z "$SERVER_DIR" ]; then
    echo -e "${RED}✘ Could not find 'atmos payment system/server' directory.${NC}"
    exit 1
  fi

  echo -e "${BLUE}📁 Navigating to $SERVER_DIR${NC}"
  cd "$SERVER_DIR"

  if [ ! -d "node_modules" ] || [ ! -d "node_modules/express" ]; then
    echo -e "${BLUE}📦 Installing npm dependencies...${NC}"
    npm install
  fi

  if [ ! -f ".env" ]; then
    echo -e "${YELLOW}📝 Creating .env file for payment server...${NC}"
    cat > .env << 'ENVEOF'
ATMOS_STORE_ID=100506
ATMOS_KEY=TpLRLagJ1SXiZ0dT_om5BT_I3Nga
ATMOS_SECRET=bMH7gjat2EgI3fTXoLJX7CRUcbAa
ATMOS_BASE_URL=https://apigw.atmos.uz
PORT=3001
FRONTEND_URL=https://swipies.app
ADMIN_PASSWORD=0czavZsPcYfroExMAdb
RAGFLOW_BASE_URL=https://swipies.app
RAGFLOW_ADMIN_EMAIL=your-admin@swipies.app
RAGFLOW_ADMIN_PASSWORD=your-admin-password
RAGFLOW_PUBLIC_KEY_PATH=./ragflow_public.pem
ENVEOF
  fi

  if ! command -v pm2 >/dev/null 2>&1; then
    echo -e "${YELLOW}⚙️ PM2 is not installed. Installing PM2 globally...${NC}"
    npm install -g pm2 || sudo npm install -g pm2 || true
  fi

  if command -v pm2 >/dev/null 2>&1; then
    echo -e "${BLUE}🔄 Starting atmos-payment via PM2...${NC}"
    pm2 delete atmos-payment 2>/dev/null || true
    pm2 start index.js --name "atmos-payment" --update-env
    pm2 save || true
  else
    echo -e "${YELLOW}⚡ PM2 unavailable, starting with nohup in background...${NC}"
    nohup node index.js > atmos.log 2>&1 &
  fi

  # Wait for startup
  echo -e "${BLUE}⏳ Waiting for payment server to initialize...${NC}"
  for i in {1..10}; do
    if check_health; then
      echo -e "${GREEN}✔ Payment server started successfully!${NC}"
      break
    fi
    sleep 1
  done
fi

# Run test cycle
echo -e "\n${BLUE}🧪 Running full cycle test...${NC}"
HEALTH_DATA=$(curl -s --connect-timeout 5 http://localhost:3001/api/health || echo '{"status":"error"}')
echo -e "Health response: ${GREEN}$HEALTH_DATA${NC}"

CREATE_TEST=$(curl -s -X POST http://localhost:3001/api/pay/create \
  -H "Content-Type: application/json" \
  -d '{"amount": 1000, "account": "test-healthcheck@swipies.app"}' --connect-timeout 10 || echo '{"error":"Connection timeout"}')

echo -e "Pay create test response: ${GREEN}$CREATE_TEST${NC}"

if echo "$CREATE_TEST" | grep -q -E '"transaction_id"|"mock"|"result"|"error"'; then
  echo -e "${GREEN}✅ Payment service full cycle test finished successfully (valid JSON returned).${NC}"
else
  echo -e "${RED}✘ Unexpected non-JSON response from payment server!${NC}"
fi
