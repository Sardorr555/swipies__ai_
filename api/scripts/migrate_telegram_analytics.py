"""Additive migration. Dry-run unless --apply is explicitly supplied."""
import argparse
import json
from api.db.db_models import DB
from api.db.telegram_analytics_models import TABLES

def migrate(apply=False):
    with DB.connection_context():
        existing=set(DB.get_tables())
        pending=[m._meta.table_name for m in TABLES if m._meta.table_name not in existing]
        if apply:
            DB.create_tables(TABLES, safe=True)
        return {'mode':'apply' if apply else 'dry-run','tables_to_create':pending}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    print(json.dumps(migrate(parser.parse_args().apply)))
