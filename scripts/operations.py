"""Non-destructive SQLite backup/restore/check with new destinations only."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from recase.store import Store


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['backup','restore','check']);p.add_argument('--db',required=True);p.add_argument('--target');a=p.parse_args()
    source=Path(a.db).resolve()
    if not source.is_file():p.error('Database does not exist')
    store=Store(source,read_only=True)
    if a.action=='check':
        with store.db() as db:
            checks=[r[0] for r in db.execute('PRAGMA integrity_check')]
            result={'integrity':checks,'schema_version':db.execute('PRAGMA user_version').fetchone()[0]}
        print(json.dumps(result));raise SystemExit(0 if checks==['ok'] else 1)
    if not a.target:p.error('--target required; existing targets are never replaced')
    target=Path(a.target).resolve();target.parent.mkdir(parents=True,exist_ok=True)
    try:store.backup(target)
    except FileExistsError:p.exit(2,'Existing destination refused\n')
    with sqlite3.connect(target) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':p.exit(1,'Integrity check failed\n')
    print(json.dumps({'action':a.action,'status':'PASS','target':str(target),'note':'restore writes a new database; switch RECASE_DB after stopping the server'}))


if __name__=='__main__':main()
