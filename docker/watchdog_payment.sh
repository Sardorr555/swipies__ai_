#!/bin/bash
# ==============================================================================
#  Swipies: Automated Indestructible Watchdog for Atmos Payment Gateway (Port 3001)
# ==============================================================================

LOG_FILE="/var/log/atmos-watchdog.log"
SERVER_DIR="/home/ubuntu/swipies__ai_/atmos payment system/server"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE" 2>&1
}

# 1. Check if payment server is healthy on port 3001
if curl -s -f --connect-timeout 4 http://127.0.0.1:3001/api/health >/dev/null 2>&1; then
  exit 0
fi

log "⚠️ Atmos Payment Gateway is DOWN or unresponsive on port 3001. Initiating auto-recovery..."

# 2. Kill any hung or zombie processes on port 3001
sudo fuser -k 3001/tcp >> "$LOG_FILE" 2>&1 || true

# 3. Attempt restart via systemd service first (preferred, robust)
if sudo systemctl is-enabled atmos-payment >/dev/null 2>&1 || [ -f "/etc/systemd/system/atmos-payment.service" ]; then
  log "🔄 Restarting via systemctl restart atmos-payment..."
  sudo systemctl daemon-reload >> "$LOG_FILE" 2>&1 || true
  sudo systemctl restart atmos-payment >> "$LOG_FILE" 2>&1
  sleep 3
fi

# 4. Fallback: if still not responding and PM2 is available
if ! curl -s -f --connect-timeout 3 http://127.0.0.1:3001/api/health >/dev/null 2>&1; then
  export NVM_DIR="$HOME/.nvm"
  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
  export PATH="$PATH:$HOME/.npm-global/bin:$HOME/.config/yarn/global/node_modules/.bin:/usr/local/bin:$PATH"

  if command -v pm2 >/dev/null 2>&1; then
    log "🔄 Restarting via PM2..."
    cd "$SERVER_DIR" || cd "/home/ubuntu/swipies__ai_/atmos payment system/server"
    pm2 restart atmos-payment >> "$LOG_FILE" 2>&1 || pm2 start ecosystem.config.cjs >> "$LOG_FILE" 2>&1
    sleep 3
  fi
fi

# 5. Final Fallback: Direct Node.js process if both systemd and PM2 failed
if ! curl -s -f --connect-timeout 3 http://127.0.0.1:3001/api/health >/dev/null 2>&1; then
  log "⚡ Fallback: Starting index.js directly with nohup..."
  cd "$SERVER_DIR" || cd "/home/ubuntu/swipies__ai_/atmos payment system/server"
  nohup node index.js >> atmos.log 2>&1 &
  sleep 3
fi

# 6. Verify recovery
if curl -s -f --connect-timeout 4 http://127.0.0.1:3001/api/health >/dev/null 2>&1; then
  log "✅ Atmos Payment Gateway successfully RESTORED and responding on port 3001!"
else
  log "❌ CRITICAL: Atmos Payment Gateway could not be revived on port 3001. Check logs in $SERVER_DIR/atmos.log."
fi
