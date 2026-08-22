import sqlite3
import os
import datetime
import urllib.request
import urllib.parse
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# Use absolute path so the DB is found regardless of working directory
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.sqlite')

# Optional Telegram notification (set these env vars on the server to enable)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID   = os.environ.get('TELEGRAM_CHAT_ID', '')


def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
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
                create_date TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS visitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visitor_id TEXT,
                ip TEXT,
                country TEXT,
                city TEXT,
                isp TEXT,
                is_proxy TEXT,
                connection_type TEXT,
                cpu_cores TEXT,
                ram_gb TEXT,
                gpu_info TEXT,
                theme_pref TEXT,
                session_duration INTEGER DEFAULT 0,
                scroll_depth INTEGER DEFAULT 0,
                clicked_buttons TEXT,
                utm_source TEXT,
                utm_medium TEXT,
                utm_campaign TEXT,
                utm_term TEXT,
                utm_content TEXT,
                user_agent TEXT,
                device_type TEXT,
                browser TEXT,
                os TEXT,
                screen_res TEXT,
                language TEXT,
                timezone TEXT,
                page_url TEXT,
                referrer TEXT,
                cookie_consent TEXT,
                create_date TEXT NOT NULL
            )
        ''')

        # Automatic column migration for existing database files
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
            'utm_content': 'TEXT'
        }
        for col_name, col_type in new_cols.items():
            if col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE visitors ADD COLUMN {col_name} {col_type}")

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
        url = f"http://ip-api.com/json/{ip}?fields=status,country,city,isp,org,mobile,proxy,hosting"
        req = urllib.request.Request(url, headers={'User-Agent': 'Swipies-GeoIP/1.0'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            geo_data = json.loads(resp.read().decode('utf-8'))
            if geo_data.get('status') == 'success':
                is_proxy_val = 'Yes' if (geo_data.get('proxy') or geo_data.get('hosting')) else 'No'
                return {
                    'country': geo_data.get('country') or 'Unknown Country',
                    'city': geo_data.get('city') or 'Unknown City',
                    'isp': geo_data.get('isp') or geo_data.get('org') or 'Unknown ISP',
                    'is_proxy': is_proxy_val
                }
    except Exception as e:
        print(f"[GeoIP] Lookup failed for {ip}: {e}")
        
    return {
        'country': 'Unknown Country',
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


@app.route('/api/leads', methods=['POST'])
def create_lead():
    data = request.json or {}
    company       = data.get('company', '')
    name          = data.get('name', '')
    email         = data.get('email', '')
    phone         = data.get('phone', '')
    message       = data.get('message', '')
    referral_code = data.get('referral_code', '')
    create_date   = datetime.datetime.utcnow().isoformat() + "Z"

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO leads (company, name, email, phone, message, referral_code, create_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (company, name, email, phone, message, referral_code, create_date))
        conn.commit()
        lead_id = cursor.lastrowid

    # Notify admin via Telegram
    tg_msg = (
        f"📬 <b>New Lead — Swipies.app</b>\n\n"
        f"👤 <b>Name:</b> {name}\n"
        f"🏢 <b>Company:</b> {company}\n"
        f"📧 <b>Email:</b> {email}\n"
        f"📞 <b>Phone:</b> {phone or '—'}\n"
        f"💬 <b>Message:</b> {message or '—'}\n"
        f"🔗 <b>Ref Code:</b> {referral_code or '—'}\n"
        f"🕐 <b>Time (UTC):</b> {create_date}"
    )
    send_telegram(tg_msg)

    return jsonify({"code": 0, "message": "Success", "data": {"id": lead_id}}), 201


@app.route('/api/leads', methods=['GET'])
def get_leads():
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM leads ORDER BY id DESC')
        rows = cursor.fetchall()

    leads = [dict(row) for row in rows]
    return jsonify({"code": 0, "data": leads})


@app.route('/api/leads/<int:lead_id>', methods=['PUT'])
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
def delete_lead(lead_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM leads WHERE id = ?', (lead_id,))
        conn.commit()

    return jsonify({"code": 0, "message": "Deleted"})


@app.route('/api/visitors', methods=['POST'])
def track_visitor():
    data = request.json or {}
    
    # Extract client IP accurately
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        ip = request.headers.get('X-Real-IP').strip()
    else:
        ip = request.remote_addr or '127.0.0.1'

    user_agent = request.headers.get('User-Agent', '') or data.get('user_agent', '')
    visitor_id = data.get('visitor_id', '')
    screen_res = data.get('screen_res', '')
    language = data.get('language', '')
    timezone = data.get('timezone', '')
    page_url = data.get('page_url', '')
    referrer = data.get('referrer', '')
    cookie_consent = data.get('cookie_consent', 'accepted')

    # Extended metrics & UTM params
    connection_type = data.get('connection_type', '')
    cpu_cores       = str(data.get('cpu_cores', '')) if data.get('cpu_cores') else ''
    ram_gb          = str(data.get('ram_gb', '')) if data.get('ram_gb') else ''
    gpu_info        = data.get('gpu_info', '')
    theme_pref      = data.get('theme_pref', '')
    session_duration = int(data.get('session_duration', 0) or 0)
    scroll_depth    = int(data.get('scroll_depth', 0) or 0)
    clicked_buttons = data.get('clicked_buttons', '')
    if isinstance(clicked_buttons, list):
        clicked_buttons = ", ".join(clicked_buttons)

    utm_source   = data.get('utm_source', '')
    utm_medium   = data.get('utm_medium', '')
    utm_campaign = data.get('utm_campaign', '')
    utm_term     = data.get('utm_term', '')
    utm_content  = data.get('utm_content', '')

    create_date = datetime.datetime.utcnow().isoformat() + "Z"
    
    parsed_ua = parse_user_agent(user_agent)
    device_type = parsed_ua['device']
    browser = parsed_ua['browser']
    os_name = parsed_ua['os']

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # Check if visitor entry already exists for session update
        existing_row = None
        if visitor_id:
            cursor.execute('SELECT id, country, city, isp, is_proxy, clicked_buttons, scroll_depth, session_duration FROM visitors WHERE visitor_id = ? ORDER BY id DESC LIMIT 1', (visitor_id,))
            existing_row = cursor.fetchone()

        if existing_row:
            v_id, country, city, isp, is_proxy, old_clicks, old_scroll, old_dur = existing_row
            
            # Merge clicked buttons
            new_clicks_list = [c.strip() for c in (clicked_buttons or '').split(',') if c.strip()]
            old_clicks_list = [c.strip() for c in (old_clicks or '').split(',') if c.strip()]
            merged_clicks = ", ".join(dict.fromkeys(old_clicks_list + new_clicks_list))

            new_scroll = max(scroll_depth, old_scroll or 0)
            new_duration = max(session_duration, old_dur or 0)

            cursor.execute('''
                UPDATE visitors SET
                    cookie_consent = ?,
                    connection_type = ?,
                    cpu_cores = ?,
                    ram_gb = ?,
                    gpu_info = ?,
                    theme_pref = ?,
                    session_duration = ?,
                    scroll_depth = ?,
                    clicked_buttons = ?,
                    utm_source = COALESCE(NULLIF(?, ''), utm_source),
                    utm_medium = COALESCE(NULLIF(?, ''), utm_medium),
                    utm_campaign = COALESCE(NULLIF(?, ''), utm_campaign),
                    utm_term = COALESCE(NULLIF(?, ''), utm_term),
                    utm_content = COALESCE(NULLIF(?, ''), utm_content),
                    screen_res = ?,
                    language = ?
                WHERE id = ?
            ''', (
                cookie_consent, connection_type, cpu_cores, ram_gb, gpu_info, theme_pref,
                new_duration, new_scroll, merged_clicks,
                utm_source, utm_medium, utm_campaign, utm_term, utm_content,
                screen_res, language, v_id
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
                    visitor_id, ip, country, city, isp, is_proxy, connection_type,
                    cpu_cores, ram_gb, gpu_info, theme_pref, session_duration, scroll_depth,
                    clicked_buttons, utm_source, utm_medium, utm_campaign, utm_term, utm_content,
                    user_agent, device_type, browser, os, screen_res,
                    language, timezone, page_url, referrer, cookie_consent, create_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                visitor_id, ip, country, city, isp, is_proxy, connection_type,
                cpu_cores, ram_gb, gpu_info, theme_pref, session_duration, scroll_depth,
                clicked_buttons, utm_source, utm_medium, utm_campaign, utm_term, utm_content,
                user_agent, device_type, browser, os_name, screen_res,
                language, timezone, page_url, referrer, cookie_consent, create_date
            ))
            conn.commit()
            v_id = cursor.lastrowid

            # Telegram notification for brand new visitor
            tg_msg = (
                f"👁️ <b>New Site Visitor — Swipies.app</b>\n\n"
                f"🌐 <b>IP:</b> {ip} ({country}, {city})\n"
                f"🏢 <b>ISP:</b> {isp} (VPN/Proxy: {is_proxy})\n"
                f"📱 <b>Device:</b> {device_type} ({os_name} / {browser})\n"
                f"💻 <b>Hardware:</b> CPU: {cpu_cores or '?'} cores | RAM: {ram_gb or '?'} GB | GPU: {gpu_info or 'Unknown'}\n"
                f"⚡ <b>Net & Theme:</b> {connection_type or 'Standard'} | {theme_pref or 'Default'}\n"
                f"🖥️ <b>Screen:</b> {screen_res or 'Unknown'}\n"
                f"🌍 <b>Timezone:</b> {timezone or '—'} | <b>Lang:</b> {language or '—'}\n"
                f"🔗 <b>Page:</b> {page_url or '/'}\n"
                f"📍 <b>Referrer:</b> {referrer or 'Direct'}\n"
                f"🍪 <b>Cookie Consent:</b> {cookie_consent.upper()}\n"
                f"🕐 <b>Time (UTC):</b> {create_date}"
            )
            send_telegram(tg_msg)

            return jsonify({"code": 0, "message": "Visitor tracked", "data": {"id": v_id}}), 201


@app.route('/api/visitors', methods=['GET'])
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
            "avg_duration": avg_duration,
            "avg_scroll": avg_scroll
        }
    })


@app.route('/api/visitors/<int:v_id>', methods=['DELETE'])
def delete_visitor(v_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM visitors WHERE id = ?', (v_id,))
        conn.commit()

    return jsonify({"code": 0, "message": "Visitor record deleted"})


@app.route('/api/visitors/clear', methods=['DELETE'])
def clear_visitors():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM visitors')
        conn.commit()

    return jsonify({"code": 0, "message": "All visitor records cleared"})



@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"code": 0, "status": "ok", "db": DB_FILE})


@app.route('/api/analytics/query', methods=['POST'])
def analytics_query():
    data = request.json or {}
    property_id = data.get("property_id")
    service_key_str = data.get("service_account_key")
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


DEFAULT_YM_COUNTER_ID = '106098534'
DEFAULT_YM_OAUTH_TOKEN = 'y0__wgBELnapf8GGITgRSDb2K6tGONdSMrx_H9z1BiPLXe2H5x89ro3'


@app.route('/api/yandex_analytics/query', methods=['POST'])
def yandex_analytics_query():
    data = request.json or {}
    counter_id = data.get("counter_id") or DEFAULT_YM_COUNTER_ID
    oauth_token = data.get("oauth_token") or DEFAULT_YM_OAUTH_TOKEN
    params = data.get("params", {})
    
    if not counter_id or not oauth_token:
        return jsonify({"code": 1, "message": "Missing required parameters: counter_id and oauth_token are required."}), 400
        
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



if __name__ == '__main__':
    init_db()
    print(f"Server starting on http://127.0.0.1:5005")
    print(f"Database file: {DB_FILE}")
    app.run(host='127.0.0.1', port=5005, debug=False)
