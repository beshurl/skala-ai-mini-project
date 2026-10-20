"""Explicit browser failure-state testing. Never loads or falls back to an LLM."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import uvicorn
from recase.api import create_app
from recase.testing import FixtureModel


def main():
    p=argparse.ArgumentParser();p.add_argument('--scenario',choices=['slow-invalid','unavailable'],required=True);p.add_argument('--db',required=True);p.add_argument('--port',type=int,required=True);a=p.parse_args()
    if Path(a.db).exists():p.error('Use a fresh fixture database path')
    if not 1024<=a.port<=65535:p.error('Use a non-privileged local port')
    if a.scenario=='unavailable':
        class Unavailable(FixtureModel):
            def load(self):raise RuntimeError('deliberate fixture loading failure')
        model=Unavailable()
    else:model=FixtureModel(delay=2,invalid=True)
    uvicorn.run(create_app(a.db,model=model),host='127.0.0.1',port=a.port,workers=1,access_log=False,log_level='warning')


if __name__=='__main__':main()
