"""Only ingest locally supplied judgments for which the operator has permission to process."""
import argparse,hashlib,json,re
from pathlib import Path

def clean(text):
    text=re.sub(r'(?m)^\s*(?:대법원|서울중앙지방법원|[가-힣]+지방법원)\s*$', '[법원]',text)
    text=re.sub(r'(?<!\d)01[016789][- ]?\d{3,4}[- ]?\d{4}(?!\d)','[전화번호]',text)
    text=re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}','[이메일]',text)
    text=re.sub(r'\b\d{6}[- ]?[1-4]\d{6}\b','[주민등록번호]',text)
    text=re.sub(r'(?m)^[ \t]+','',text)
    return re.sub(r'\n{3,}','\n\n',text).strip()

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',default='data/judgments_cleaned.jsonl');p.add_argument('--manifest',required=True,help='JSON file listing allowed file names and rights basis');a=p.parse_args()
    from pypdf import PdfReader
    root=Path(a.input).resolve(); manifest=json.loads(Path(a.manifest).read_text(encoding='utf8')); allowed={x['file']:x for x in manifest['documents'] if x.get('permission_confirmed') is True}
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);seen=set();count=0
    with out.open('w',encoding='utf8') as f:
        for path in sorted(root.iterdir()):
            if path.name not in allowed or path.suffix.lower() not in ('.txt','.pdf'):continue
            if path.suffix.lower()=='.txt':raw=path.read_text(encoding='utf8')
            else:raw='\n'.join(page.extract_text() or '' for page in PdfReader(path).pages)
            content=clean(raw);digest=hashlib.sha256(content.encode()).hexdigest()
            if len(content)<200 or digest in seen:continue
            seen.add(digest);f.write(json.dumps({'doc_id':digest[:16],'source_file':path.name,'rights_basis':allowed[path.name]['rights_basis'],'text':content,'review_required':True},ensure_ascii=False)+'\n');count+=1
    print('정제 문서:',count,'(인명·주소·사건번호 등의 비식별화는 수동 검수가 추가로 필요합니다)')
if __name__=='__main__':main()
