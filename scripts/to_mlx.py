"""Preserve existing MLX datasets; use the shared system prompt for new exports."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.model import SYSTEM


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source', default='data/processed')
    p.add_argument('--output', default='data/mlx')
    args=p.parse_args()
    source,target=Path(args.source),Path(args.output)
    if target.exists():
        raise FileExistsError('기존 MLX 데이터 보존: --output으로 새 디렉터리를 지정하세요')
    datasets={name:[json.loads(x) for x in (source/f'{name}.jsonl').read_text().splitlines() if x.strip()] for name in ['train','val','test']}
    target.mkdir(parents=True,exist_ok=False)
    for name,dest in [('train','train'),('val','valid'),('test','test')]:
        with (target/f'{dest}.jsonl').open('x') as f:
            for row in datasets[name]:
                f.write(json.dumps({'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':row['prompt']},{'role':'assistant','content':row['answer']}]},ensure_ascii=False)+'\n')
        print(dest,len(datasets[name]))


if __name__=='__main__':main()
