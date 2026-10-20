"""Non-destructive SQLite backup/restore/check with new destinations only."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from recase.store import Store
from recase.ledger import append_record, read_ledger
from recase.retention import apply_deletions, delete_case


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['backup','restore','check','delete-case','init-deletions']);p.add_argument('--db');p.add_argument('--target');p.add_argument('--deletions');p.add_argument('--owner');p.add_argument('--case-id');a=p.parse_args()
    if a.action=='init-deletions':
        if not a.deletions or Path(a.deletions).exists():p.error('A new --deletions path is required')
        append_record(a.deletions,{'action':'initialize','policy':'explicit-local-operator-v1','automatic_retention':'NOT_CONFIGURED'})
        print(json.dumps({'status':'PASS','action':a.action}));return
    if not a.db:p.error('--db required')
    source=Path(a.db).resolve()
    if not source.is_file():p.error('Database does not exist')
    if a.action=='delete-case':
        if not all((a.deletions,a.owner,a.case_id)):p.error('--deletions/--owner/--case-id required')
        read_ledger(a.deletions)
        print(json.dumps(delete_case(source,a.deletions,a.owner,a.case_id)));return
    store=Store(source,read_only=True)
    if a.action=='check':
        with store.db() as db:
            checks=[r[0] for r in db.execute('PRAGMA integrity_check')]
            result={'integrity':checks,'schema_version':db.execute('PRAGMA user_version').fetchone()[0]}
        print(json.dumps(result));raise SystemExit(0 if checks==['ok'] else 1)
    if not a.target:p.error('--target required; existing targets are never replaced')
    if a.action=='restore':
        if not a.deletions:p.error('Restore requires the current independent --deletions journal; old backups must not revive deleted cases')
        read_ledger(a.deletions)
    target=Path(a.target).resolve();target.parent.mkdir(parents=True,exist_ok=True)
    try:store.backup(target)
    except FileExistsError:p.exit(2,'Existing destination refused\n')
    replay=apply_deletions(target,a.deletions) if a.action=='restore' else None
    with sqlite3.connect(target) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':p.exit(1,'Integrity check failed\n')
    print(json.dumps({'action':a.action,'status':'PASS','target':str(target),'deletions':replay,'note':'restore writes a new database and revokes sessions; switch RECASE_DB after stopping the server'}))


if __name__=='__main__':main()
