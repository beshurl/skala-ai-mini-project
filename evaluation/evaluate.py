"""Evaluate a model/adapter on held-out cases. Produces per-example JSONL and metrics JSON."""
import argparse,json,re,time
from pathlib import Path
from sklearn.metrics import accuracy_score,f1_score,classification_report

def parse_label(text):
    try:
        o=json.loads(text[text.index('{'):text.rindex('}')+1]);return o.get('label','invalid')
    except (ValueError,KeyError,TypeError):
        for k in ['추가확인필요','일치','모순']:
            if re.search(r'"label"\s*:\s*"'+k+'"',text):return k
        return 'invalid'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--model',default='Qwen/Qwen3-0.6B');ap.add_argument('--adapter');ap.add_argument('--test',default='data/processed/test.jsonl');ap.add_argument('--out',default='outputs/eval');ap.add_argument('--max-examples',type=int,default=54);args=ap.parse_args()
    import torch
    from transformers import AutoTokenizer,AutoModelForCausalLM
    from peft import PeftModel
    tok=AutoTokenizer.from_pretrained(args.model)
    model=AutoModelForCausalLM.from_pretrained(args.model,torch_dtype='auto',device_map='auto')
    if args.adapter:model=PeftModel.from_pretrained(model,args.adapter)
    model.eval();rows=[]
    with open(args.test,encoding='utf-8') as f:examples=[json.loads(s) for s in f][:args.max_examples]
    for ex in examples:
        msg=tok.apply_chat_template([{'role':'user','content':ex['prompt']}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
        inputs=tok(msg,return_tensors='pt').to(model.device);t=time.monotonic()
        with torch.inference_mode(): ids=model.generate(**inputs,max_new_tokens=128,do_sample=False,pad_token_id=tok.eos_token_id)
        answer=tok.decode(ids[0][inputs['input_ids'].shape[-1]:],skip_special_tokens=True)
        rows.append({'case_id':ex['case_id'],'gold':ex['label'],'pred':parse_label(answer),'answer':answer,'seconds':round(time.monotonic()-t,3)})
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    with (out/'predictions.jsonl').open('w',encoding='utf-8') as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    y=[r['gold'] for r in rows];p=[r['pred'] for r in rows]
    result={'count':len(rows),'accuracy':accuracy_score(y,p),'macro_f1':f1_score(y,p,labels=['일치','모순','추가확인필요'],average='macro',zero_division=0),'invalid_rate':sum(v=='invalid' for v in p)/len(p),'avg_seconds':sum(r['seconds'] for r in rows)/len(rows),'report':classification_report(y,p,zero_division=0,output_dict=True)}
    (out/'metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='report'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
