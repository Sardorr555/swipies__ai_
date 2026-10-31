import sqlite3
import os
import datetime
import urllib.request
import urllib.parse
import json
import hashlib
import secrets
import threading
import time
import re
import html
from collections import defaultdict
from functools import wraps
from flask import Flask, request, jsonify

# Auto-load .env file if present in the current or script directory
def load_dotenv():
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_file):
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

load_dotenv()
from landing_platform_reports import load_private_settings
load_private_settings()

app = Flask(__name__)

# Use absolute path so the DB is found regardless of working directory
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.sqlite')

# Optional Telegram notification (set these env vars on the server to enable)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID   = os.environ.get('TELEGRAM_CHAT_ID', '')

# --- Rate Limiting & Bot Protection ---
_rate_limit_lock = threading.Lock()
_rate_limits = defaultdict(list)

def get_client_ip(req=None):
    """Extract real client IP address, handling reverse proxies."""
    if req is None:
        req = request
    xff = req.headers.get('X-Forwarded-For')
    if xff:
        return xff.split(',')[0].strip()
    xri = req.headers.get('X-Real-IP')
    if xri:
        return xri.strip()
    return req.remote_addr or '127.0.0.1'

def is_rate_limited(key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
    """Check if key has exceeded max_requests in window_seconds without consuming quota."""
    now = time.time()
    with _rate_limit_lock:
        valid = [t for t in _rate_limits[key] if now - t < window_seconds]
        _rate_limits[key] = valid
        if len(valid) >= max_requests:
            retry_after = max(1, int(window_seconds - (now - valid[0])))
            return True, retry_after
        return False, 0

def record_rate_limit_attempt(key: str):
    """Record an attempt or hit for a given key."""
    now = time.time()
    with _rate_limit_lock:
        _rate_limits[key].append(now)

def check_rate_limit(key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
    """Check if key is within rate limit; if so, records the attempt and returns (True, 0).
    If limit is exceeded, returns (False, retry_after)."""
    now = time.time()
    with _rate_limit_lock:
        valid = [t for t in _rate_limits[key] if now - t < window_seconds]
        if len(valid) >= max_requests:
            retry_after = max(1, int(window_seconds - (now - valid[0])))
            _rate_limits[key] = valid
            return False, retry_after
        valid.append(now)
        _rate_limits[key] = valid
        return True, 0

def clear_rate_limits_key(key: str):
    """Clear recorded rate limit attempts for a specific key."""
    with _rate_limit_lock:
        _rate_limits.pop(key, None)

def clear_rate_limits():
    """Clear all rate limit tracking (utility for testing)."""
    with _rate_limit_lock:
        _rate_limits.clear()

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

def validate_lead_payload(data):
    """Validate and sanitize lead submission payload."""
    raw_name = (data.get('name') or '').strip()
    raw_company = (data.get('company') or '').strip()
    raw_email = (data.get('email') or '').strip()
    raw_phone = (data.get('phone') or '').strip()
    raw_message = (data.get('message') or '').strip()
    raw_referral = (data.get('referral_code') or '').strip()
    source = (data.get('source') or 'b2c').strip().lower()

    if source not in ('b2c', 'enterprise'):
        source = 'b2c'

    if not raw_name:
        return None, "Name is required"
    if len(raw_name) > 120:
        return None, "Name exceeds maximum length of 120 characters"
    if len(raw_company) > 150:
        return None, "Company exceeds maximum length of 150 characters"
    if len(raw_message) > 3000:
        return None, "Message exceeds maximum length of 3000 characters"

    if not raw_email and not raw_phone:
        return None, "Either email or phone number is required as a contact method"

    if raw_email:
        if len(raw_email) > 120:
            return None, "Email exceeds maximum length of 120 characters"
        if not EMAIL_REGEX.match(raw_email):
            return None, "Invalid email address format"

    if raw_phone:
        if len(raw_phone) > 40:
            return None, "Phone number exceeds maximum length of 40 characters"
        digits = [c for c in raw_phone if c.isdigit()]
        if len(digits) < 5:
            return None, "Phone number must contain at least 5 digits"

    return {
        'name': html.escape(raw_name),
        'company': html.escape(raw_company),
        'email': raw_email,
        'phone': raw_phone,
        'message': html.escape(raw_message),
        'referral_code': html.escape(raw_referral[:50]),
        'source': source
    }, None


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def utc_now_iso():
    return utc_now().isoformat()


def hash_password(password: str, salt: bytes = None) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256 and a random salt."""
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100_000)
    return f"{salt.hex()}:{dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a plaintext password against stored salt:hash string."""
    try:
        salt_hex, hash_hex = stored_hash.split(':')
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100_000)
        return secrets.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def get_authenticated_admin(req):
    """Extract and validate Bearer token from Authorization header or X-Admin-Token."""
    auth_header = req.headers.get('Authorization', '')
    token = ''
    if auth_header.startswith('Bearer '):
        token = auth_header[7:].strip()
    elif auth_header.startswith('Token '):
        token = auth_header[6:].strip()
    elif req.headers.get('X-Admin-Token'):
        token = req.headers.get('X-Admin-Token').strip()

    if not token:
        return None

    now_iso = utc_now_iso()
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT username, expires_at FROM admin_sessions
                WHERE token = ?
            ''', (token,))
            row = cursor.fetchone()
            if not row:
                return None
            username, expires_at = row
            if expires_at < now_iso:
                cursor.execute('DELETE FROM admin_sessions WHERE token = ?', (token,))
                conn.commit()
                return None
            return username
    except Exception as e:
        print(f"[Auth] Session lookup error: {e}")
        return None


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin = get_authenticated_admin(request)
        if not admin:
            return jsonify({"code": 401, "message": "Unauthorized: Valid admin token required"}), 401
        return f(*args, **kwargs)
    return decorated_function


def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS platform_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                nickname TEXT,
                visitor_id TEXT,
                session_id TEXT,
                utm_source TEXT,
                utm_medium TEXT,
                utm_campaign TEXT,
                utm_term TEXT,
                utm_content TEXT,
                referred_by TEXT,
                is_active INTEGER DEFAULT 1,
                is_superuser INTEGER DEFAULT 0,
                knowledgebases_count INTEGER DEFAULT 0,
                dialogs_count INTEGER DEFAULT 0,
                tokens_consumed INTEGER DEFAULT 0,
                last_active_date TEXT,
                create_date TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS platform_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                visitor_id TEXT,
                event_name TEXT NOT NULL, -- e.g. registered, created_kb, asked_question, logged_in
                metadata TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                message TEXT,
                referral_code TEXT,
                status TEXT DEFAULT '1', -- 1 = unread, 2 = read
                source TEXT DEFAULT 'b2c', -- 'b2c' or 'enterprise'
                create_date TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS visitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visitor_id TEXT,
                session_id TEXT,
                fingerprint_hash TEXT,
                canvas_fp TEXT,
                webgl_fp TEXT,
                audio_fp TEXT,
                ip TEXT,
                country TEXT,
                city TEXT,
                isp TEXT,
                is_proxy TEXT,
                connection_type TEXT,
                network_type TEXT,
                network_downlink TEXT,
                network_rtt TEXT,
                cpu_cores TEXT,
                ram_gb TEXT,
                gpu_info TEXT,
                screen_res TEXT,
                viewport_size TEXT,
                pixel_ratio TEXT,
                color_depth INTEGER DEFAULT 24,
                touch_support TEXT,
                theme_pref TEXT,
                session_duration INTEGER DEFAULT 0,
                scroll_depth INTEGER DEFAULT 0,
                sections_viewed TEXT,
                first_interaction_time INTEGER DEFAULT 0,
                clicks_count INTEGER DEFAULT 0,
                clicked_buttons TEXT,
                is_bot_detected TEXT DEFAULT 'No',
                page_url TEXT,
                page_title TEXT,
                referrer TEXT,
                initial_referrer TEXT,
                landing_page TEXT,
                visit_count INTEGER DEFAULT 1,
                last_seen_date TEXT,
                utm_source TEXT,
                utm_medium TEXT,
                utm_campaign TEXT,
                utm_term TEXT,
                utm_content TEXT,
                user_agent TEXT,
                device_type TEXT,
                browser TEXT,
                os TEXT,
                language TEXT,
                timezone TEXT,
                cookie_consent TEXT,
                create_date TEXT NOT NULL
            )
        ''')

        # Automatic column migration for existing database files
        cursor.execute("PRAGMA table_info(leads)")
        existing_lead_cols = [row[1] for row in cursor.fetchall()]
        if 'source' not in existing_lead_cols:
            cursor.execute("ALTER TABLE leads ADD COLUMN source TEXT DEFAULT 'b2c'")

        cursor.execute("PRAGMA table_info(visitors)")
        existing_cols = [row[1] for row in cursor.fetchall()]
        new_cols = {
            'country': 'TEXT',
            'city': 'TEXT',
            'isp': 'TEXT',
            'is_proxy': 'TEXT',
            'connection_type': 'TEXT',
            'cpu_cores': 'TEXT',
            'ram_gb': 'TEXT',
            'gpu_info': 'TEXT',
            'theme_pref': 'TEXT',
            'session_duration': 'INTEGER DEFAULT 0',
            'scroll_depth': 'INTEGER DEFAULT 0',
            'clicked_buttons': 'TEXT',
            'utm_source': 'TEXT',
            'utm_medium': 'TEXT',
            'utm_campaign': 'TEXT',
            'utm_term': 'TEXT',
            'utm_content': 'TEXT',
            'session_id': 'TEXT',
            'fingerprint_hash': 'TEXT',
            'canvas_fp': 'TEXT',
            'webgl_fp': 'TEXT',
            'audio_fp': 'TEXT',
            'viewport_size': 'TEXT',
            'pixel_ratio': 'TEXT',
            'color_depth': 'INTEGER DEFAULT 24',
            'touch_support': 'TEXT',
            'network_type': 'TEXT',
            'network_downlink': 'TEXT',
            'network_rtt': 'TEXT',
            'first_interaction_time': 'INTEGER DEFAULT 0',
            'sections_viewed': 'TEXT',
            'clicks_count': 'INTEGER DEFAULT 0',
            'is_bot_detected': "TEXT DEFAULT 'No'",
            'page_title': 'TEXT',
            'initial_referrer': 'TEXT',
            'landing_page': 'TEXT',
            'visit_count': 'INTEGER DEFAULT 1',
            'last_seen_date': 'TEXT'
        }
        for col_name, col_type in new_cols.items():
            if col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE visitors ADD COLUMN {col_name} {col_type}")

        cursor.execute("PRAGMA table_info(platform_users)")
        existing_pu_cols = [row[1] for row in cursor.fetchall()]
        for col_name in ('utm_term', 'utm_content'):
            if col_name not in existing_pu_cols:
                cursor.execute(f"ALTER TABLE platform_users ADD COLUMN {col_name} TEXT")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_visitors_session_id ON visitors(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_visitors_visitor_id ON visitors(visitor_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_visitors_fp_hash ON visitors(fingerprint_hash)")

        # Normalize malformed +00:00Z timestamps so JS Date parsing succeeds
        cursor.execute("UPDATE visitors SET create_date = REPLACE(create_date, '+00:00Z', '+00:00') WHERE create_date LIKE '%+00:00Z'")
        cursor.execute("UPDATE visitors SET last_seen_date = REPLACE(last_seen_date, '+00:00Z', '+00:00') WHERE last_seen_date LIKE '%+00:00Z'")
        cursor.execute("UPDATE leads SET create_date = REPLACE(create_date, '+00:00Z', '+00:00') WHERE create_date LIKE '%+00:00Z'")

        # Ensure at least one admin user exists
        cursor.execute("SELECT COUNT(*) FROM admin_users")
        if cursor.fetchone()[0] == 0:
            default_pwd = os.environ.get('SWIPIES_ADMIN_PASSWORD')
            if not default_pwd:
                # If no password is provided in environment, generate a cryptographically strong random password
                default_pwd = secrets.token_urlsafe(16)
                print(f"[SECURITY] Generated initial one-time password for 'admin': {default_pwd}")
                print("[SECURITY] Please set the SWIPIES_ADMIN_PASSWORD environment variable or change this password immediately.")
            cursor.execute('''
                INSERT INTO admin_users (username, password_hash, created_at)
                VALUES (?, ?, ?)
            ''', ('admin', hash_password(default_pwd), utc_now_iso()))

        conn.commit()



def get_ip_geo(ip):
    """Fetch country, city, ISP, and proxy/VPN status for an IP address."""
    if not ip or ip in ('127.0.0.1', '::1', 'localhost') or ip.startswith(('192.168.', '10.', '172.16.')):
        return {
            'country': 'Local Host',
            'city': 'Local Network',
            'isp': 'Internal Loopback',
            'is_proxy': 'No'
        }

    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,city,isp,org,mobile,proxy,hosting"
        req = urllib.request.Request(url, headers={'User-Agent': 'Swipies-GeoIP/1.0'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            geo_data = json.loads(resp.read().decode('utf-8'))
            if geo_data.get('status') == 'success':
                is_proxy_val = 'Yes' if (geo_data.get('proxy') or geo_data.get('hosting')) else 'No'
                return {
                    'country': geo_data.get('country') or 'Unknown Country',
                    'country_code': geo_data.get('countryCode') or '',
                    'city': geo_data.get('city') or 'Unknown City',
                    'isp': geo_data.get('isp') or geo_data.get('org') or 'Unknown ISP',
                    'is_proxy': is_proxy_val
                }
    except Exception as e:
        print(f"[GeoIP] Lookup failed for {ip}: {e}")

    return {
        'country': 'Unknown Country',
        'country_code': '',
        'city': 'Unknown City',
        'isp': 'Unknown ISP',
        'is_proxy': 'No'
    }


def parse_user_agent(ua_str):
    """Simple UA string parser for browser, OS, and device type."""
    ua = (ua_str or '').lower()

    # Device type
    if 'mobile' in ua or 'android' in ua and 'mobile' in ua or 'iphone' in ua or 'ipod' in ua:
        device = 'Mobile'
    elif 'ipad' in ua or 'tablet' in ua or 'android' in ua:
        device = 'Tablet'
    else:
        device = 'Desktop'

    # Operating System
    if 'windows' in ua:
        os_name = 'Windows'
    elif 'macintosh' in ua or 'mac os' in ua:
        os_name = 'macOS'
    elif 'iphone' in ua or 'ipad' in ua or 'ipod' in ua:
        os_name = 'iOS'
    elif 'android' in ua:
        os_name = 'Android'
    elif 'linux' in ua:
        os_name = 'Linux'
    else:
        os_name = 'Unknown OS'

    # Browser
    if 'edg/' in ua or 'edge' in ua:
        browser = 'Edge'
    elif 'chrome' in ua or 'crios' in ua:
        browser = 'Chrome'
    elif 'firefox' in ua or 'fxios' in ua:
        browser = 'Firefox'
    elif 'safari' in ua:
        browser = 'Safari'
    elif 'opera' in ua or 'opr/' in ua:
        browser = 'Opera'
    else:
        browser = 'Other Browser'

    return {'device': device, 'os': os_name, 'browser': browser}


def send_telegram(text):
    """Fire-and-forget Telegram message; silently fails if not configured."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
        payload = json.dumps({
            'chat_id': TELEGRAM_CHAT_ID,
            'text': text,
            'parse_mode': 'HTML'
        }).encode('utf-8')
        req = urllib.request.Request(url, data=payload,
                                     headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"[Telegram] Failed to send notification: {e}")


@app.route('/api/geo', methods=['GET'])
def get_geo():
    """Returns detected visitor country and recommended currency."""
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        ip = request.headers.get('X-Real-IP').strip()
    else:
        ip = request.remote_addr or '127.0.0.1'

    geo = get_ip_geo(ip)
    country = geo.get('country', '')
    country_code = (geo.get('country_code') or '').upper()
    is_uz = (country.lower() in ('uzbekistan', 'uz') or country_code == 'UZ')
    return jsonify({
        "code": 0,
        "ip": ip,
        "country": country,
        "country_code": "UZ" if is_uz else country_code,
        "is_uz": is_uz,
        "currency": "UZS" if is_uz else "USD"
    })


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    ip = get_client_ip()

    # 1. Check if IP is blocked due to too many failed login attempts
    is_blocked, retry_after = is_rate_limited(f"login_fail:{ip}", max_requests=5, window_seconds=900)
    if is_blocked:
        resp = jsonify({
            "code": 429,
            "message": f"Too many failed login attempts. Please try again in {retry_after} seconds.",
            "retry_after": retry_after
        })
        resp.headers['Retry-After'] = str(retry_after)
        return resp, 429

    # 2. General burst rate limiting on login endpoint (max 20 req/minute per IP)
    is_burst_ok, burst_retry = check_rate_limit(f"login_burst:{ip}", max_requests=20, window_seconds=60)
    if not is_burst_ok:
        resp = jsonify({
            "code": 429,
            "message": f"Too many requests to login endpoint. Please wait {burst_retry} seconds.",
            "retry_after": burst_retry
        })
        resp.headers['Retry-After'] = str(burst_retry)
        return resp, 429

    data = request.json or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({"code": 1, "message": "Username and password are required"}), 400

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT username, password_hash FROM admin_users WHERE username = ?', (username,))
        user_row = cursor.fetchone()

        # Support login by email if admin set email or entered email prefix
        if not user_row and ('@' in username or username == 'admin'):
            cursor.execute('SELECT username, password_hash FROM admin_users WHERE username = ?', (username.split('@')[0],))
            user_row = cursor.fetchone()

        if not user_row or not verify_password(password, user_row[1]):
            # Record failed login attempt for brute-force protection
            record_rate_limit_attempt(f"login_fail:{ip}")
            return jsonify({"code": 1, "message": "Invalid username or password"}), 401

        # Clear failed login record on successful authentication
        clear_rate_limits_key(f"login_fail:{ip}")

        actual_username = user_row[0]
        token = secrets.token_urlsafe(32)
        created_at = utc_now_iso()
        expires_at = (utc_now() + datetime.timedelta(hours=24)).isoformat()

        cursor.execute('''
            INSERT INTO admin_sessions (token, username, created_at, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (token, actual_username, created_at, expires_at))
        conn.commit()

    return jsonify({
        "code": 0,
        "message": "Authenticated",
        "token": token,
        "username": actual_username,
        "expires_at": expires_at
    }), 200


@app.route('/api/auth/verify', methods=['GET'])
@admin_required
def auth_verify():
    admin = get_authenticated_admin(request)
    return jsonify({"code": 0, "status": "authenticated", "username": admin})


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    auth_header = request.headers.get('Authorization', '')
    token = ''
    if auth_header.startswith('Bearer '):
        token = auth_header[7:].strip()
    elif auth_header.startswith('Token '):
        token = auth_header[6:].strip()
    elif request.headers.get('X-Admin-Token'):
        token = request.headers.get('X-Admin-Token').strip()

    if token:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM admin_sessions WHERE token = ?', (token,))
            conn.commit()

    return jsonify({"code": 0, "message": "Logged out successfully"})


@app.route('/api/auth/change_password', methods=['POST'])
@admin_required
def auth_change_password():
    admin = get_authenticated_admin(request)
    data = request.json or {}
    new_password = (data.get('new_password') or '').strip()
    if not new_password or len(new_password) < 6:
        return jsonify({"code": 1, "message": "New password must be at least 6 characters long"}), 400

    new_hash = hash_password(new_password)
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE admin_users SET password_hash = ? WHERE username = ?', (new_hash, admin))
        conn.commit()

    return jsonify({"code": 0, "message": "Password updated successfully"})


@app.route('/api/leads', methods=['POST'])
def create_lead():
    ip = get_client_ip()

    # Rate limiting on lead submissions (max 5 submissions per 10 minutes per IP)
    allowed, retry_after = check_rate_limit(f"leads:{ip}", max_requests=5, window_seconds=600)
    if not allowed:
        return jsonify({
            "code": 429,
            "message": f"Too many lead submissions from your IP. Please wait {retry_after} seconds before trying again.",
            "retry_after": retry_after
        }), 429

    data = request.json or {}

    # Honeypot spam bot trap
    hp_field = (data.get('hp_field') or data.get('website_url') or data.get('address_field') or '').strip()
    source = (data.get('source') or 'b2c').strip().lower()
    if source not in ('b2c', 'enterprise'):
        source = 'b2c'

    if hp_field:
        # Silent drop: fake 201 so the spam bot believes it succeeded,
        # but do not store in DB and do not send Telegram notification
        return jsonify({
            "code": 0,
            "data": {"id": -1, "source": source},
            "message": "Success"
        }), 201

    # Validate and sanitize inputs
    cleaned, err = validate_lead_payload(data)
    if err:
        return jsonify({"code": 1, "message": err}), 400

    company       = cleaned['company']
    name          = cleaned['name']
    email         = cleaned['email']
    phone         = cleaned['phone']
    message       = cleaned['message']
    referral_code = cleaned['referral_code']
    source        = cleaned['source']
    create_date   = utc_now_iso()

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO leads (company, name, email, phone, message, referral_code, source, create_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (company, name, email, phone, message, referral_code, source, create_date))
        conn.commit()
        lead_id = cursor.lastrowid

    # Notify admin via Telegram
    channel_label = "Enterprise (enterprise.swipies.app)" if source == "enterprise" else "B2C Cloud (swipies.app)"
    tg_msg = (
        f"📬 <b>New Lead — {channel_label}</b>\n\n"
        f"🌐 <b>Channel:</b> {channel_label}\n"
        f"👤 <b>Name:</b> {name}\n"
        f"🏢 <b>Company:</b> {company}\n"
        f"📧 <b>Email:</b> {email}\n"
        f"📞 <b>Phone:</b> {phone or '—'}\n"
        f"💬 <b>Message:</b> {message or '—'}\n"
        f"🔗 <b>Ref Code:</b> {referral_code or '—'}\n"
        f"🕐 <b>Time (UTC):</b> {create_date}"
    )
    send_telegram(tg_msg)

    return jsonify({"code": 0, "message": "Success", "data": {"id": lead_id, "source": source}}), 201


@app.route('/api/leads', methods=['GET'])
@admin_required
def get_leads():
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM leads ORDER BY id DESC')
        rows = cursor.fetchall()

    leads = [dict(row) for row in rows]
    return jsonify({"code": 0, "data": leads})


@app.route('/api/leads/<int:lead_id>', methods=['PUT'])
@admin_required
def update_lead(lead_id):
    data = request.json or {}
    new_status = data.get('status')
    if not new_status:
        return jsonify({"code": 1, "message": "Status required"}), 400

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE leads SET status = ? WHERE id = ?', (new_status, lead_id))
        conn.commit()

    return jsonify({"code": 0, "message": "Updated"})


@app.route('/api/leads/<int:lead_id>', methods=['DELETE'])
@admin_required
def delete_lead(lead_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM leads WHERE id = ?', (lead_id,))
        conn.commit()

    return jsonify({"code": 0, "message": "Deleted"})


@app.route('/api/visitors', methods=['POST'])
def track_visitor():
    ip = get_client_ip()

    # Rate limiting on visitor tracking (max 60 hits/minute per IP)
    allowed, retry_after = check_rate_limit(f"visitors:{ip}", max_requests=60, window_seconds=60)
    if not allowed:
        return jsonify({
            "code": 429,
            "message": "Visitor tracking rate limit exceeded",
            "retry_after": retry_after
        }), 429

    data = request.get_json(silent=True)
    if not data and request.data:
        try:
            data = json.loads(request.data.decode('utf-8'))
        except Exception:
            data = {}
    if not data:
        data = request.form.to_dict() or {}

    user_agent = request.headers.get('User-Agent', '') or data.get('user_agent', '')
    session_id = str(data.get('session_id') or '').strip()
    visitor_id = str(data.get('visitor_id') or '').strip()
    fingerprint_hash = str(data.get('fingerprint_hash') or '').strip()
    canvas_fp = str(data.get('canvas_fp') or '').strip()
    webgl_fp = str(data.get('webgl_fp') or '').strip()
    audio_fp = str(data.get('audio_fp') or '').strip()

    screen_res = str(data.get('screen_res') or '').strip()
    viewport_size = str(data.get('viewport_size') or '').strip()
    pixel_ratio = str(data.get('pixel_ratio') or '').strip()
    color_depth = int(data.get('color_depth', 24) or 24)
    touch_support = str(data.get('touch_support') or '').strip()

    connection_type = str(data.get('connection_type') or '').strip()
    network_type = str(data.get('network_type') or '').strip()
    network_downlink = str(data.get('network_downlink') or '').strip()
    network_rtt = str(data.get('network_rtt') or '').strip()

    cpu_cores = str(data.get('cpu_cores') or '').strip()
    ram_gb = str(data.get('ram_gb') or '').strip()
    gpu_info = str(data.get('gpu_info') or '').strip()
    theme_pref = str(data.get('theme_pref') or '').strip()

    session_duration = int(data.get('session_duration', 0) or 0)
    scroll_depth = int(data.get('scroll_depth', 0) or 0)

    sections_viewed = data.get('sections_viewed', '')
    if isinstance(sections_viewed, list):
        sections_viewed = ", ".join(s.strip() for s in sections_viewed if s)
    else:
        sections_viewed = str(sections_viewed or '').strip()

    first_interaction_time = int(data.get('first_interaction_time', 0) or 0)
    clicks_count = int(data.get('clicks_count', 0) or 0)

    clicked_buttons = data.get('clicked_buttons', '')
    if isinstance(clicked_buttons, list):
        clicked_buttons = ", ".join(c.strip() for c in clicked_buttons if c)
    else:
        clicked_buttons = str(clicked_buttons or '').strip()

    is_bot_detected = str(data.get('is_bot_detected') or 'No').strip()
    if not is_bot_detected:
        is_bot_detected = 'No'

    page_url = str(data.get('page_url') or '').strip()
    page_title = str(data.get('page_title') or '').strip()
    referrer = str(data.get('referrer') or '').strip()
    initial_referrer = str(data.get('initial_referrer') or referrer or 'Direct').strip()
    landing_page = str(data.get('landing_page') or page_url or '/').strip()
    language = str(data.get('language') or '').strip()
    timezone = str(data.get('timezone') or '').strip()
    visit_count = int(data.get('visit_count', 1) or 1)
    cookie_consent = str(data.get('cookie_consent') or 'accepted').strip()

    utm_source = str(data.get('utm_source') or '').strip()
    utm_medium = str(data.get('utm_medium') or '').strip()
    utm_campaign = str(data.get('utm_campaign') or '').strip()
    utm_term = str(data.get('utm_term') or '').strip()
    utm_content = str(data.get('utm_content') or '').strip()

    now_iso = utc_now_iso()
    create_date = now_iso
    last_seen_date = now_iso

    parsed_ua = parse_user_agent(user_agent)
    device_type = parsed_ua['device']
    browser = parsed_ua['browser']
    os_name = parsed_ua['os']

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Check if visitor entry already exists for session update
        existing_row = None
        if session_id:
            cursor.execute('''
                SELECT id, clicked_buttons, scroll_depth, session_duration, sections_viewed, clicks_count, first_interaction_time, is_bot_detected
                FROM visitors WHERE session_id = ? ORDER BY id DESC LIMIT 1
            ''', (session_id,))
            existing_row = cursor.fetchone()
        elif visitor_id:
            cursor.execute('''
                SELECT id, clicked_buttons, scroll_depth, session_duration, sections_viewed, clicks_count, first_interaction_time, is_bot_detected
                FROM visitors WHERE visitor_id = ? ORDER BY id DESC LIMIT 1
            ''', (visitor_id,))
            existing_row = cursor.fetchone()

        if existing_row:
            v_id, old_clicks_btn, old_scroll, old_dur, old_sections, old_clicks_cnt, old_fit, old_bot = existing_row

            # Merge clicked buttons
            new_btn_list = [c.strip() for c in (clicked_buttons or '').split(',') if c.strip()]
            old_btn_list = [c.strip() for c in (old_clicks_btn or '').split(',') if c.strip()]
            merged_buttons = ", ".join(dict.fromkeys(old_btn_list + new_btn_list))

            # Merge sections viewed
            new_sec_list = [s.strip() for s in (sections_viewed or '').split(',') if s.strip()]
            old_sec_list = [s.strip() for s in (old_sections or '').split(',') if s.strip()]
            merged_sections = ", ".join(dict.fromkeys(old_sec_list + new_sec_list))

            new_scroll = max(scroll_depth, old_scroll or 0)
            new_duration = max(session_duration, old_dur or 0)
            new_clicks_cnt = max(clicks_count, old_clicks_cnt or 0)
            new_fit = old_fit if (old_fit and old_fit > 0) else first_interaction_time
            bot_flag = is_bot_detected if (is_bot_detected and is_bot_detected != 'No') else (old_bot or 'No')

            cursor.execute('''
                UPDATE visitors SET
                    cookie_consent = COALESCE(NULLIF(?, ''), cookie_consent),
                    connection_type = COALESCE(NULLIF(?, ''), connection_type),
                    network_type = COALESCE(NULLIF(?, ''), network_type),
                    network_downlink = COALESCE(NULLIF(?, ''), network_downlink),
                    network_rtt = COALESCE(NULLIF(?, ''), network_rtt),
                    cpu_cores = COALESCE(NULLIF(?, ''), cpu_cores),
                    ram_gb = COALESCE(NULLIF(?, ''), ram_gb),
                    gpu_info = COALESCE(NULLIF(?, ''), gpu_info),
                    theme_pref = COALESCE(NULLIF(?, ''), theme_pref),
                    session_duration = ?,
                    scroll_depth = ?,
                    sections_viewed = ?,
                    clicks_count = ?,
                    clicked_buttons = ?,
                    first_interaction_time = ?,
                    is_bot_detected = ?,
                    last_seen_date = ?,
                    screen_res = COALESCE(NULLIF(?, ''), screen_res),
                    viewport_size = COALESCE(NULLIF(?, ''), viewport_size),
                    pixel_ratio = COALESCE(NULLIF(?, ''), pixel_ratio),
                    color_depth = CASE WHEN ? > 0 THEN ? ELSE color_depth END,
                    touch_support = COALESCE(NULLIF(?, ''), touch_support),
                    language = COALESCE(NULLIF(?, ''), language),
                    utm_source = COALESCE(NULLIF(?, ''), utm_source),
                    utm_medium = COALESCE(NULLIF(?, ''), utm_medium),
                    utm_campaign = COALESCE(NULLIF(?, ''), utm_campaign),
                    utm_term = COALESCE(NULLIF(?, ''), utm_term),
                    utm_content = COALESCE(NULLIF(?, ''), utm_content)
                WHERE id = ?
            ''', (
                cookie_consent, connection_type, network_type, network_downlink, network_rtt,
                cpu_cores, ram_gb, gpu_info, theme_pref,
                new_duration, new_scroll, merged_sections, new_clicks_cnt, merged_buttons,
                new_fit, bot_flag, last_seen_date,
                screen_res, viewport_size, pixel_ratio, color_depth, color_depth,
                touch_support, language,
                utm_source, utm_medium, utm_campaign, utm_term, utm_content,
                v_id
            ))
            conn.commit()

            return jsonify({"code": 0, "message": "Visitor telemetry updated", "data": {"id": v_id}}), 200

        else:
            # Perform GeoIP lookup for new visitor
            geo = get_ip_geo(ip)
            country = geo['country']
            city = geo['city']
            isp = geo['isp']
            is_proxy = geo['is_proxy']

            cursor.execute('''
                INSERT INTO visitors (
                    visitor_id, session_id, fingerprint_hash, canvas_fp, webgl_fp, audio_fp,
                    ip, country, city, isp, is_proxy,
                    connection_type, network_type, network_downlink, network_rtt,
                    cpu_cores, ram_gb, gpu_info, screen_res, viewport_size, pixel_ratio,
                    color_depth, touch_support, theme_pref,
                    session_duration, scroll_depth, sections_viewed,
                    first_interaction_time, clicks_count, clicked_buttons, is_bot_detected,
                    page_url, page_title, referrer, initial_referrer, landing_page,
                    visit_count, last_seen_date,
                    utm_source, utm_medium, utm_campaign, utm_term, utm_content,
                    user_agent, device_type, browser, os, language, timezone,
                    cookie_consent, create_date
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?
                )
            ''', (
                visitor_id, session_id, fingerprint_hash, canvas_fp, webgl_fp, audio_fp,
                ip, country, city, isp, is_proxy,
                connection_type, network_type, network_downlink, network_rtt,
                cpu_cores, ram_gb, gpu_info, screen_res, viewport_size, pixel_ratio,
                color_depth, touch_support, theme_pref,
                session_duration, scroll_depth, sections_viewed,
                first_interaction_time, clicks_count, clicked_buttons, is_bot_detected,
                page_url, page_title, referrer, initial_referrer, landing_page,
                visit_count, last_seen_date,
                utm_source, utm_medium, utm_campaign, utm_term, utm_content,
                user_agent, device_type, browser, os_name, language, timezone,
                cookie_consent, create_date
            ))
            conn.commit()
            v_id = cursor.lastrowid

            return jsonify({"code": 0, "message": "Visitor tracked", "data": {"id": v_id}}), 201


@app.route('/api/visitors', methods=['GET'])
@admin_required
def get_visitors():
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM visitors ORDER BY id DESC LIMIT 500')
        rows = cursor.fetchall()

    visitors = [dict(row) for row in rows]
    total_count = len(visitors)
    unique_ips = len(set(v['ip'] for v in visitors if v.get('ip')))
    accepted_count = sum(1 for v in visitors if v.get('cookie_consent') == 'accepted')
    consent_rate = round((accepted_count / total_count * 100), 1) if total_count > 0 else 100.0
    vpn_count = sum(1 for v in visitors if v.get('is_proxy') == 'Yes')
    bot_count = sum(1 for v in visitors if v.get('is_bot_detected') and v.get('is_bot_detected') != 'No')

    avg_duration = round(sum(v.get('session_duration') or 0 for v in visitors) / total_count) if total_count > 0 else 0
    avg_scroll = round(sum(v.get('scroll_depth') or 0 for v in visitors) / total_count) if total_count > 0 else 0

    return jsonify({
        "code": 0,
        "data": visitors,
        "stats": {
            "total_visits": total_count,
            "unique_ips": unique_ips,
            "accepted_count": accepted_count,
            "consent_rate": consent_rate,
            "vpn_count": vpn_count,
            "bot_count": bot_count,
            "avg_duration": avg_duration,
            "avg_scroll": avg_scroll
        }
    })


@app.route('/api/visitors/<int:v_id>', methods=['DELETE'])
@admin_required
def delete_visitor(v_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM visitors WHERE id = ?', (v_id,))
        conn.commit()

    return jsonify({"code": 0, "message": "Visitor record deleted"})


@app.route('/api/visitors/clear', methods=['DELETE'])
@admin_required
def clear_visitors():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM visitors')
        conn.commit()

    return jsonify({"code": 0, "message": "All visitor records cleared"})



@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"code": 0, "status": "ok", "db": DB_FILE})


# --- PLATFORM TELEMETRY & PRODUCT ANALYTICS ---

def sync_mysql_platform_users():
    """Sync live registered users, knowledgebases, dialogs, and token usage from Swipies MySQL (rag_flow)."""
    if not DB_FILE.endswith('database.sqlite'):
        return
    try:
        import pymysql
        mysql_host = os.environ.get('MYSQL_HOST', '127.0.0.1')
        mysql_port = int(os.environ.get('MYSQL_PORT', '5455'))
        mysql_user = os.environ.get('MYSQL_USER', 'root')
        mysql_pwd = os.environ.get('MYSQL_PASSWORD', '')
        mysql_db = os.environ.get('MYSQL_DBNAME', 'rag_flow')

        mconn = pymysql.connect(
            host=mysql_host, port=mysql_port,
            user=mysql_user, password=mysql_pwd,
            database=mysql_db,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=2
        )
        with mconn.cursor() as mcur:
            mcur.execute("""
                SELECT
                    u.id, u.email, u.nickname, u.is_active, u.is_superuser, u.status,
                    u.create_date, u.update_date, u.last_login_time,
                    u.visitor_id, u.session_id, u.utm_source, u.utm_medium, u.utm_campaign, u.utm_term, u.utm_content,
                    ref.email AS referred_by_email,
                    (SELECT COUNT(*) FROM knowledgebase k WHERE k.created_by = u.id AND k.status = '1') AS kb_count,
                    (SELECT COALESCE(SUM(k.token_num), 0) FROM knowledgebase k WHERE k.created_by = u.id AND k.status = '1') +
                    (SELECT COALESCE(SUM(t.total_tokens), 0) FROM token_usage_log t WHERE t.user_id = u.id OR t.tenant_id = u.id) AS tokens_used,
                    (SELECT COUNT(*) FROM dialog d WHERE d.tenant_id = u.id AND d.status = '1') AS dialog_count
                FROM user u
                LEFT JOIN user ref ON u.referred_by_id = ref.id
                WHERE u.status = '1'
            """)
            mrows = mcur.fetchall()
        mconn.close()

        with sqlite3.connect(DB_FILE) as sconn:
            scur = sconn.cursor()
            for r in mrows:
                email = (r.get('email') or '').strip().lower()
                if not email:
                    continue
                nickname = (r.get('nickname') or '').strip()
                is_active = 1 if str(r.get('is_active', '1')) == '1' else 0
                is_super = 1 if r.get('is_superuser') else 0
                kb_cnt = int(r.get('kb_count') or 0)
                dlg_cnt = int(r.get('dialog_count') or 0)
                tok_cnt = int(r.get('tokens_used') or 0)
                ref_by = (r.get('referred_by_email') or '').strip()
                v_id = (r.get('visitor_id') or '').strip()
                s_id = (r.get('session_id') or '').strip()
                u_src = (r.get('utm_source') or '').strip()
                u_med = (r.get('utm_medium') or '').strip()
                u_cmp = (r.get('utm_campaign') or '').strip()
                u_trm = (r.get('utm_term') or '').strip()
                u_cnt = (r.get('utm_content') or '').strip()

                c_dt = r.get('create_date')
                create_iso = c_dt.replace(tzinfo=datetime.timezone.utc).isoformat() if isinstance(c_dt, datetime.datetime) else utc_now_iso()

                l_dt = r.get('update_date') or r.get('last_login_time') or c_dt
                last_iso = l_dt.replace(tzinfo=datetime.timezone.utc).isoformat() if isinstance(l_dt, datetime.datetime) else create_iso

                scur.execute('SELECT id FROM platform_users WHERE email = ?', (email,))
                existing = scur.fetchone()
                if not existing:
                    scur.execute('''
                        INSERT INTO platform_users (
                            email, nickname, visitor_id, session_id,
                            utm_source, utm_medium, utm_campaign, utm_term, utm_content, referred_by,
                            is_active, is_superuser, knowledgebases_count, dialogs_count, tokens_consumed,
                            last_active_date, create_date
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        email, nickname, v_id, s_id,
                        u_src, u_med, u_cmp, u_trm, u_cnt, ref_by,
                        is_active, is_super, kb_cnt, dlg_cnt, tok_cnt,
                        last_iso, create_iso
                    ))
                else:
                    scur.execute('''
                        UPDATE platform_users SET
                            nickname = COALESCE(NULLIF(?, ''), nickname),
                            visitor_id = COALESCE(NULLIF(?, ''), visitor_id),
                            session_id = COALESCE(NULLIF(?, ''), session_id),
                            utm_source = COALESCE(NULLIF(?, ''), utm_source),
                            utm_medium = COALESCE(NULLIF(?, ''), utm_medium),
                            utm_campaign = COALESCE(NULLIF(?, ''), utm_campaign),
                            utm_term = COALESCE(NULLIF(?, ''), utm_term),
                            utm_content = COALESCE(NULLIF(?, ''), utm_content),
                            referred_by = COALESCE(NULLIF(?, ''), referred_by),
                            is_active = ?,
                            is_superuser = ?,
                            knowledgebases_count = MAX(knowledgebases_count, ?),
                            dialogs_count = MAX(dialogs_count, ?),
                            tokens_consumed = MAX(tokens_consumed, ?),
                            last_active_date = MAX(COALESCE(last_active_date, ''), ?)
                        WHERE id = ?
                    ''', (
                        nickname, v_id, s_id, u_src, u_med, u_cmp, u_trm, u_cnt, ref_by,
                        is_active, is_super, kb_cnt, dlg_cnt, tok_cnt, last_iso, existing[0]
                    ))
            sconn.commit()
    except Exception as e:
        print(f"[PlatformSync] MySQL sync skipped/failed: {e}")


@app.route('/api/platform/events', methods=['POST'])
def track_platform_event():
    """Ingest user lifecycle and activity events from web platform."""
    data = request.json or {}
    email = (data.get('email') or '').strip().lower()
    event_name = (data.get('event_name') or '').strip()
    visitor_id = (data.get('visitor_id') or '').strip()
    session_id = (data.get('session_id') or '').strip()
    meta = data.get('metadata') or {}
    now_iso = utc_now_iso()

    if not event_name:
        return jsonify({"code": 1, "message": "event_name is required"}), 400

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Log raw event
        cursor.execute('''
            INSERT INTO platform_events (email, visitor_id, event_name, metadata, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (email, visitor_id, event_name, json.dumps(meta), now_iso))

        # Handle User registration or user upsert
        if email:
            cursor.execute('SELECT id, knowledgebases_count, dialogs_count, tokens_consumed FROM platform_users WHERE email = ?', (email,))
            existing = cursor.fetchone()

            nickname = (data.get('nickname') or meta.get('nickname') or '').strip()
            utm_source = (data.get('utm_source') or meta.get('utm_source') or '').strip()
            utm_medium = (data.get('utm_medium') or meta.get('utm_medium') or '').strip()
            utm_campaign = (data.get('utm_campaign') or meta.get('utm_campaign') or '').strip()
            utm_term = (data.get('utm_term') or meta.get('utm_term') or '').strip()
            utm_content = (data.get('utm_content') or meta.get('utm_content') or '').strip()
            ref_by = (data.get('ref') or data.get('referred_by') or meta.get('ref') or '').strip()

            if not existing:
                # If utm or visitor_id not in payload, attempt backfilling from visitors table
                if (not utm_source or not utm_campaign) and visitor_id:
                    cursor.execute('SELECT utm_source, utm_medium, utm_campaign, utm_term, utm_content FROM visitors WHERE visitor_id = ? ORDER BY id DESC LIMIT 1', (visitor_id,))
                    v_row = cursor.fetchone()
                    if v_row:
                        utm_source = utm_source or v_row[0] or ''
                        utm_medium = utm_medium or v_row[1] or ''
                        utm_campaign = utm_campaign or v_row[2] or ''
                        utm_term = utm_term or v_row[3] or ''
                        utm_content = utm_content or v_row[4] or ''

                cursor.execute('''
                    INSERT INTO platform_users (
                        email, nickname, visitor_id, session_id,
                        utm_source, utm_medium, utm_campaign, utm_term, utm_content, referred_by,
                        is_active, is_superuser, knowledgebases_count, dialogs_count, tokens_consumed,
                        last_active_date, create_date
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?, ?, ?, ?)
                ''', (
                    email, nickname, visitor_id, session_id,
                    utm_source, utm_medium, utm_campaign, utm_term, utm_content, ref_by,
                    int(meta.get('kb_count') or (1 if event_name in ('create_kb', 'created_kb') else 0)),
                    int(meta.get('dialog_count') or (1 if event_name in ('dialog_created', 'asked_question') else 0)),
                    int(meta.get('tokens') or 0),
                    now_iso, now_iso
                ))
            else:
                u_id, cur_kb, cur_dialogs, cur_tokens = existing
                add_kb = 1 if event_name in ('create_kb', 'created_kb') else int(meta.get('kb_increment') or 0)
                add_dialog = 1 if event_name in ('dialog_created', 'asked_question') else int(meta.get('dialog_increment') or 0)
                add_tokens = int(meta.get('tokens') or 0)

                cursor.execute('''
                    UPDATE platform_users SET
                        last_active_date = ?,
                        knowledgebases_count = knowledgebases_count + ?,
                        dialogs_count = dialogs_count + ?,
                        tokens_consumed = tokens_consumed + ?,
                        is_active = COALESCE(?, is_active),
                        visitor_id = COALESCE(NULLIF(?, ''), visitor_id),
                        utm_source = COALESCE(NULLIF(?, ''), utm_source),
                        utm_campaign = COALESCE(NULLIF(?, ''), utm_campaign),
                        utm_term = COALESCE(NULLIF(?, ''), utm_term),
                        utm_content = COALESCE(NULLIF(?, ''), utm_content)
                    WHERE id = ?
                ''', (
                    now_iso, add_kb, add_dialog, add_tokens,
                    data.get('is_active'), visitor_id, utm_source, utm_campaign, utm_term, utm_content, u_id
                ))

        conn.commit()

    return jsonify({"code": 0, "message": "Event recorded"}), 201


@app.route('/api/platform/users', methods=['GET'])
@admin_required
def get_platform_users():
    """Return all platform users with activity stats and referral links."""
    sync_mysql_platform_users()
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT
                u.*,
                (SELECT COUNT(*) FROM platform_users r WHERE r.referred_by = u.email) AS referrals_count
            FROM platform_users u
            ORDER BY u.id DESC
        ''')
        rows = cursor.fetchall()

    users = [dict(r) for r in rows]
    return jsonify({"code": 0, "data": users})


@app.route('/api/platform/users/<path:email>/activate', methods=['PUT'])
@admin_required
def set_platform_user_status(email):
    """Suspend or activate a user account."""
    data = request.json or {}
    status_str = data.get('activate_status', 'on')
    is_active = 1 if status_str == 'on' else 0

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE platform_users SET is_active = ? WHERE email = ?', (is_active, email))
        conn.commit()

    if DB_FILE.endswith('database.sqlite'):
        try:
            import pymysql
            mconn = pymysql.connect(
                host=os.environ.get('MYSQL_HOST', '127.0.0.1'),
                port=int(os.environ.get('MYSQL_PORT', '5455')),
                user=os.environ.get('MYSQL_USER', 'root'),
                password=os.environ.get('MYSQL_PASSWORD', ''),
                database=os.environ.get('MYSQL_DBNAME', 'rag_flow'),
                connect_timeout=2
            )
            with mconn.cursor() as mcur:
                mcur.execute('UPDATE user SET is_active = %s WHERE email = %s', (str(is_active), email))
            mconn.commit()
            mconn.close()
        except Exception:
            pass

    return jsonify({"code": 0, "message": f"User status updated to {status_str}"})


@app.route('/api/platform/users/<path:email>', methods=['DELETE'])
@admin_required
def delete_platform_user(email):
    """Delete a user account from platform tracker."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM platform_users WHERE email = ?', (email,))
        cursor.execute('DELETE FROM platform_events WHERE email = ?', (email,))
        conn.commit()

    if DB_FILE.endswith('database.sqlite'):
        try:
            import pymysql
            mconn = pymysql.connect(
                host=os.environ.get('MYSQL_HOST', '127.0.0.1'),
                port=int(os.environ.get('MYSQL_PORT', '5455')),
                user=os.environ.get('MYSQL_USER', 'root'),
                password=os.environ.get('MYSQL_PASSWORD', ''),
                database=os.environ.get('MYSQL_DBNAME', 'rag_flow'),
                connect_timeout=2
            )
            with mconn.cursor() as mcur:
                mcur.execute("UPDATE user SET status = '0', is_active = '0' WHERE email = %s", (email,))
            mconn.commit()
            mconn.close()
        except Exception:
            pass

    return jsonify({"code": 0, "message": f"User {email} deleted"})


@app.route('/api/platform/metrics', methods=['GET'])
@admin_required
def get_platform_metrics():
    """Calculate cross-funnel conversion and user retention metrics."""
    sync_mysql_platform_users()
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Total visitors
        cursor.execute('SELECT COUNT(*), COUNT(DISTINCT ip) FROM visitors')
        total_visits, unique_visitors = cursor.fetchone()

        # 2. Total registered platform users
        cursor.execute('SELECT COUNT(*), COUNT(CASE WHEN is_active = 1 THEN 1 END) FROM platform_users')
        total_users, active_accounts = cursor.fetchone()

        # 3. Activation: users who created >= 1 KB or >= 1 Dialog
        cursor.execute('''
            SELECT COUNT(*) FROM platform_users
            WHERE (knowledgebases_count > 0 OR dialogs_count > 0)
        ''')
        activated_users = cursor.fetchone()[0]

        # 4. Active within last 7 days (WAU)
        seven_days_ago = (utc_now() - datetime.timedelta(days=7)).isoformat()
        cursor.execute('SELECT COUNT(*) FROM platform_users WHERE last_active_date >= ?', (seven_days_ago,))
        wau_count = cursor.fetchone()[0]

        # 5. Active within last 24 hours (DAU)
        one_day_ago = (utc_now() - datetime.timedelta(days=1)).isoformat()
        cursor.execute('SELECT COUNT(*) FROM platform_users WHERE last_active_date >= ?', (one_day_ago,))
        dau_count = cursor.fetchone()[0]

        # 6. Usage volume
        cursor.execute('SELECT SUM(knowledgebases_count), SUM(dialogs_count), SUM(tokens_consumed) FROM platform_users')
        sum_kbs, sum_dialogs, sum_tokens = cursor.fetchone()

        # 7. Acquisition Sources breakdown
        cursor.execute('''
            SELECT
                COALESCE(NULLIF(utm_source, ''), 'Direct / Organic') as source,
                COUNT(*) as count
            FROM platform_users
            GROUP BY source
            ORDER BY count DESC
            LIMIT 5
        ''')
        source_rows = cursor.fetchall()
        top_sources = [{"source": r[0], "count": r[1]} for r in source_rows]

    # Rates calculations
    landing_to_signup_rate = round((total_users / unique_visitors * 100), 2) if unique_visitors > 0 else 0.0
    activation_rate = round((activated_users / total_users * 100), 2) if total_users > 0 else 0.0
    stickiness_rate = round((dau_count / wau_count * 100), 1) if wau_count > 0 else 0.0

    return jsonify({
        "code": 0,
        "metrics": {
            "total_visitors": total_visits or 0,
            "unique_visitors": unique_visitors or 0,
            "total_users": total_users or 0,
            "active_accounts": active_accounts or 0,
            "activated_users": activated_users or 0,
            "dau": dau_count or 0,
            "wau": wau_count or 0,
            "landing_to_signup_rate": landing_to_signup_rate,
            "activation_rate": activation_rate,
            "stickiness_rate": stickiness_rate,
            "total_kbs": sum_kbs or 0,
            "total_dialogs": sum_dialogs or 0,
            "total_tokens": sum_tokens or 0,
            "top_sources": top_sources
        }
    })



@app.route('/api/analytics/utm', methods=['GET'])
@admin_required
def get_utm_analytics():
    """Calculate visitor counts, registration conversions, and effectiveness status per UTM campaign."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Fetch visitors with UTM tags
        cursor.execute('''
            SELECT
                COALESCE(NULLIF(utm_source, ''), 'direct') AS source,
                COALESCE(NULLIF(utm_medium, ''), 'none') AS medium,
                COALESCE(NULLIF(utm_campaign, ''), 'unnamed') AS campaign,
                COALESCE(NULLIF(utm_term, ''), '') AS term,
                COALESCE(NULLIF(utm_content, ''), '') AS content,
                visitor_id,
                session_id,
                ip,
                session_duration,
                create_date
            FROM visitors
            WHERE (utm_source IS NOT NULL AND utm_source != '')
               OR (utm_campaign IS NOT NULL AND utm_campaign != '')
            ORDER BY id DESC
        ''')
        visitor_rows = [dict(r) for r in cursor.fetchall()]

        # 2. Fetch all registered platform users
        cursor.execute('''
            SELECT
                id,
                email,
                nickname,
                visitor_id,
                session_id,
                COALESCE(NULLIF(utm_source, ''), 'direct') AS source,
                COALESCE(NULLIF(utm_medium, ''), 'none') AS medium,
                COALESCE(NULLIF(utm_campaign, ''), 'unnamed') AS campaign,
                referred_by,
                is_active,
                knowledgebases_count,
                dialogs_count,
                tokens_consumed,
                create_date
            FROM platform_users
            ORDER BY id DESC
        ''')
        user_rows = [dict(r) for r in cursor.fetchall()]

    campaigns = {}

    for v in visitor_rows:
        src = v['source'].lower()
        med = v['medium'].lower()
        cmp = v['campaign'].lower()
        key = f"{src}::{med}::{cmp}"

        if key not in campaigns:
            campaigns[key] = {
                "source": v['source'],
                "medium": v['medium'],
                "campaign": v['campaign'],
                "visits": 0,
                "unique_visitors": set(),
                "visitor_ids": set(),
                "total_duration": 0,
                "last_visit_date": v.get('create_date') or '',
                "registrations": 0,
                "users": [],
            }

        c = campaigns[key]
        c["visits"] += 1
        c["total_duration"] += (v.get("session_duration") or 0)
        if v.get("ip"):
            c["unique_visitors"].add(v["ip"])
        if v.get("visitor_id"):
            c["visitor_ids"].add(v["visitor_id"])
        if v.get("create_date") and v["create_date"] > c["last_visit_date"]:
            c["last_visit_date"] = v["create_date"]

    for u in user_rows:
        u_src = u['source'].lower()
        u_cmp = u['campaign'].lower()
        u_vid = u.get('visitor_id')

        matched_key = None
        if u_vid:
            for k, c in campaigns.items():
                if u_vid in c["visitor_ids"]:
                    matched_key = k
                    break

        if not matched_key and (u_src != 'direct' or u_cmp != 'unnamed'):
            for k, c in campaigns.items():
                if c["source"].lower() == u_src and c["campaign"].lower() == u_cmp:
                    matched_key = k
                    break

        if not matched_key and (u_src != 'direct' or u_cmp != 'unnamed'):
            matched_key = f"{u_src}::{u['medium'].lower()}::{u_cmp}"
            if matched_key not in campaigns:
                campaigns[matched_key] = {
                    "source": u['source'],
                    "medium": u['medium'],
                    "campaign": u['campaign'],
                    "visits": 1,
                    "unique_visitors": {u['email']},
                    "visitor_ids": {u_vid} if u_vid else set(),
                    "total_duration": 0,
                    "last_visit_date": u.get('create_date') or '',
                    "registrations": 0,
                    "users": [],
                }

        if matched_key and matched_key in campaigns:
            c = campaigns[matched_key]
            c["registrations"] += 1
            c["users"].append({
                "email": u["email"],
                "nickname": u.get("nickname") or "",
                "created_at": u.get("create_date") or "",
                "is_active": u.get("is_active", 1),
                "kbs": u.get("knowledgebases_count", 0),
                "dialogs": u.get("dialogs_count", 0),
            })

    campaign_list = []
    total_utm_visits = 0
    total_unique_visitors = 0
    total_utm_registrations = 0

    for c in campaigns.values():
        unique_cnt = len(c["unique_visitors"]) or max(len(c["visitor_ids"]), 1)
        visits = c["visits"]
        regs = c["registrations"]
        cr = round((regs / unique_cnt * 100), 2) if unique_cnt > 0 else 0.0
        avg_dur = round(c["total_duration"] / visits) if visits > 0 else 0

        if cr >= 10.0 and regs >= 2:
            verdict = "high_performing"
            verdict_text = "🔥 High Performing"
        elif regs > 0:
            verdict = "converting"
            verdict_text = "✅ Converting"
        else:
            verdict = "ineffective"
            verdict_text = "❌ Ineffective (0 signups)"

        total_utm_visits += visits
        total_unique_visitors += unique_cnt
        total_utm_registrations += regs

        campaign_list.append({
            "source": c["source"],
            "medium": c["medium"],
            "campaign": c["campaign"],
            "visits": visits,
            "unique_visitors": unique_cnt,
            "registrations": regs,
            "conversion_rate": cr,
            "avg_duration": avg_dur,
            "last_visit_date": c["last_visit_date"],
            "verdict": verdict,
            "verdict_text": verdict_text,
            "users": c["users"],
        })

    campaign_list.sort(key=lambda x: (x["registrations"], x["conversion_rate"], x["visits"]), reverse=True)
    overall_cr = round((total_utm_registrations / total_unique_visitors * 100), 2) if total_unique_visitors > 0 else 0.0

    converting_campaigns = [c for c in campaign_list if c["registrations"] > 0]
    best_campaign = converting_campaigns[0] if converting_campaigns else None
    ineffective_campaigns = [c for c in campaign_list if c["registrations"] == 0 and c["visits"] >= 1]

    return jsonify({
        "code": 0,
        "summary": {
            "total_utm_visits": total_utm_visits,
            "total_unique_visitors": total_unique_visitors,
            "total_utm_registrations": total_utm_registrations,
            "overall_conversion_rate": overall_cr,
            "total_campaigns_count": len(campaign_list),
            "converting_campaigns_count": len(converting_campaigns),
            "ineffective_campaigns_count": len(ineffective_campaigns),
            "top_campaign": best_campaign["campaign"] if best_campaign else "—",
            "top_source": best_campaign["source"] if best_campaign else "—",
            "top_cr": best_campaign["conversion_rate"] if best_campaign else 0.0,
        },
        "campaigns": campaign_list
    })


DEFAULT_GA_PROPERTY_ID = os.environ.get('GA_PROPERTY_ID', '470471775')
DEFAULT_GA_SERVICE_KEY = os.environ.get('GA_SERVICE_ACCOUNT_KEY', '')


@app.route('/api/analytics/query', methods=['POST'])
@admin_required
def analytics_query():
    data = request.json or {}
    property_id = data.get("property_id") or DEFAULT_GA_PROPERTY_ID
    service_key_str = data.get("service_account_key") or DEFAULT_GA_SERVICE_KEY
    endpoint = data.get("endpoint", "runReport")
    payload = data.get("payload")

    if not property_id or not service_key_str or not payload:
        return jsonify({"code": 1, "message": "Missing required parameters: property_id, service_account_key, and payload are required."}), 400

    try:
        service_account_info = json.loads(service_key_str)
    except Exception:
        return jsonify({"code": 1, "message": "Invalid Service Account JSON key format."}), 400

    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
        import requests

        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/analytics.readonly']
        )
        credentials.refresh(Request())
        access_token = credentials.token

        url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:{endpoint}"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers, timeout=15)

        if not response.ok:
            try:
                err_msg = response.json().get("error", {}).get("message", "Google Analytics API query failed.")
            except Exception:
                err_msg = response.text or "Google Analytics API query failed."
            return jsonify({"code": 1, "message": err_msg}), 400

        return jsonify({"code": 0, "data": response.json()})

    except Exception as e:
        return jsonify({"code": 1, "message": str(e)}), 500


DEFAULT_YM_COUNTER_ID = os.environ.get('YM_COUNTER_ID', '106098534')
DEFAULT_YM_OAUTH_TOKEN = os.environ.get('YM_OAUTH_TOKEN', '')


@app.route('/api/yandex_analytics/query', methods=['POST'])
@admin_required
def yandex_analytics_query():
    data = request.json or {}
    counter_id = data.get("counter_id") or DEFAULT_YM_COUNTER_ID
    oauth_token = data.get("oauth_token") or DEFAULT_YM_OAUTH_TOKEN
    params = data.get("params", {})

    if not counter_id or not oauth_token:
        return jsonify({"code": 1, "message": "Missing required parameters: counter_id and oauth_token are required (configure via environment variables or settings)."}), 400

    try:
        import requests

        url = "https://api-metrika.yandex.net/stat/v1/data"

        headers = {
            "Authorization": f"OAuth {oauth_token}",
            "Accept": "application/json"
        }

        query_params = dict(params)
        query_params["ids"] = counter_id

        response = requests.get(url, params=query_params, headers=headers, timeout=15)

        if not response.ok:
            try:
                err_msg = response.json().get("message", "Yandex Metrika API query failed.")
            except Exception:
                err_msg = response.text or "Yandex Metrika API query failed."
            return jsonify({"code": 1, "message": err_msg}), 400

        return jsonify({"code": 0, "data": response.json()})

    except Exception as e:
        return jsonify({"code": 1, "message": str(e)}), 500




# Factual reports reuse this service's existing verified administrator sessions.
from landing_admin_api import register_admin_analytics
from landing_platform_reports import platform_report

def _reporting_provider_defaults(source):
    if source == "ga":
        return {"property_id": os.environ.get("GA_PROPERTY_ID", "470471775"), "service_account_key": DEFAULT_GA_SERVICE_KEY}
    if source == "ym":
        return {"counter_id": os.environ.get("YM_COUNTER_ID", "106098534"), "oauth_token": DEFAULT_YM_OAUTH_TOKEN}
    return {}

register_admin_analytics(app, DB_FILE, landing_authorizer=get_authenticated_admin,
                         platform_reader=platform_report, provider_defaults=_reporting_provider_defaults)

if __name__ == '__main__':
    init_db()
    print("Server starting on http://127.0.0.1:5005")
    print(f"Database file: {DB_FILE}")
    app.run(host='127.0.0.1', port=5005, debug=False)
