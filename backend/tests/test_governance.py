import json
from pathlib import Path
import pytest
from recase.ingestion import ingest, clean
from recase.governance import approved_for
from recase.search import search_evidence


def fixture(tmp_path):
    raw=tmp_path/'raw'; raw.mkdir()
    text=('합성 문서입니다. 인물 A가 서울의 실험실에서 작성한 가상의 기록입니다. ' * 10) + '010-1234-5678 person@example.test 900101-1234567'
    (raw/'fixture.txt').write_text(text)
    manifest=tmp_path/'manifest.json'
    manifest.write_text(json.dumps({'source_type':'synthetic_fixture','documents':[{'file':'fixture.txt','rights_basis':'locally authored synthetic test','permissions':{'processing':True,'rag':True,'training':False}}]}))
    return raw,manifest


def test_ingestion_dry_run_resume_and_quarantine_gate(tmp_path):
    raw,manifest=fixture(tmp_path); output=tmp_path/'output'
    assert ingest(raw,manifest,output,dry_run=True)['collected']==1
    assert not output.exists()
    assert ingest(raw,manifest,output)['quarantined']==1
    record=json.loads((output/'quarantined.jsonl').read_text())
    assert record['source_type']=='synthetic_fixture' and record['state']=='QUARANTINED'
    assert record['privacy_review']['human_reviewed'] is False
    assert '010-1234-5678' not in record['text'] and '[전화번호]' in record['text']
    assert record['text'][record['spans'][0]['start']:record['spans'][0]['end']]==record['spans'][0]['text']
    assert approved_for(record,'rag') is False
    assert ingest(raw,manifest,output,resume=True)['duplicates']==1
    assert len((output/'quarantined.jsonl').read_text().splitlines())==1
    with pytest.raises(FileExistsError): ingest(raw,manifest,output)


def test_purpose_separation_and_human_review():
    d={'state':'APPROVED_FOR_SPECIFIC_USE','permissions':{'rag':True,'training':False},'privacy_review':{'human_reviewed':True,'reviewer':'human-test-fixture'}}
    # Legacy boolean flags have no hash-bound human attestation.
    assert not approved_for(d,'rag')
    assert not approved_for(d,'training')
    assert not approved_for(d,'display')
    assert not approved_for({**d,'privacy_review':{'human_reviewed':False}},'rag')


def test_ingestion_denies_traversal_symlink_and_legacy_blanket_permission(tmp_path):
    raw,manifest=fixture(tmp_path)
    outside=tmp_path/'outside.txt'; outside.write_text('private content')
    (raw/'linked.txt').symlink_to(outside)
    manifest.write_text(json.dumps({'documents':[{'file':f,'rights_basis':'test','permissions':{'processing':True}} for f in ['../outside.txt','linked.txt']] + [{'file':'fixture.txt','permission_confirmed':True,'rights_basis':'legacy'}]}))
    assert ingest(raw,manifest,tmp_path/'output')['denied']==3


def test_html_scripts_and_parse_failure_are_quarantined(tmp_path):
    raw,manifest=fixture(tmp_path)
    (raw/'fixture.html').write_text('<script>private()</script><p>'+('가상 문서 내용 '*30)+'</p>')
    (raw/'bad.pdf').write_bytes(b'not a PDF')
    manifest.write_text(json.dumps({'source_type':'synthetic_fixture','documents':[{'file':f,'rights_basis':'synthetic','permissions':{'processing':True}} for f in ['fixture.html','bad.pdf']]}))
    result=ingest(raw,manifest,tmp_path/'output')
    assert result['failed']==1 and result['quarantined']==1
    rows=[json.loads(x) for x in (tmp_path/'output/quarantined.jsonl').read_text().splitlines()]
    assert 'private()' not in rows[0]['text'] and rows[1]['quarantine_reason']=='PARSE_FAILED'


def test_search_has_verified_offsets_and_scope_only():
    snap={'case_id':'CASE-1','evidence_version':1,'evidence':[{'id':'E1','title':'출입 기록','text':'인물 A는 연구실을 방문했다.'}]}
    hits=search_evidence(snap,'연구실 방문')
    assert len(hits)==1 and hits[0]['case_id']=='CASE-1'
    assert hits[0]['text'][hits[0]['start']:hits[0]['end']]=='인물 A는 연구실을 방문했다.'
    assert search_evidence(snap,'해양 관측')==[]
    with pytest.raises(ValueError): search_evidence(snap,'x',limit=999)
