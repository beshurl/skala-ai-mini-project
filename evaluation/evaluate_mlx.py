import argparse,json,re,time
from pathlib import Path
from sklearn.metrics import accuracy_score,f1_score,classification_report

def extract(s):
    s=re.sub(r'<think>.*?</think>','',s,flags=re.S)
    try:
        obj=json.loads(s[s.index('{'):s.rindex('}')+1]);return obj.get('label','invalid') if obj.get('label') in ('일치','모순','추가확인필요') else 'invalid'
    except (ValueError,TypeError,KeyError):return 'invalid'

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',default='mlx-community/Qwen3-0.6B-4bit');p.add_argument('--adapter');p.add_argument('--test',default='data/processed/test.jsonl');p.add_argument('--out',default='outputs/base_mlx');p.add_argument('--limit',type=int,default=54);a=p.parse_args()
    from mlx_lm import load,generate
    model,tok=load(a.model,adapter_path=a.adapter)
    examples=[json.loads(x) for x in Path(a.test).read_text(encoding='utf8').splitlines() if x.strip()][:a.limit]
    rows=[]
    for ex in examples:
        messages=[{'role':'system','content':'당신은 증거를 근거로 판단하며 JSON으로 답변합니다. /no_think'},{'role':'user','content':ex['prompt']}]
        prompt=tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
        t=time.perf_counter();reply=generate(model,tok,prompt=prompt,max_tokens=160,verbose=False)
        rows.append({'case_id':ex['case_id'],'gold':ex['label'],'pred':extract(reply),'response':reply,'seconds':round(time.perf_counter()-t,3)})
    if not rows:raise ValueError('평가 데이터가 비어 있습니다')
    y=[r['gold'] for r in rows];z=[r['pred'] for r in rows];out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    with (out/'predictions.jsonl').open('w',encoding='utf8') as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    metrics={'count':len(rows),'accuracy':accuracy_score(y,z),'macro_f1':f1_score(y,z,labels=['일치','모순','추가확인필요'],average='macro',zero_division=0),'invalid_rate':z.count('invalid')/len(z),'mean_latency_s':sum(r['seconds'] for r in rows)/len(rows),'classification_report':classification_report(y,z,zero_division=0,output_dict=True)}
    (out/'metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in metrics.items() if k!='classification_report'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
