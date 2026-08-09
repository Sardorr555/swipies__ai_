#!/usr/bin/env python3
"""
setup_nginx.py — Writes the correct Nginx config for swipies.app
  - Serves static files from /var/www/html
  - Proxies /api/* to Flask on port 5005
  - Redirects /admin -> /admin.html
"""

import os
import subprocess

NGINX_CONF = """\
server {
    listen 80;
    listen [::]:80;
    server_name swipies.app www.swipies.app;

    # Redirect HTTP to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name swipies.app www.swipies.app;

    ssl_certificate     /etc/letsencrypt/live/swipies.app/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/swipies.app/privkey.pem;
    include             /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam         /etc/letsencrypt/ssl-dhparams.pem;

    root  /var/www/html;
    index index.html;

    # --- Exact redirect: /admin -> /admin.html ---
    location = /admin {
        return 301 /admin.html;
    }

    # --- Proxy API calls to the Flask backend (port 5005) ---
    location /api/ {
        proxy_pass         http://127.0.0.1:5005;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

        # CORS headers
        add_header 'Access-Control-Allow-Origin'  '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization' always;
        add_header 'Access-Control-Expose-Headers' 'Authorization' always;

        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin'  '*';
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS';
            add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization';
            add_header 'Content-Type' 'text/plain charset=UTF-8';
            add_header 'Content-Length' 0;
            return 204;
        }
    }

    # --- Static files ---
    location / {
        try_files $uri $uri/ $uri.html =404;
    }

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml image/svg+xml;
    gzip_min_length 1000;
}

server {
    listen 80;
    listen [::]:80;
    server_name api.swipies.app;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.swipies.app;

    ssl_certificate     /etc/letsencrypt/live/swipies.app/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/swipies.app/privkey.pem;
    include             /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam         /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass         http://127.0.0.1:9222;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

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
    server_name app.swipies.app;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name app.swipies.app;

    ssl_certificate     /etc/letsencrypt/live/swipies.app/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/swipies.app/privkey.pem;
    include             /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam         /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass         http://127.0.0.1:9222;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

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
"""

conf_path = '/etc/nginx/sites-available/swipies'
enabled_path = '/etc/nginx/sites-enabled/swipies'

# Remove default site if present
default_enabled = '/etc/nginx/sites-enabled/default'
if os.path.exists(default_enabled):
    os.remove(default_enabled)
    print(f"Removed default nginx site: {default_enabled}")

# Write new config
with open(conf_path, 'w') as f:
    f.write(NGINX_CONF)
print(f"Written nginx config: {conf_path}")

# Enable site
if not os.path.exists(enabled_path):
    os.symlink(conf_path, enabled_path)
    print(f"Enabled nginx site: {enabled_path}")
else:
    print(f"Nginx site already enabled: {enabled_path}")

print("=== SSL CERTIFICATES ===")
if os.path.exists('/etc/letsencrypt/live'):
    print(os.listdir('/etc/letsencrypt/live'))
    # Print certificate details for swipies.app
    cert_path = '/etc/letsencrypt/live/swipies.app/fullchain.pem'
    if os.path.exists(cert_path):
        import subprocess
        try:
            out = subprocess.check_output(['openssl', 'x509', '-in', cert_path, '-text', '-noout'], stderr=subprocess.STDOUT).decode('utf-8')
            for line in out.split('\n'):
                if 'DNS:' in line:
                    print("swipies.app cert covers:", line.strip())
        except Exception as e:
            print("Error reading cert:", e)
else:
    print("No /etc/letsencrypt/live directory")

print("=== AVAILABLE NGINX SITES ===")
if os.path.exists('/etc/nginx/sites-available'):
    print(os.listdir('/etc/nginx/sites-available'))
else:
    print("No /etc/nginx/sites-available directory")

print("Nginx config written successfully. Run: sudo nginx -t && sudo systemctl reload nginx")
