"""Non-secret environment manifest, suitable for reproducible local run records."""
import argparse
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    target=Path(a.out);target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():raise FileExistsError(target)
    packages={}
    for name in ['mlx','mlx-lm','transformers','fastapi','langgraph','mcp','pydantic','pytest','pypdf']:
        try:packages[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:packages[name]='NOT_INSTALLED'
    info={'time_utc':datetime.now(timezone.utc).isoformat(),'python':sys.version,'executable':sys.executable,'machine':platform.machine(), 'platform':platform.platform(),'packages':packages,'disk_free_bytes':shutil.disk_usage('.').free,'environment_variable_names':['RECASE_BACKEND','RECASE_ADAPTER','RECASE_DB'],'secret_values':'NOT_COLLECTED'}
    if sys.platform=='darwin':
        info['physical_memory_bytes']=int(subprocess.check_output(['sysctl','-n','hw.memsize'],text=True))
        info['vm_stat']=subprocess.check_output(['vm_stat'],text=True)
    target.write_text(json.dumps(info,ensure_ascii=False,indent=2));print(target)


if __name__=='__main__':main()
