#!/usr/bin/env bash
#
# setup_demo_nginx.sh
# Configures host Nginx reverse proxy and SSL for:
#   - demo.swipies.app -> http://127.0.0.1:9222
#   - ads.swipies.app  -> http://127.0.0.1:9222
#

set -e

echo "=================================================="
echo "🌐 Configuring Nginx host for demo.swipies.app and ads.swipies.app"
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

# Clean up duplicate / conflicting configurations
rm -f /etc/nginx/conf.d/demo.swipies.app.conf /etc/nginx/conf.d/demo.swipies.app.conf* /etc/nginx/conf.d/ads.swipies.app.conf 2>/dev/null || true

# Target config in sites-available / sites-enabled
mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled
TARGET_CONF="/etc/nginx/sites-available/demo_and_ads.conf"
ENABLED_CONF="/etc/nginx/sites-enabled/demo_and_ads.conf"

# Remove old single-domain symlinks if they exist
rm -f /etc/nginx/sites-enabled/demo.swipies.app 2>/dev/null || true

# 2. Determine SSL certificate paths for each domain
DEMO_CERT=""
DEMO_KEY=""
if [ -f /etc/letsencrypt/live/demo.swipies.app/fullchain.pem ] && [ -f /etc/letsencrypt/live/demo.swipies.app/privkey.pem ]; then
  echo "🔒 Found dedicated certificate for demo.swipies.app"
  DEMO_CERT="/etc/letsencrypt/live/demo.swipies.app/fullchain.pem"
  DEMO_KEY="/etc/letsencrypt/live/demo.swipies.app/privkey.pem"
elif [ -f /etc/letsencrypt/live/swipies.app/fullchain.pem ] && [ -f /etc/letsencrypt/live/swipies.app/privkey.pem ]; then
  echo "🔒 Found swipies.app certificate for demo.swipies.app"
  DEMO_CERT="/etc/letsencrypt/live/swipies.app/fullchain.pem"
  DEMO_KEY="/etc/letsencrypt/live/swipies.app/privkey.pem"
fi

ADS_CERT=""
ADS_KEY=""
if [ -f /etc/letsencrypt/live/ads.swipies.app/fullchain.pem ] && [ -f /etc/letsencrypt/live/ads.swipies.app/privkey.pem ]; then
  echo "🔒 Found dedicated certificate for ads.swipies.app"
  ADS_CERT="/etc/letsencrypt/live/ads.swipies.app/fullchain.pem"
  ADS_KEY="/etc/letsencrypt/live/ads.swipies.app/privkey.pem"
elif [ -f /etc/letsencrypt/live/swipies.app/fullchain.pem ] && [ -f /etc/letsencrypt/live/swipies.app/privkey.pem ]; then
  echo "🔒 Found swipies.app certificate for ads.swipies.app"
  ADS_CERT="/etc/letsencrypt/live/swipies.app/fullchain.pem"
  ADS_KEY="/etc/letsencrypt/live/swipies.app/privkey.pem"
fi

# 3. Generate Nginx configuration
cat << 'EOF' > "$TARGET_CONF"
# ================================================================
# HTTP Server Blocks (Port 80)
# ================================================================

server {
    listen 80;
    listen [::]:80;
    server_name demo.swipies.app;

    client_max_body_size 128M;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
        try_files $uri =404;
    }

    location / {
        proxy_pass         http://127.0.0.1:9222;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;

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

server {
    listen 80;
    listen [::]:80;
    server_name ads.swipies.app;

    client_max_body_size 128M;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
        try_files $uri =404;
    }

    location / {
        proxy_pass         http://127.0.0.1:9222;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;

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

# Append HTTPS for demo.swipies.app if cert exists
if [ -n "$DEMO_CERT" ] && [ -n "$DEMO_KEY" ]; then
  cat << EOF >> "$TARGET_CONF"

# ================================================================
# HTTPS Server Block for demo.swipies.app (Port 443)
# ================================================================
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name demo.swipies.app;

    ssl_certificate     $DEMO_CERT;
    ssl_certificate_key $DEMO_KEY;
    ssl_session_timeout 1d;
    ssl_session_cache   shared:SSL_DEMO:10m;
    ssl_protocols       TLSv1.2 TLSv1.3;

    client_max_body_size 128M;

    location / {
        proxy_pass         http://127.0.0.1:9222;
        proxy_http_version 1.1;
        proxy_set_header   Host \$host;
        proxy_set_header   X-Real-IP \$remote_addr;
        proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;

        proxy_set_header   Upgrade \$http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;

        if (\$request_method = 'OPTIONS') {
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

# Append HTTPS for ads.swipies.app if cert exists
if [ -n "$ADS_CERT" ] && [ -n "$ADS_KEY" ]; then
  cat << EOF >> "$TARGET_CONF"

# ================================================================
# HTTPS Server Block for ads.swipies.app (Port 443)
# ================================================================
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name ads.swipies.app;

    ssl_certificate     $ADS_CERT;
    ssl_certificate_key $ADS_KEY;
    ssl_session_timeout 1d;
    ssl_session_cache   shared:SSL_ADS:10m;
    ssl_protocols       TLSv1.2 TLSv1.3;

    client_max_body_size 128M;

    location / {
        proxy_pass         http://127.0.0.1:9222;
        proxy_http_version 1.1;
        proxy_set_header   Host \$host;
        proxy_set_header   X-Real-IP \$remote_addr;
        proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;

        proxy_set_header   Upgrade \$http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;

        if (\$request_method = 'OPTIONS') {
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

# Enable in sites-enabled
ln -sf "$TARGET_CONF" "$ENABLED_CONF"

# If host uses conf.d exclusively, copy there too
if grep -q "conf.d/\*\.conf" /etc/nginx/nginx.conf 2>/dev/null && ! grep -q "sites-enabled" /etc/nginx/nginx.conf 2>/dev/null; then
  cp -f "$TARGET_CONF" /etc/nginx/conf.d/demo_and_ads.conf
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

echo "=================================================="
echo "🎉 Configuration completed for demo.swipies.app and ads.swipies.app!"
echo "   Access: http://demo.swipies.app -> http://127.0.0.1:9222"
echo "   Access: http://ads.swipies.app -> http://127.0.0.1:9222"
if [ -n "$DEMO_CERT" ]; then
  echo "   Access (HTTPS): https://demo.swipies.app"
fi
if [ -n "$ADS_CERT" ]; then
  echo "   Access (HTTPS): https://ads.swipies.app"
fi
echo "=================================================="
