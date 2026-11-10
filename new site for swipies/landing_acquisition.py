"""Independent multi-landing campaign links and platform handoff reporting."""
import datetime as dt
import re
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode, urlsplit

from flask import jsonify, redirect, request, send_file

UTM = ('utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content')
ORIGIN = 'https://swipies.app'
PLATFORM = 'https://api.swipies.app/login'
DEFAULTS = {
    'sales': 'ИИ-продавец', 'support': 'Поддержка клиентов',
    'knowledge': 'Помощник по документам', 'booking': 'Запись на услуги',
    'education': 'Учебные центры', 'realty': 'Недвижимость',
    'hr': 'Помощник HR', 'operations': 'CRM и ERP', 'enterprise': 'Для компаний',
}


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def text(value, maximum=160):
    if not isinstance(value, str) or len(value) > maximum or any(ord(c) < 32 for c in value):
        raise ValueError('Некорректное или слишком длинное значение.')
    return value.strip()


def landing_url(value):
    value = text(value, 500)
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port
            or not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.swipies\.app', parsed.netloc)
            or parsed.hostname.split('.')[0] in {'api', 'app', 'www', 'ads'}
            or parsed.query or parsed.fragment):
        raise ValueError('Укажите HTTPS-адрес отдельного поддомена Swipies без параметров.')
    return value.rstrip('/') + '/' if parsed.path in ('', '/') else value


def verified_users(visitor_ids):
    """Use persisted accounts, never the public legacy lifecycle endpoint."""
    if not visitor_ids:
        return {}
    from landing_platform_reports import connection
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute(
            'SELECT visitor_id,email,nickname,create_time FROM user WHERE visitor_id IN ('
            + ','.join(['%s'] * len(visitor_ids)) + ') AND status = %s',
            [*visitor_ids, '1'],
        )
        result = {}
        for row in cursor.fetchall():
            result.setdefault(row['visitor_id'], []).append(dict(row))
        return result


def register_acquisition(app, database, *, admin_required, admin_identity,
                         user_reader=verified_users, assets=None, client_ip=None):
    assets = Path(assets or Path(__file__).parent)
    state = Path(database).with_name('acquisition-state.sqlite')

    @contextmanager
    def db():
        conn = sqlite3.connect(state, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS acquisition_landings (
                    slug TEXT PRIMARY KEY, name TEXT NOT NULL, url TEXT UNIQUE NOT NULL,
                    active INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS acquisition_campaigns (
                    id TEXT PRIMARY KEY, landing TEXT NOT NULL, name TEXT NOT NULL,
                    utm_source TEXT NOT NULL, utm_medium TEXT NOT NULL,
                    utm_campaign TEXT NOT NULL, utm_term TEXT NOT NULL,
                    utm_content TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS acquisition_transitions (
                    id INTEGER PRIMARY KEY, landing TEXT NOT NULL, campaign_id TEXT,
                    visitor_id TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL,
                    utm_source TEXT NOT NULL, utm_medium TEXT NOT NULL,
                    utm_campaign TEXT NOT NULL, utm_term TEXT NOT NULL, utm_content TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS acquisition_period ON acquisition_transitions(created_at,landing);
            ''')
            conn.executemany(
                'INSERT OR IGNORE INTO acquisition_landings VALUES (?,?,?,0)',
                [(slug, name, f'https://{slug}.swipies.app/') for slug, name in DEFAULTS.items()],
            )
            yield conn
            conn.commit()
        finally:
            conn.close()

    def payload():
        raw = request.get_json(silent=True) if request.content_length and request.content_length <= 4096 else None
        if not isinstance(raw, dict):
            raise ValueError('Нужен JSON-объект размером до 4 KiB.')
        return raw

    def campaign_link(row, url):
        query = [(k, row[k]) for k in UTM if row[k]]
        query.append(('sw_campaign', row['id']))
        return url + ('&' if '?' in url else '?') + urlencode(query)

    @app.after_request
    def acquisition_headers(response):
        if request.path.startswith(('/api/admin/acquisition/', '/api/acquisition/', '/admin/acquisition')):
            response.headers['Cache-Control'] = 'no-store'
            response.headers['Referrer-Policy'] = 'no-referrer'
            response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.get('/admin/acquisition')
    def acquisition_page():
        token = request.cookies.get('swipies_acquisition_admin', '')
        if not token or len(token) > 8192 or not admin_identity(SimpleNamespace(headers={'Authorization': 'Bearer ' + token})):
            return redirect('/admin.html')
        return send_file(assets / 'acquisition.html')

    @app.post('/api/admin/acquisition/open')
    @admin_required
    def acquisition_open():
        raw = request.headers.get('Authorization', '')
        if not raw.startswith('Bearer ') or len(raw) > 8192:
            return jsonify(code=401, message='Войдите в админку.'), 401
        response = jsonify(code=0)
        response.set_cookie('swipies_acquisition_admin', raw[7:], max_age=300,
                            secure=True, httponly=True, samesite='Strict', path='/admin/acquisition')
        return response

    @app.route('/api/admin/acquisition/landings', methods=['GET', 'POST'])
    @admin_required
    def acquisition_landings():
        try:
            with db() as conn:
                if request.method == 'POST':
                    data = payload()
                    slug = text(data.get('slug', ''), 64)
                    if not re.fullmatch(r'[a-z][a-z0-9-]{0,63}', slug):
                        raise ValueError('Код лендинга: латинские буквы, цифры и дефис.')
                    name = text(data.get('name', ''))
                    if not name or not isinstance(data.get('active', False), bool):
                        raise ValueError('Заполните название и статус.')
                    url = landing_url(data.get('url', ''))
                    previous = conn.execute('SELECT url FROM acquisition_landings WHERE slug=?', (slug,)).fetchone()
                    if previous and previous['url'] != url:
                        raise ValueError('Для другого адреса создайте отдельный код лендинга.')
                    conn.execute('''INSERT INTO acquisition_landings VALUES (?,?,?,?)
                        ON CONFLICT(slug) DO UPDATE SET name=excluded.name,active=excluded.active''',
                        (slug, name, url, int(data.get('active', False))))
                rows = [dict(r) for r in conn.execute('SELECT * FROM acquisition_landings ORDER BY slug')]
            return jsonify(code=0, data=rows)
        except (ValueError, sqlite3.IntegrityError):
            return jsonify(code=1, message='Проверьте код, название и уникальный HTTPS-адрес поддомена. Адрес существующего кода изменить нельзя.'), 400

    @app.route('/api/admin/acquisition/campaigns', methods=['GET', 'POST'])
    @admin_required
    def acquisition_campaigns():
        try:
            with db() as conn:
                if request.method == 'POST':
                    data = payload()
                    slug = text(data.get('landing', ''), 64)
                    if not conn.execute('SELECT 1 FROM acquisition_landings WHERE slug=?', (slug,)).fetchone():
                        raise ValueError('Выберите лендинг.')
                    tags = [text(data.get(k, '')) for k in UTM]
                    if not all(tags[:3]):
                        raise ValueError('Заполните source, medium и campaign.')
                    conn.execute('INSERT INTO acquisition_campaigns VALUES (?,?,?,?,?,?,?,?,?)',
                                 (secrets.token_urlsafe(12), slug, text(data.get('name', '')) or tags[2], *tags, now()))
                slug = text(request.args.get('landing', ''), 64)
                rows = conn.execute('''SELECT c.*,l.url,l.active FROM acquisition_campaigns c
                    JOIN acquisition_landings l ON l.slug=c.landing WHERE (?='' OR c.landing=?)
                    ORDER BY c.created_at DESC LIMIT 501''', (slug, slug)).fetchall()
                if len(rows) > 500:
                    raise ValueError('Более 500 ссылок. Выберите отдельный лендинг.')
                result = []
                for row in rows:
                    item = dict(row)
                    item['url'] = campaign_link(row, row['url'])
                    item['handoff_url'] = ORIGIN + '/api/acquisition/go/' + row['landing'] + '?sw_campaign=' + row['id']
                    result.append(item)
            return jsonify(code=0, data=result)
        except ValueError as error:
            return jsonify(code=1, message=str(error)), 400

    @app.get('/api/acquisition/go/<slug>')
    def acquisition_go(slug):
        # This records the redirect itself, not a registration or a unique person.
        if len(request.query_string) > 2048:
            return jsonify(code=1, message='Слишком длинная ссылка.'), 400
        limiter = app.config.setdefault('ACQUISITION_LIMITER', {})
        import time
        import threading
        lock = app.config.setdefault('ACQUISITION_LIMIT_LOCK', threading.Lock())
        address = client_ip() if client_ip else request.remote_addr or ''
        with lock:
            tick = int(time.monotonic() // 60)
            for key in list(limiter):
                if limiter[key][0] != tick:
                    del limiter[key]
            count = limiter.get(address, (tick, 0))[1]
            if count >= 60 or len(limiter) >= 10000:
                return jsonify(code=429, message='Повторите через минуту.'), 429
            limiter[address] = (tick, count + 1)
        try:
            with db() as conn:
                landing = conn.execute('SELECT * FROM acquisition_landings WHERE slug=? AND active=1', (slug,)).fetchone()
                if not landing:
                    return jsonify(code=404, message='Лендинг не активирован.'), 404
                campaign_id = text(request.args.get('sw_campaign', ''), 64)
                campaign = conn.execute('SELECT * FROM acquisition_campaigns WHERE id=? AND landing=?',
                                        (campaign_id, slug)).fetchone() if campaign_id else None
                if campaign_id and not campaign:
                    raise ValueError('Кампания не принадлежит этому лендингу.')
                tags = {k: campaign[k] if campaign else text(request.args.get(k, '')) for k in UTM}
                visitor = 'acq_' + secrets.token_urlsafe(24)
                conn.execute('''INSERT INTO acquisition_transitions
                    (landing,campaign_id,visitor_id,created_at,utm_source,utm_medium,utm_campaign,utm_term,utm_content)
                    VALUES (?,?,?,?,?,?,?,?,?)''', (slug, campaign_id or None, visitor, now(), *tags.values()))
            return redirect(PLATFORM + '?' + urlencode({'vid': visitor, **tags}), code=302)
        except ValueError as error:
            return jsonify(code=1, message=str(error)), 400

    @app.get('/api/admin/acquisition/report')
    @admin_required
    def acquisition_report():
        try:
            end = dt.datetime.fromisoformat(request.args.get('end') or now())
            start = dt.datetime.fromisoformat(request.args.get('start') or (end - dt.timedelta(days=30)).isoformat())
            if not start.tzinfo or not end.tzinfo or not start < end or end - start > dt.timedelta(days=366):
                raise ValueError('Укажите период до 366 дней с часовым поясом.')
            slug = text(request.args.get('landing', ''), 64)
            campaign = text(request.args.get('campaign', ''), 64)
            page = int(request.args.get('page', '1'))
            if not 1 <= page <= 100000:
                raise ValueError('Некорректная страница.')
            where = "created_at>=? AND created_at<? AND (?='' OR landing=?) AND (?='' OR campaign_id=?)"
            values = (start.astimezone(dt.timezone.utc).isoformat(), end.astimezone(dt.timezone.utc).isoformat(), slug, slug, campaign, campaign)
            with db() as conn:
                total = conn.execute('SELECT count(*) FROM acquisition_transitions WHERE ' + where, values).fetchone()[0]
                summary = [dict(r) for r in conn.execute('SELECT landing,count(*) AS transitions FROM acquisition_transitions WHERE ' + where + ' GROUP BY landing ORDER BY transitions DESC', values)]
                rows = [dict(r) for r in conn.execute('SELECT * FROM acquisition_transitions WHERE ' + where + ' ORDER BY created_at DESC,id DESC LIMIT 100 OFFSET ?', (*values, (page-1)*100))]
            try:
                users = user_reader([r['visitor_id'] for r in rows])
                status = 'ready'
            except Exception:
                users, status = {}, 'unavailable'
            for row in rows:
                row['accounts'] = users.get(row['visitor_id'], [])
            return jsonify(code=0, data=dict(rows=rows, total=total, page=page, page_size=100,
                           summary=summary, accounts_status=status))
        except (ValueError, OverflowError):
            return jsonify(code=1, message='Проверьте период, фильтры и номер страницы.'), 400
