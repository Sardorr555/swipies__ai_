"""Test landing_slug attribution, lead validation, anti-spoofing, and database migration."""
import importlib.util
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'new site for swipies'
sys.path.insert(0, str(SITE))

spec = importlib.util.spec_from_file_location('api_module', SITE / 'api.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)

pytestmark = [
    pytest.mark.filterwarnings("ignore::ResourceWarning"),
    pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
]

@pytest.fixture(autouse=True)
def isolated_app(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False)
    tmp.close()
    db_path = tmp.name
    monkeypatch.setattr(api, 'DB_FILE', db_path)
    # Silence telegram in tests
    monkeypatch.setattr(api, 'send_telegram', lambda msg: True)
    api.clear_rate_limits()
    api.init_db()
    client = api.app.test_client()
    yield client, db_path
    import gc
    gc.collect()
    try:
        Path(db_path).unlink(missing_ok=True)
    except Exception:
        pass

def test_resolve_landing_slug_direct():
    # Direct function testing
    class FakeReq:
        def __init__(self, host, x_host=None):
            self.host = host
            self.headers = {'X-Forwarded-Host': x_host} if x_host else {}

    # Matching subdomains
    slug, err = api.resolve_landing_slug(FakeReq('sales.swipies.app'), 'sales')
    assert slug == 'sales' and err is None

    # Omitted payload slug with matching host
    slug, err = api.resolve_landing_slug(FakeReq('support.swipies.app'), None)
    assert slug == 'support' and err is None

    # Spoofed landing slug (e.g. host is sales.swipies.app, payload claims knowledge)
    slug, err = api.resolve_landing_slug(FakeReq('sales.swipies.app'), 'knowledge')
    assert err is not None
    assert 'mismatch' in err

    # Main domain swipies.app defaults to b2c
    slug, err = api.resolve_landing_slug(FakeReq('swipies.app'), None)
    assert slug == 'b2c' and err is None

    # Enterprise subdomain
    slug, err = api.resolve_landing_slug(FakeReq('enterprise.swipies.app'), 'enterprise')
    assert slug == 'enterprise' and err is None

    # Invalid slug name rejected
    slug, err = api.resolve_landing_slug(FakeReq('127.0.0.1:5005'), 'evil_landing')
    assert err is not None

def test_create_lead_with_landing_slug(isolated_app):
    client, db_path = isolated_app

    # 1. Post to sales.swipies.app
    res = client.post(
        '/api/leads',
        headers={'Host': 'sales.swipies.app'},
        json={
            'name': 'Aziz Karimov',
            'email': 'aziz@example.com',
            'phone': '+998901234567',
            'company': 'Retail Pro',
            'message': 'Интересует ИИ-продавец',
            'landing_slug': 'sales'
        }
    )
    assert res.status_code == 201
    body = res.get_json()
    assert body['code'] == 0
    assert body['data']['landing_slug'] == 'sales'
    assert body['data']['source'] == 'b2c'

    # 2. Check SQLite record
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT * FROM leads WHERE id = ?', (body['data']['id'],))
        row = cur.fetchone()
        assert row['name'] == 'Aziz Karimov'
        assert row['landing_slug'] == 'sales'
        assert row['source'] == 'b2c'

def test_create_lead_phone_only_no_email(isolated_app):
    client, db_path = isolated_app

    res = client.post(
        '/api/contact',
        headers={'Host': 'support.swipies.app'},
        json={
            'name': 'Malika Karimova',
            'phone': '+998909876543',
            'landing_slug': 'support'
        }
    )
    assert res.status_code == 201
    body = res.get_json()
    assert body['code'] == 0
    assert body['data']['landing_slug'] == 'support'

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT * FROM leads WHERE id = ?', (body['data']['id'],))
        row = cur.fetchone()
        assert row['name'] == 'Malika Karimova'
        assert row['phone'] == '+998909876543'
        assert row['email'] == ''
        assert row['landing_slug'] == 'support'

def test_create_lead_rejects_missing_both_contacts(isolated_app):
    client, db_path = isolated_app

    res = client.post(
        '/api/leads',
        headers={'Host': 'knowledge.swipies.app'},
        json={
            'name': 'No Contact Person'
        }
    )
    assert res.status_code == 400
    assert 'contact method' in res.get_json()['message'].lower()

def test_create_lead_rejects_spoofed_slug(isolated_app):
    client, db_path = isolated_app

    res = client.post(
        '/api/leads',
        headers={'Host': 'sales.swipies.app'},
        json={
            'name': 'Hacker',
            'email': 'hacker@example.com',
            'landing_slug': 'support'  # mismatch with Host sales.swipies.app!
        }
    )
    assert res.status_code == 400
    assert 'mismatch' in res.get_json()['message'].lower()

def test_legacy_leads_migration_and_retrieval(isolated_app):
    client, db_path = isolated_app

    # Insert a legacy lead with NULL landing_slug
    with sqlite3.connect(db_path) as conn:
        conn.execute('''
            INSERT INTO leads (company, name, email, phone, message, referral_code, status, source, landing_slug, create_date)
            VALUES ('Old Corp', 'Legacy User', 'old@example.com', '', 'Old message', '', '1', 'b2c', NULL, '2026-01-01T00:00:00Z')
        ''')
        conn.commit()

    # Login admin to fetch leads
    with sqlite3.connect(db_path) as conn:
        token = 'test_admin_token_123'
        conn.execute('''
            INSERT INTO admin_sessions (token, username, created_at, expires_at)
            VALUES (?, 'admin', '2026-01-01T00:00:00Z', '2030-01-01T00:00:00Z')
        ''', (token,))
        conn.commit()

    res = client.get('/api/leads', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    data = res.get_json()['data']
    assert len(data) >= 1
    legacy_lead = [d for d in data if d['name'] == 'Legacy User'][0]
    assert legacy_lead['landing_slug'] == ''
