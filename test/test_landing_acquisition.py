"""Acquisition boundaries, actual handoff semantics, private reports. No network."""
import importlib.util
import sqlite3
import uuid
from functools import wraps
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from flask import Flask, jsonify, request

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'new site for swipies'
if not SITE.exists():
    SITE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('landing_acquisition', SITE / 'landing_acquisition.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def client():
    # Avoid pytest's chmod(0700) temporary directory on managed Windows ACLs.
    tmp_path = Path.cwd() / 'work' / 'acquisition-test-data' / uuid.uuid4().hex
    tmp_path.mkdir(parents=True)
    app = Flask(__name__)
    def identity(req):
        return 'owner' if req.headers.get('Authorization') == 'Bearer test-admin' else None
    def required(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            return fn(*args, **kwargs) if identity(request) else (jsonify(code=401), 401)
        return wrapped
    app.config['USERS'] = {}
    def reader(ids):
        if app.config.get('UNAVAILABLE'):
            raise RuntimeError('private-credential-must-not-leak')
        return {vid: app.config['USERS'][vid] for vid in ids if vid in app.config['USERS']}
    module.register_acquisition(app, tmp_path / 'database.sqlite', admin_required=required,
                                admin_identity=identity, user_reader=reader, assets=SITE)
    return app.test_client()


AUTH = {'Authorization': 'Bearer test-admin'}


def activate(client, slug='sales'):
    return client.post('/api/admin/acquisition/landings', headers=AUTH,
        json=dict(slug=slug, name='Продажи', url=f'https://{slug}.swipies.app/', active=True))


def campaign(client, slug='sales'):
    response = client.post('/api/admin/acquisition/campaigns', headers=AUTH,
        json=dict(landing=slug, name='Тест', utm_source='telegram', utm_medium='paid social',
                  utm_campaign='Продажи & рост', utm_content='видео/1', utm_term=''))
    assert response.status_code == 200
    return response.json['data'][0]


def test_private_routes_and_revocable_page_access(client):
    for path in ['landings', 'campaigns', 'report']:
        assert client.get('/api/admin/acquisition/' + path).status_code == 401
    assert client.post('/api/admin/acquisition/open').status_code == 401
    assert client.get('/admin/acquisition').status_code == 302
    response = client.post('/api/admin/acquisition/open', headers=AUTH)
    cookie = response.headers['Set-Cookie']
    assert 'HttpOnly' in cookie and 'Secure' in cookie and 'SameSite=Strict' in cookie
    with client.get('/admin/acquisition', base_url='https://localhost') as page:
        assert page.status_code == 200
    client.set_cookie('swipies_acquisition_admin', 'revoked', secure=True, path='/admin/acquisition')
    assert client.get('/admin/acquisition', base_url='https://localhost').status_code == 302


def test_defaults_are_planned_and_main_domain_is_absent(client):
    rows = client.get('/api/admin/acquisition/landings', headers=AUTH).json['data']
    assert len(rows) == 9 and not any(r['active'] for r in rows)
    assert all(r['url'] != 'https://swipies.app/' for r in rows)
    assert client.get('/api/acquisition/go/sales').status_code == 404


@pytest.mark.parametrize('url', ['https://evil.com/', 'https://sales.swipies.app.evil.com/',
    'https://api.swipies.app/', 'https://swipies.app/', 'http://sales.swipies.app/',
    'https://user:pass@sales.swipies.app/', 'https://sales.swipies.app:443/',
    'https://sales.swipies.app/?token=x', 'https://sales.swipies.app/#x'])
def test_reject_redirect_targets_outside_landing_registry(client, url):
    assert client.post('/api/admin/acquisition/landings', headers=AUTH,
        json=dict(slug='custom', name='Custom', url=url)).status_code == 400


def test_campaign_encoding_and_server_owned_tags(client):
    activate(client)
    c = campaign(client)
    query = parse_qs(urlsplit(c['url']).query)
    assert query['utm_campaign'] == ['Продажи & рост']
    response = client.get('/api/acquisition/go/sales', query_string=dict(sw_campaign=c['id'], utm_source='forged', next='https://evil.com'))
    assert response.status_code == 302
    target = urlsplit(response.location)
    assert target.netloc == 'api.swipies.app' and target.path == '/login'
    q = parse_qs(target.query)
    assert q['utm_source'] == ['telegram'] and q['vid'][0].startswith('acq_')
    assert response.headers['Cache-Control'] == 'no-store'
    assert response.headers['Referrer-Policy'] == 'no-referrer'


def test_campaign_cannot_be_attached_to_other_landing(client):
    activate(client); activate(client, 'support')
    c = campaign(client)
    assert client.get('/api/acquisition/go/support', query_string={'sw_campaign':c['id']}).status_code == 400
    assert client.get('/api/admin/acquisition/report', headers=AUTH).json['data']['total'] == 0


def test_report_matches_verified_account_without_inventing_registration(client):
    activate(client)
    first = client.get('/api/acquisition/go/sales?utm_source=telegram')
    vid = parse_qs(urlsplit(first.location).query)['vid'][0]
    client.get('/api/acquisition/go/sales')
    client.application.config['USERS'][vid] = [dict(email='person@example.test', nickname='Person')]
    data = client.get('/api/admin/acquisition/report?landing=sales', headers=AUTH).json['data']
    assert data['total'] == 2 and data['summary'] == [dict(landing='sales',transitions=2)]
    assert sum(bool(r['accounts']) for r in data['rows']) == 1
    assert data['accounts_status'] == 'ready'
    client.application.config['UNAVAILABLE'] = True
    response = client.get('/api/admin/acquisition/report', headers=AUTH)
    assert response.json['data']['accounts_status'] == 'unavailable'
    assert b'private-credential' not in response.data


def test_period_filters_and_pagination(client):
    activate(client)
    for _ in range(3): client.get('/api/acquisition/go/sales')
    data = client.get('/api/admin/acquisition/report?page=2', headers=AUTH).json['data']
    assert data['total'] == 3 and data['rows'] == []
    assert client.get('/api/admin/acquisition/report?start=2020-01-01T00:00:00%2B00:00&end=2020-01-02T00:00:00%2B00:00', headers=AUTH).json['data']['total'] == 0
    for params in ['page=0', 'page=abc', 'start=bad', 'start=2026-01-01',
                   'start=2020-01-01T00:00:00%2B00:00&end=2026-01-01T00:00:00%2B00:00']:
        assert client.get('/api/admin/acquisition/report?' + params, headers=AUTH).status_code == 400


def test_bad_payload_and_active_status(client):
    assert client.post('/api/admin/acquisition/landings', headers=AUTH, json=[]).status_code == 400
    assert client.post('/api/admin/acquisition/campaigns', headers=AUTH, json=dict(landing='sales')).status_code == 400
    activate(client)
    assert client.post('/api/admin/acquisition/landings', headers=AUTH,
        json=dict(slug='sales',name='Sales',url='https://another.swipies.app/',active=True)).status_code == 400
    client.post('/api/admin/acquisition/landings', headers=AUTH,
        json=dict(slug='sales',name='Sales',url='https://sales.swipies.app/',active=False))
    assert client.get('/api/acquisition/go/sales').status_code == 404


def test_handoff_rate_limit(client):
    activate(client)
    for _ in range(60): assert client.get('/api/acquisition/go/sales').status_code == 302
    assert client.get('/api/acquisition/go/sales').status_code == 429
