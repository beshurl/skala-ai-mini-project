"""Guarded new-run launcher. No automatic retraining or adapter overwrite."""
import argparse
import fcntl
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from recase.model import resolve_model, sha256


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--iters',type=int,default=10);p.add_argument('--out');a=p.parse_args()
    data=Path(a.data)
    if not 1<=a.iters<=120:p.error('1..120 iterations only per pilot')
    for name in ['train','valid']:
        if not (data/f'{name}.jsonl').is_file():p.error('train.jsonl and valid.jsonl required')
    validation=data/'approval.json'
    if not validation.is_file():p.error('approval.json with reviewed source and leakage audit required')
    approval=json.loads(validation.read_text())
    if not approval.get('split_audit_pass') or not approval.get('source_approved') or approval.get('train_sha256')!=sha256(data/'train.jsonl') or approval.get('valid_sha256')!=sha256(data/'valid.jsonl'):
        p.error('Data approval is incomplete or hashes have changed')
    root=Path(__file__).resolve().parents[1]; runtime=root/'runtime';runtime.mkdir(exist_ok=True)
    with (runtime/'model.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:p.exit(2,'MODEL_BUSY: stop the model server before training\n')
        out=Path(a.out or root/'outputs/runs'/ (datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%z')+'-train'))
        out.mkdir(parents=True,exist_ok=False)
        command=[sys.executable,'-m','mlx_lm','lora','--model',str(resolve_model()),'--train','--data',str(data),'--batch-size','1','--num-layers','8','--iters',str(a.iters),'--learning-rate','1e-4','--max-seq-length','768','--grad-checkpoint','--mask-prompt','--adapter-path',str(out/'adapter'),'--save-every',str(a.iters),'--steps-per-eval',str(a.iters),'--val-batches','2']
        (out/'plan.json').write_text(json.dumps({'command':command,'max_seconds':1800,'memory_stop':'operator interruption on system memory pressure','source_approval':approval},ensure_ascii=False,indent=2))
        try:
            with (out/'training.log').open('x') as log: result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
        except subprocess.TimeoutExpired:p.exit(1,'TRAINING_TIMEOUT: inspect preserved run\n')
        raise SystemExit(result.returncode)


if __name__=='__main__':main()
