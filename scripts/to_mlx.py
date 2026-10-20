import json
from pathlib import Path
source=Path('data/processed'); target=Path('data/mlx');target.mkdir(parents=True,exist_ok=True)
for src,dest in [('train','train'),('val','valid'),('test','test')]:
    n=0
    with (source/f'{src}.jsonl').open(encoding='utf8') as fi,(target/f'{dest}.jsonl').open('w',encoding='utf8') as fo:
        for line in fi:
            row=json.loads(line)
            fo.write(json.dumps({'messages':[{'role':'system','content':'당신은 증거를 근거로 판단하며, 불충분한 증거에는 단정하지 않는 분석가입니다.'},{'role':'user','content':row['prompt']},{'role':'assistant','content':row['answer']}]},ensure_ascii=False)+'\n');n+=1
    print(dest,n)
