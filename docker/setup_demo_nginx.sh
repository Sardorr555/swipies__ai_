#!/usr/bin/env bash
#
# setup_demo_nginx.sh
# Configures host Nginx reverse proxy and SSL for demo.swipies.app -> http://127.0.0.1:9222
#

set -e

echo "=================================================="
echo "🌐 Configuring Nginx host for demo.swipies.app"
echo "=================================================="

# 1. Ensure Nginx and Certbot are installed
if ! command -v nginx &>/dev/null; then
  echo "📦 Installing Nginx..."
  apt-get update -y
  apt-get install -y nginx certbot python3-certbot-nginx
fi

# Ensure webroot directory exists for ACME challenges
mkdir -p /var/www/html
chmod -R 755 /var/www/html

TARGET_CONF="/etc/nginx/sites-available/demo.swipies.app"
ENABLED_CONF="/etc/nginx/sites-enabled/demo.swipies.app"

# Fallback for systems using /etc/nginx/conf.d directly
if [ ! -d /etc/nginx/sites-available ]; then
  mkdir -p /etc/nginx/sites-available
fi
if [ ! -d /etc/nginx/sites-enabled ]; then
  mkdir -p /etc/nginx/sites-enabled
fi

# 2. Determine SSL certificate paths
SSL_CERT=""
SSL_KEY=""

if [ -f /etc/letsencrypt/live/demo.swipies.app/fullchain.pem ] && [ -f /etc/letsencrypt/live/demo.swipies.app/privkey.pem ]; then
  echo "🔒 Found dedicated certificate for demo.swipies.app"
  SSL_CERT="/etc/letsencrypt/live/demo.swipies.app/fullchain.pem"
  SSL_KEY="/etc/letsencrypt/live/demo.swipies.app/privkey.pem"
elif [ -f /etc/letsencrypt/live/swipies.app/fullchain.pem ] && [ -f /etc/letsencrypt/live/swipies.app/privkey.pem ]; then
  echo "🔒 Found swipies.app certificate. Checking coverage..."
  SSL_CERT="/etc/letsencrypt/live/swipies.app/fullchain.pem"
  SSL_KEY="/etc/letsencrypt/live/swipies.app/privkey.pem"
fi

# 3. Generate Nginx configuration
cat << 'EOF' > "$TARGET_CONF"
# Configuration for demo.swipies.app
server {
    listen 80;
    listen [::]:80;
    server_name demo.swipies.app;

    client_max_body_size 128M;

    # Let's Encrypt HTTP-01 challenge path
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        try_files $uri =404;
    }

    # Proxy to Swipies Docker frontend container (port 9222)
    location / {
        proxy_pass         http://127.0.0.1:9222;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;

        # CORS preflight
        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin'  '*' always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
            add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization' always;
            add_header 'Content-Type' 'text/plain charset=UTF-8';
            add_header 'Content-Length' 0;
            return 204;
        }
    }
}
EOF

# If SSL certificate is available, append HTTPS block
if [ -n "$SSL_CERT" ] && [ -n "$SSL_KEY" ]; then
  cat << EOF >> "$TARGET_CONF"

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name demo.swipies.app;

    ssl_certificate     $SSL_CERT;
    ssl_certificate_key $SSL_KEY;
    ssl_session_timeout 1d;
    ssl_session_cache   shared:SSL:10m;
    ssl_protocols       TLSv1.2 TLSv1.3;

    client_max_body_size 128M;

    location / {
        proxy_pass         http://127.0.0.1:9222;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;

        # CORS preflight
        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin'  '*' always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
            add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization' always;
            add_header 'Content-Type' 'text/plain charset=UTF-8';
            add_header 'Content-Length' 0;
            return 204;
        }
    }
}
EOF
fi

# Link to sites-enabled
ln -sf "$TARGET_CONF" "$ENABLED_CONF"

# Also sync to /etc/nginx/conf.d/ if the main nginx.conf includes conf.d/*.conf
if grep -q "conf.d/\*\.conf" /etc/nginx/nginx.conf 2>/dev/null; then
  cp -f "$TARGET_CONF" /etc/nginx/conf.d/demo.swipies.app.conf
fi

echo "🔍 Validating Nginx configuration syntax..."
if nginx -t; then
  echo "🔄 Reloading Nginx service..."
  systemctl reload nginx || service nginx reload || true
  echo "✅ Nginx reloaded successfully."
else
  echo "❌ Nginx configuration test failed!"
  exit 1
fi

# 4. Attempt Certbot certificate generation if DNS resolves to this host
echo "🌐 Checking DNS resolution for demo.swipies.app..."
HOST_IP=$(curl -4 -s --connect-timeout 3 ifconfig.me || curl -4 -s --connect-timeout 3 icanhazip.com || echo "51.20.190.248")
RESOLVED_IP=$(getent ahosts demo.swipies.app 2>/dev/null | awk '{print $1}' | head -n 1 || true)

echo "   Host Public IP: $HOST_IP"
echo "   DNS Resolved IP: ${RESOLVED_IP:-Not resolved yet}"

if [ -n "$RESOLVED_IP" ] && [ "$RESOLVED_IP" = "$HOST_IP" ]; then
  echo "🚀 DNS points to this server! Requesting/renewing Let's Encrypt SSL certificate..."
  if certbot --nginx -d demo.swipies.app --non-interactive --agree-tos --register-unsafely-without-email --redirect; then
    echo "🎉 SSL Certificate successfully issued and configured for demo.swipies.app!"
    systemctl reload nginx || true
  else
    echo "⚠️ Certbot challenge encountered an issue, HTTP proxy remains fully active."
  fi
else
  echo "ℹ️ DNS A-record for demo.swipies.app is not yet pointing directly to $HOST_IP (or is propagating)."
  echo "   Once you create the A record (demo.swipies.app -> $HOST_IP), rerun this script or wait for auto-deploy:"
  echo "   sudo bash docker/setup_demo_nginx.sh"
fi

echo "=================================================="
echo "🎉 demo.swipies.app configuration completed!"
echo "   Access: http://demo.swipies.app -> http://127.0.0.1:9222"
if [ -n "$SSL_CERT" ]; then
  echo "   Access (HTTPS): https://demo.swipies.app"
fi
echo "=================================================="
