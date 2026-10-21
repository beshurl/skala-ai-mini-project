import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {parseCaseFile,readCaseFile,casePayload,MAX_FILE_BYTES} from '../src/caseFiles.ts';

const template=JSON.parse(await readFile(new URL('../public/assets/recase-case-template.json',import.meta.url),'utf8'));
const parse=value=>parseCaseFile('case.json',JSON.stringify(value));

test('JSON preserves explicit public/held-back evidence while creating a new request',()=>{
  const imported=parse(template),draft=imported.cases[0];
  assert.equal(draft.evidence[1].initially_released,false);
  const payload=casePayload(draft,'a'.repeat(32));
  assert.equal(payload.synthetic_only,true);
  assert.deepEqual(Object.keys(payload).sort(),['claims','creation_id','evidence','summary','synthetic_only','title']);
  assert.equal('human_reviewed' in payload,false);
});
test('TXT and MD preserve literal markup, astral characters and Unicode source boundaries',()=>{
  const content='가상 원문 😀 <script>untrusted()</script>\n'+'가'.repeat(7800)+'😀'.repeat(20);
  for(const name of ['sample.TXT','sample.md']){
    const file=parseCaseFile(name,content);
    assert.equal(file.cases[0].evidence.map(e=>e.text).join(''),content);
    assert.equal(file.cases[0].evidence.length,1);
  }
  const large='A'.repeat(7999)+'😀'+'B'.repeat(8001);
  const parts=parseCaseFile('long.txt',large).cases[0].evidence;
  assert.equal(parts.length,3);assert.equal(parts.map(p=>p.text).join(''),large);
  assert.ok(parts.every(p=>Array.from(p.text).length<=8000));
});
test('the existing 12-case synthetic practice bundle maps only claims and evidence',async()=>{
  const bundle=await readFile(new URL('../../data/practice/v1/cases.json',import.meta.url),'utf8');
  const imported=parseCaseFile('cases.json',bundle);
  assert.equal(imported.cases.length,12);assert.equal(imported.format,'practice');
  for(const c of imported.cases){
    assert.deepEqual(c.evidence.map(e=>e.initially_released),[true,true,false,false]);
    assert.ok(c.claims.every(x=>typeof x==='string'));
    assert.equal('attributes' in c.evidence[0],false);
  }
});
test('approval claims, source roles and answer keys cannot be imported as authority',()=>{
  for(const input of [{...template,synthetic_only:false},{...template,human_reviewed:true},{...template,role:'admin'},{...template,expected_label:'SUPPORTED'}])assert.throws(()=>parse(input));
  const evidence=[{...template.evidence[0],initially_released:'false'}];assert.throws(()=>parse({...template,evidence}));
  assert.throws(()=>parse({...template,evidence:[{...template.evidence[0],initially_released:null}]}));
  assert.throws(()=>parse({...template,evidence:[{...template.evidence[0],attributes:{owner:'forged'}}]}));
});
test('practice files claiming real cases or human approval are rejected',()=>{
  const bundle={schema:'recase_user_practice_v1',source:'AI_AUTHORED_SYNTHETIC',actual_cases:1,human_reviewed:false,training_eligible:false,independent_final_set:false,cases:[]};
  assert.throws(()=>parse(bundle),/가상 연습/);
  assert.throws(()=>parse({...bundle,actual_cases:0,human_reviewed:true}),/가상 연습/);
});
test('bounds reject excessive, empty, binary and malformed input instead of truncating it',()=>{
  for(const [name,value] of [['wrong.pdf','text'],['empty.txt','  '],['binary.txt','a\0b'],['bad.json','{'],['list.json','[]']])assert.throws(()=>parseCaseFile(name,value));
  assert.throws(()=>parseCaseFile('large.txt','A'.repeat(24001)),/24,000/);
  assert.throws(()=>parse({...template,claims:['x'.repeat(701)]}));
  assert.throws(()=>parse({...template,claims:['line1\nline2']}),/줄바꿈/);
  assert.throws(()=>parse({...template,evidence:[{...template.evidence[0],text:'x'.repeat(8001)}]}));
  assert.throws(()=>parseCaseFile('bad.txt','\ud800'),/잘못된 문자/);
});
test('the UTF-8 payload budget respects the existing server 64KiB boundary',()=>{
  assert.throws(()=>parseCaseFile('korean.txt','가'.repeat(23000)),/64KiB/);
  assert.doesNotThrow(()=>parseCaseFile('ascii.txt','A'.repeat(24000)));
  assert.throws(()=>casePayload(parse(template).cases[0],'invalid-id'));
});
test('oversized and unsupported files are rejected before their bytes are read',async()=>{
  let reads=0;const arrayBuffer=async()=>{reads++;return new ArrayBuffer(0);};
  await assert.rejects(readCaseFile({name:'large.json',size:MAX_FILE_BYTES+1,arrayBuffer}),/256KiB/);
  await assert.rejects(readCaseFile({name:'case.docx',size:1,arrayBuffer}),/TXT/);
  assert.equal(reads,0);
});
test('UTF-8 BOM is accepted and invalid encoding is reported without replacement characters',async()=>{
  const bytes=new TextEncoder().encode('\uFEFF'+JSON.stringify(template));
  assert.equal((await readCaseFile({name:'case.json',size:bytes.length,arrayBuffer:async()=>bytes.buffer})).cases.length,1);
  await assert.rejects(readCaseFile({name:'case.txt',size:2,arrayBuffer:async()=>new Uint8Array([0xff,0xfe]).buffer}),/UTF-8/);
});
test('all three downloadable examples can actually be imported',async()=>{
  for(const ext of ['txt','md','json']){
    const bytes=await readFile(new URL('../public/assets/recase-case-template.'+ext,import.meta.url));
    const imported=await readCaseFile({name:'recase-case-template.'+ext,size:bytes.length,arrayBuffer:async()=>bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength)});
    assert.equal(imported.cases.length,1);
  }
});
