"""Prepare synthetic Korean evidence reasoning examples; no real persons/cases."""
import json, random, re, argparse
from pathlib import Path

def build(seed=42):
    rng=random.Random(seed)
    rows=[]
    places=['연구실','도서관','창고','회의실','복도','주차장']
    for i in range(360):
        p,q=rng.sample(places,2)
        h=18+i%5; m=(i*7)%50
        typ=i%3
        if typ==0:
            a=f'기록에 따르면 {h:02d}:{m:02d}에 인물 A가 {p}에 있었다.'
            b=f'동일 시각 {h:02d}:{m:02d}에 인물 A가 {q}에 있었다.'
            label='추가확인필요'; reason='서로 다른 장소 기록이 있으나 기록 오류 또는 장소 간 관계를 확인해야 합니다.'
        elif typ==1:
            a=f'인물 A는 {h:02d}:{m:02d}에 {p}에 있었다고 진술했다.'
            b=f'출입 기록은 같은 시각 A가 {p}에 들어간 것으로 표시한다.'
            label='일치'; reason='진술과 출입 기록의 장소와 시각이 일치합니다.'
        else:
            a=f'인물 A는 사건 당일 {p}에 간 적이 없다고 진술했다.'
            b=f'본인 확인이 완료된 출입 기록에 A가 그날 {p}에 입장한 사실이 남아 있다.'
            label='모순'; reason='방문 사실을 전면 부정한 진술과 확인된 출입 기록이 충돌합니다.'
        rows.append({'case_id':f'SYN-{i:04d}','source':'synthetic','instruction':'두 자료의 관계를 판단하고 근거를 설명하라. 자료가 부족하면 단정하지 마라.', 'evidence':[{'id':'E1','text':a},{'id':'E2','text':b}], 'label':label,'reason':reason})
    rng.shuffle(rows)
    return rows

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output',default='data/processed'); args=ap.parse_args()
    out=Path(args.output)
    if any((out/f'{name}.jsonl').exists() for name in ('train','val','test')):
        raise FileExistsError('기존 데이터 덮어쓰기 금지: --output으로 새 디렉터리를 지정하세요')
    out.mkdir(parents=True,exist_ok=True)
    rows=build()
    for name,chunk in [('train',rows[:252]),('val',rows[252:306]),('test',rows[306:])]:
        with (out/f'{name}.jsonl').open('w',encoding='utf-8') as f:
            for r in chunk:
                prompt=r['instruction']+'\n'+'\n'.join(x['id']+': '+x['text'] for x in r['evidence'])+'\nJSON 형식으로 label, reason을 출력하라.'
                answer=json.dumps({'label':r['label'],'reason':r['reason'],'evidence_ids':['E1','E2']},ensure_ascii=False)
                f.write(json.dumps({'case_id':r['case_id'],'source':r['source'],'prompt':prompt,'answer':answer,'label':r['label']},ensure_ascii=False)+'\n')
        print(name,len(chunk))
if __name__=='__main__':main()
