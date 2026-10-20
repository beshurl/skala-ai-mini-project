"""Audit all data without printing prompts/answers; real tokenizer lengths, split leakage."""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from evaluation.scoring import LABELS, parse_response, allowed_evidence, percentile
from recase.model import resolve_model, SYSTEM


def skeleton(text):
    return re.sub(r'\d+', '#', re.sub('연구실|도서관|창고|회의실|복도|주차장','[장소]',text))


def audit(source, tokenize=True):
    source=Path(source)
    datasets={name:[json.loads(x) for x in (source/f'{name}.jsonl').read_text().splitlines() if x.strip()] for name in ['train','val','test']}
    report={'splits':{},'overlap':{},'status':'PASS','evaluation_use':'development_exposed'}
    tokenizer=None
    if tokenize:
        from transformers import AutoTokenizer
        tokenizer=AutoTokenizer.from_pretrained(str(resolve_model()),local_files_only=True,trust_remote_code=False)
    for name,rows in datasets.items():
        errors=[]; input_lengths=[]; output_lengths=[]; training_lengths=[]
        for r in rows:
            parsed,error=parse_response(r['answer'],allowed_evidence(r))
            if error or r['label'] not in LABELS or (parsed and parsed['label']!=r['label']): errors.append(r['case_id'])
            if tokenizer:
                messages=[{'role':'system','content':SYSTEM},{'role':'user','content':r['prompt']}]
                input_lengths.append(len(tokenizer.apply_chat_template(messages,add_generation_prompt=True,enable_thinking=False,return_dict=False)))
                output_lengths.append(len(tokenizer.encode(r['answer'],add_special_tokens=False)))
                training_lengths.append(len(tokenizer.apply_chat_template(messages+[{'role':'assistant','content':r['answer']}],add_generation_prompt=False,return_dict=False)))
        report['splits'][name]={'count':len(rows),'sha256':hashlib.sha256((source/f'{name}.jsonl').read_bytes()).hexdigest(),
                              'labels':dict(Counter(r['label'] for r in rows)),'contract_error_ids':errors,'unique_templates':len({skeleton(r['prompt']) for r in rows}),
                              'group_metadata_complete':all('scenario_family' in r and 'document_family' in r for r in rows)}
        if tokenizer:
            report['splits'][name]['tokens']={key:{'p50':percentile(values,.5),'p95':percentile(values,.95),'max':max(values),'over_768':sum(v>768 for v in values)} for key,values in [('input',input_lengths),('answer',output_lengths),('training_template',training_lengths)]}
        if errors or len({r['case_id'] for r in rows})!=len(rows):report['status']='FAIL'
    for a,b in [('train','val'),('train','test'),('val','test')]:
        report['overlap'][a+'_'+b]={
            'case_ids':len({r['case_id'] for r in datasets[a]}&{r['case_id'] for r in datasets[b]}),
            'exact_prompts':len({r['prompt'] for r in datasets[a]}&{r['prompt'] for r in datasets[b]}),
            'normalized_template_families':len({skeleton(r['prompt']) for r in datasets[a]}&{skeleton(r['prompt']) for r in datasets[b]})}
    report['generalization_split']='FAIL' if any(x['normalized_template_families'] or x['exact_prompts'] or x['case_ids'] for x in report['overlap'].values()) else 'UNVERIFIED_WITHOUT_FAMILY_METADATA'
    if report['generalization_split']=='FAIL':report['status']='FAIL'
    report['template_alignment']={'training':'MLX ChatDataset default full conversation template','inference':'enable_thinking=False; shared system prompt v2', 'legacy_training_thinking_flag':'UNVERIFIED (not recorded)', 'note':'Original train system differs from original evaluation system; new inference uses original train system. No training rerun.'}
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',default='data/processed');p.add_argument('--out',required=True);p.add_argument('--no-tokenize',action='store_true');a=p.parse_args()
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():raise FileExistsError(out)
    report=audit(a.source,not a.no_tokenize)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'status':report['status'],'generalization_split':report['generalization_split'],'result':str(out)},ensure_ascii=False))
    if report['status']=='FAIL':raise SystemExit(1)


if __name__=='__main__':main()
