"""Deployment compatibility with the existing protected landing service."""
from contextlib import contextmanager, closing
from io import BytesIO
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace, ModuleType
from urllib.parse import urlencode

from flask import Flask
import openpyxl
import pytest

from test.test_landing_admin_reporting import (
    BASE, SITE, core, adapter, load, models, web,
    test_real_models_deduplicate_mirrors_and_exclude_ads as seed_and_check_models,
)

sql = load(SITE/'landing_platform_reports.py','landing_platform_reports')


def test_native_session_auth_and_revocation_preserves_platform_denial(web):
    flags={'valid':True}
    calls=[]
    def platform(path,*args,**kwargs):
        return 401, {'code':1}, {}
    def reader(path):
        calls.append(path)
        from urllib.parse import parse_qs,urlsplit
        params={key:value[0] for key,value in parse_qs(urlsplit(path).query).items()}
        f=core.Filters.parse(params)
        return core.assemble(f,core.platform_period(f.current,f,[],[]),core.platform_period(f.previous,f,[],[]),'platform')
    app=Flask(__name__);app.testing=True
    adapter.register_admin_analytics(app,web.path,platform,
        landing_authorizer=lambda req: flags['valid'] and req.headers.get('Authorization')=='Bearer native-test',
        platform_reader=reader)
    client=app.test_client()
    def report():return client.post('/api/admin/analytics/report',headers={'Authorization':'Bearer native-test'},json={'filters':BASE})
    response=report()
    assert response.status_code==200 and response.json['data']['current']['totals']['visits']==605
    assert calls and response.headers['Cache-Control']=='no-store'
    flags['valid']=False
    # The injected upstream deliberately rejects every other identity; no local
    # session flag or prior successful report grants continuing access.
    assert report().status_code==403
    assert len(calls)==1
    assert client.post('/api/admin/analytics/report',json={'filters':BASE}).status_code==401


def test_readonly_sql_report_matches_real_model_service(models):
    seed_and_check_models(models)
    database=Path(models.db.database)
    with closing(sqlite3.connect(database)) as seed:
        seed.execute("CREATE TABLE knowledgebase (id TEXT,created_by TEXT,status TEXT)")
        seed.execute("CREATE TABLE dialog (id TEXT,tenant_id TEXT,status TEXT)")
        seed.execute("INSERT INTO knowledgebase VALUES ('k','u','1')")
        seed.commit()
    before=database.read_bytes()
    @contextmanager
    def connect():
        with closing(sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True)) as conn:
            conn.row_factory=sqlite3.Row
            class Cursor:
                def __enter__(self):self.cursor=conn.cursor();return self
                def __exit__(self,*args):self.cursor.close()
                def execute(self,query,values):self.cursor.execute(query.replace('%s','?'),values)
                def fetchall(self):return [dict(row) for row in self.cursor.fetchall()]
            yield SimpleNamespace(cursor=Cursor)
    result=sql.platform_report('/api/v1/admin/analytics/periods?'+urlencode(BASE),connect)
    assert result['current']['totals']['revenue_uzs']==300
    assert result['current']['totals']['paid_payments']==2
    assert result['current']['totals']['new_users']==1
    result=sql.platform_report('/api/v1/admin/analytics/users?'+urlencode({**BASE,'utm_source':'телеграм','search':'TEST'}),connect)
    assert result['total']==1 and result['data'][0]['kb_count']==1
    assert not {'password','access_token'} & set(result['data'][0])
    assert database.read_bytes()==before


def test_mysql_connection_is_explicitly_readonly_and_closed(monkeypatch):
    events=[]
    class Cursor:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def execute(self,query):events.append(query)
    connection=SimpleNamespace(cursor=Cursor,begin=lambda:events.append('begin'),
                               rollback=lambda:events.append('rollback'),close=lambda:events.append('close'))
    pymysql=ModuleType('pymysql');pymysql.cursors=SimpleNamespace(DictCursor=object)
    pymysql.connect=lambda **kwargs:connection
    monkeypatch.setitem(sys.modules,'pymysql',pymysql)
    monkeypatch.setenv('MYSQL_PASSWORD','synthetic-test-only')
    with pytest.raises(RuntimeError):
        with sql.connection():raise RuntimeError('synthetic failure')
    assert events==['SET SESSION TRANSACTION READ ONLY','begin','rollback','close']


def test_server_provider_credentials_are_not_returned_or_exported(web,monkeypatch):
    observed=[]
    import landing_analytics_providers
    def periods(source,credentials,filters,core):
        observed.append(credentials)
        a,b=(core.blank_period(window,filters) for window in (filters.current,filters.previous))
        for period in (a,b):period['totals']={'visits':0,'visitors':0}
        return a,b,[]
    monkeypatch.setattr(landing_analytics_providers,'provider_periods',periods)
    app=Flask(__name__);app.testing=True
    def upstream(*args,**kwargs):return 503,{},{}
    adapter.register_admin_analytics(app,web.path,upstream,landing_authorizer=lambda req:True,
        provider_defaults=lambda source:{'oauth_token':'synthetic-server-only','counter_id':'123'})
    client=app.test_client()
    response=client.post('/api/admin/analytics/export',headers={'Authorization':'Bearer native-test'},
                          json={'filters':BASE,'source':'ym','kind':'report'})
    assert response.status_code==200
    assert observed[0]['oauth_token']=='synthetic-server-only'
    workbook=openpyxl.load_workbook(BytesIO(response.data))
    assert 'synthetic-server-only' not in str([list(sheet.values) for sheet in workbook])
