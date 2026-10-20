"""Persist commands, timestamps, exit codes and artifacts without hiding failures."""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def now():
    return datetime.now(ZoneInfo('Asia/Seoul')).isoformat()


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[2];out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
    commands=[('T01',[sys.executable,'-m','pytest','backend/tests','-q','--tb=short']),
              ('T02',[sys.executable,'-m','compileall','-q','backend']),
              ('T03',[sys.executable,'-m','pip','check']),
              ('T04',[sys.executable,'backend/scripts/compare.py','outputs/runs/20261020-base-v2-retry1/metrics.json','outputs/runs/20261020-ft-v2/metrics.json'])]
    checks=[]
    for name,command in commands:
        start=now();log=out/(name+'.log')
        with log.open('x') as f:result=subprocess.run(command,cwd=root,stdout=f,stderr=subprocess.STDOUT)
        checks.append({'id':name,'status':'PASS' if result.returncode==0 else 'FAIL','command':command,'started_at':start,'finished_at':now(),'exit_code':result.returncode,'result_file':str(log)})
    manifest=json.loads((root/'outputs/runs/20261020T122029+0900-audit/original_manifest.json').read_text())
    artifact_checks={k:hashlib.sha256((root/k).read_bytes()).hexdigest()==v['sha256'] for k,v in manifest.items() if k.startswith(('outputs/','data/processed/','data/mlx/'))}
    summary={'started_at':checks[0]['started_at'],'finished_at':now(),'checks':checks,'original_artifacts_preserved':artifact_checks,'status':'PASS' if all(c['exit_code']==0 for c in checks) and all(artifact_checks.values()) else 'FAIL'}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False,indent=2))
    raise SystemExit(0 if summary['status']=='PASS' else 1)


if __name__=='__main__':main()
