#!/bin/bash

# Diagnostic script for Swipies platform server deployment
# Run this on your server using: bash diagnose_server.sh

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}   Swipies Platform Server Diagnostics Tool      ${NC}"
echo -e "${BLUE}==================================================${NC}"

# 1. Check if Nginx is installed and running on the host
echo -e "\n${BLUE}[1/5] Checking host Nginx status...${NC}"
if command -v nginx >/dev/null 2>&1; then
    nginx_status=$(systemctl is-active nginx)
    if [ "$nginx_status" = "active" ]; then
        echo -e "${GREEN}✔ Nginx is running on the host.${NC}"
    else
        echo -e "${RED}✘ Nginx is installed but NOT running (Status: $nginx_status).${NC}"
        echo -e "${YELLOW}👉 Try starting it: sudo systemctl start nginx${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Nginx is not installed on the host. (This is fine if you are terminating SSL elsewhere).${NC}"
fi

# 2. Check Nginx configuration syntax (if installed)
if command -v nginx >/dev/null 2>&1; then
    echo -e "\n${BLUE}[2/5] Testing Nginx configuration...${NC}"
    if sudo nginx -t >/dev/null 2>&1; then
        echo -e "${GREEN}✔ Nginx configuration syntax is OK.${NC}"
    else
        echo -e "${RED}✘ Nginx configuration has errors!${NC}"
        echo -e "${YELLOW}👉 Run 'sudo nginx -t' to see the exact error details.${NC}"
    fi
fi

# 3. Check Docker and RAGFlow containers
echo -e "\n${BLUE}[3/5] Checking Docker containers...${NC}"
if command -v docker >/dev/null 2>&1; then
    containers=$(docker ps --format "{{.Names}} - {{.Status}} - {{.Ports}}")
    if [ -n "$containers" ]; then
        echo -e "${GREEN}✔ Running containers:${NC}"
        echo "$containers"
        
        # Check if frontend container is running
        if echo "$containers" | grep -q "ragflow-frontend"; then
            echo -e "${GREEN}✔ ragflow-frontend container is running.${NC}"
        else
            echo -e "${RED}✘ ragflow-frontend container is NOT running!${NC}"
            echo -e "${YELLOW}👉 Run 'docker compose logs frontend' to see why it failed to start.${NC}"
        fi
        
        # Check if backend container is running
        if echo "$containers" | grep -q -E "ragflow-cpu|ragflow-gpu"; then
            echo -e "${GREEN}✔ RAGFlow backend container is running.${NC}"
        else
            echo -e "${RED}✘ RAGFlow backend container is NOT running!${NC}"
            echo -e "${YELLOW}👉 Run 'docker compose logs ragflow' to see why it failed to start.${NC}"
        fi
    else
        echo -e "${RED}✘ No Docker containers are running!${NC}"
        echo -e "${YELLOW}👉 Run 'docker compose up -d' to start the platform.${NC}"
    fi
else
    echo -e "${RED}✘ Docker is not installed or current user has no permissions to run docker.${NC}"
fi

# 4. Check port bindings on the host
echo -e "\n${BLUE}[4/5] Checking listening ports on host...${NC}"
ports_info=$(sudo ss -tulpn | grep -E '(:80|:443|:9222|:9380)')
if [ -n "$ports_info" ]; then
    echo -e "${GREEN}✔ Port bindings found:${NC}"
    echo "$ports_info"
else
    echo -e "${RED}✘ No active processes are listening on ports 80, 443, 9222, or 9380!${NC}"
fi

# 5. Check firewall / local connection
echo -e "\n${BLUE}[5/5] Checking local connectivity to frontend...${NC}"
local_conn=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9222 --connect-timeout 3)
if [ "$local_conn" = "200" ] || [ "$local_conn" = "301" ] || [ "$local_conn" = "302" ]; then
    echo -e "${GREEN}✔ Successfully connected to frontend container locally on port 9222 (HTTP Code: $local_conn).${NC}"
else
    echo -e "${RED}✘ Failed to connect to frontend container locally on port 9222 (HTTP Code/Status: $local_conn).${NC}"
    echo -e "${YELLOW}👉 Check if the frontend container Nginx is listening properly inside the container.${NC}"
fi

echo -e "\n${BLUE}==================================================${NC}"
echo -e "${BLUE}                 End of Report                    ${NC}"
echo -e "${BLUE}==================================================${NC}"
