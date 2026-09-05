#!/usr/bin/env bash
# Ensure Swipies Docker Compose Stack is armed with systemd auto-start and cron watchdog

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="/home/ubuntu/swipies__ai_/docker"

echo "⚙️ Setting up Swipies Stack systemd service..."

cat << 'EOF' | sudo tee /etc/systemd/system/swipies-stack.service > /dev/null
[Unit]
Description=Swipies AI Docker Compose Stack
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/swipies__ai_/docker
ExecStart=/usr/bin/docker compose -f docker-compose.yml --profile cpu --profile elasticsearch up -d --remove-orphans
ExecStop=/usr/bin/docker compose -f docker-compose.yml --profile cpu --profile elasticsearch stop
TimeoutStartSec=600

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable swipies-stack.service

echo "⚙️ Setting up Swipies Stack cron watchdog..."

cat << 'EOF' | sudo tee /home/ubuntu/swipies__ai_/docker/watchdog_stack.sh > /dev/null
#!/usr/bin/env bash
# Swipies Docker Stack Self-Healing Watchdog
# Runs every 2 minutes via cron

if ! sudo docker ps --format '{{.Names}} {{.Status}}' | grep -q "swipies-cpu Up"; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [STACK WATCHDOG] swipies-cpu is down or restarting. Re-starting stack..." >> /var/log/swipies-stack-watchdog.log
    cd /home/ubuntu/swipies__ai_/docker
    sudo docker compose -f docker-compose.yml --profile cpu --profile elasticsearch up -d --remove-orphans >> /var/log/swipies-stack-watchdog.log 2>&1
fi
EOF

sudo chmod +x /home/ubuntu/swipies__ai_/docker/watchdog_stack.sh

cat << 'EOF' | sudo tee /etc/cron.d/swipies-stack-watchdog > /dev/null
*/2 * * * * root /bin/bash /home/ubuntu/swipies__ai_/docker/watchdog_stack.sh
EOF

sudo chmod 0644 /etc/cron.d/swipies-stack-watchdog

echo "✅ Swipies Stack Auto-Restart & Watchdog are armed and persistent across reboots!"
