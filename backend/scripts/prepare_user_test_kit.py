"""Export a fresh, exposed synthetic practice kit. Never calls a model or changes a DB."""
import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.paths import PROJECT_ROOT
from recase.practice import BUNDLE, bundle


def export(out):
    data, source_sha = bundle()
    reference_path = PROJECT_ROOT/'docs/practice/v1/review_reference.json'
    reference = json.loads(reference_path.read_text())
    lookup = {(r['case_id'],r['version']): r for r in reference['checks']}
    pairs = {(c['id'],s['version']) for c in data['cases'] for s in c['stages']}
    if len(lookup) != 36 or set(lookup) != pairs or reference['human_reviewed'] is not False:
        raise ValueError('Review references do not match all practice stages')
    snapshots=[]; notes=['# 검토 참고표\n\nAI 작성·사람 검수 대기 제안입니다. 범인 정답이나 사건 해결 판정이 아닙니다. 먼저 본인 판단을 기록한 뒤 확인하세요.\n']
    records=[]
    for case in data['cases']:
        for stage in case['stages']:
            version=stage['version']; visible=[e for e in case['evidence'] if e['release_at']<=version]
            row=lookup[(case['id'],version)]
            if not set(row['supporting_document_keys']).issubset({e['key'] for e in visible}):
                raise ValueError('Reference cites unreleased evidence')
            if row['proposed_relation'] not in ('SUPPORTED','CONTRADICTED','INSUFFICIENT') or row['case_resolution']!='UNRESOLVED':
                raise ValueError('Invalid or overclaimed reference')
            snapshots.append({'case_id':case['id'],'title':case['title'],'evidence_version':version,'source':'AI_AUTHORED_SYNTHETIC','claims':case['claims'],'evidence':visible})
            notes.append(f"## {case['id']} {case['title']} · v{version}\n\n제안 관계: **{row['proposed_relation']}**. 사건 자체: 미해결.\n\n{row['reason']}\n\n참고 근거: {', '.join(row['supporting_document_keys'])}\n\n빠진 정보: {', '.join(row['missing_information'])}\n\n다음 확인 제안: {row['next_check']}\n")
            records.append({'case_id':case['id'],'version':version,'status':'NOT_RUN','observed_relation':None,'job_status':None,'evidence_keys':[],'missing_information':[],'next_check':'','unsupported_assertions':[],'reviewer_notes':'','duration':'NOT_MEASURED','human_reviewer':None})
    out=Path(out).absolute()
    out.mkdir(parents=True,exist_ok=False,mode=0o700)
    def write(name,text):
        path=out/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text);path.chmod(0o600)
    write('cases.json',BUNDLE.read_text())
    write('review_reference.json',reference_path.read_text())
    write('snapshots.jsonl',''.join(json.dumps(s,ensure_ascii=False)+'\n' for s in snapshots))
    write('먼저읽기.md',(PROJECT_ROOT/'docs/CASE_REVIEW_AND_TESTING.md').read_text())
    write('검토참고표.md','\n'.join(notes))
    write('결과기록.json',json.dumps({'is_blank_template':True,'source':'synthetic_exposed_practice','results':records},ensure_ascii=False,indent=2)+'\n')
    write('결과기록.md','# 직접 테스트 기록\n\n관계·근거 인용·빠진 정보·다음 확인·근거 없는 단정·실행 실패를 기록하세요. 빈칸은 통과가 아닙니다.\n\n| 사건 | 단계 | 실행 상태 | 관측 관계 | 인용 근거 | 부족 정보/다음 확인 | 메모 |\n| --- | --- | --- | --- | --- | --- | --- |\n'+''.join(f"| {r['case_id']} | v{r['version']} | NOT_RUN |  |  |  |  |\n" for r in records))
    for case in data['cases']:
        for evidence in case['evidence']:
            write('증거별/'+evidence['key']+'.md',f"# {evidence['key']} · {evidence['title']}\n\n가상 사건: {case['id']} {case['title']}\n\n공개 단계: v{evidence['release_at']}\n\n{evidence['text']}\n\n출처: {evidence['origin']['document_id']} / AI가 작성한 가상 기록. 실제 사건 자료가 아닙니다.\n")
        lines=[f"# {case['id']} {case['title']}\n",f"{case['summary']}\n",f"검토할 주장: {case['question']}\n",'현재 앱 연결: '+('P01~P03 합성 기능 데모' if case['automatic_demo'] else '수동 검토/향후 구현 자료. 자동 분석 지원 아님')+'\n']
        for stage in case['stages']:
            lines.append(f"## v{stage['version']}에 새로 공개하는 문서\n")
            for e in case['evidence']:
                if e['release_at']==stage['version']:
                    lines.extend([f"### {e['key']} · {e['title']}\n",e['text']+'\n','출처: '+e['origin']['document_id']+' / AI가 작성한 가상 문서\n'])
            lines.append('먼저 판단 기록: 관계 / 근거 / 빠진 정보 / 다음 확인 / 사건 해결 여부(미해결)\n')
        write('사건별/'+case['id']+'.md','\n'.join(lines))
    # This is an exposure record for this new synthetic kit, not a native NLI ledger modification.
    write('exposure_log.json',json.dumps({'source':'AI_AUTHORED_EXPOSED_DEVELOPMENT','human_reviewed':False,'training_eligible':False,'independent_final_set':False,'family_note':'방문·신원 사례 사이 구조 중복이 있음.12개 독립 계열이라고 주장하지 않음.','cases':[{'case_id':c['id'],'sha256':hashlib.sha256(json.dumps(c,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),'events':['AI_AUTHORED','AI_REVIEW_REFERENCE_AUTHORED','USER_PRACTICE_PUBLICATION'],'label_review':'HUMAN_REVIEW_PENDING'} for c in data['cases']]},ensure_ascii=False,indent=2)+'\n')
    paths=sorted(p for p in out.rglob('*') if p.is_file())
    manifest={'status':'STRUCTURAL_VALIDATION_PASS','counts':{'synthetic_cases':12,'documents':48,'stages':36,'app_connected_cases':3,'manual_only_cases':9,'actual_cases':0},'source_sha256':source_sha,'reference_sha256':hashlib.sha256(reference_path.read_bytes()).hexdigest(),'model_evaluation':'NOT_RUN','human_reviewed':False,'files':{str(p.relative_to(out)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in paths}}
    write('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    archive=out.parent/(out.name+'.zip')
    if archive.exists():raise FileExistsError('Refusing to replace an existing archive')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.rglob('*')):
            if p.is_file():z.write(p,arcname=str(Path(out.name)/p.relative_to(out)))
    archive.chmod(0o600)
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('Archive integrity failed')
    return {'status':manifest['status'],'counts':manifest['counts'],'directory':str(out),'archive':str(archive),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,help='A new output directory; existing files are never replaced')
    args=parser.parse_args();print(json.dumps(export(args.out),ensure_ascii=False,indent=2))
