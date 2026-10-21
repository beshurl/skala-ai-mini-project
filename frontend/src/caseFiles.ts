/** Local draft import only. No requests, source execution, review grants or model calls. */
export interface DraftEvidence {title:string;text:string;kind:string;initially_released:boolean}
export interface CaseDraft {title:string;summary:string;claims:string[];evidence:DraftEvidence[]}
export interface CaseFile {name:string;cases:CaseDraft[];format:'text'|'json'|'practice'}
export const MAX_FILE_BYTES=256*1024;
const kinds=new Set(['record','statement','note','correction','test_result']);
const length=(value:string)=>Array.from(value).length;
function record(value:unknown):Record<string,any>{
  if(!value || typeof value!=='object' || Array.isArray(value))throw new Error('사건 JSON의 항목 형식을 확인하세요.');
  return value as Record<string,any>;
}
function text(value:unknown,label:string,max:number,empty=false):string{
  if(typeof value!=='string')throw new Error(`${label}은 텍스트여야 합니다.`);
  const clean=value.trim();
  if((!empty && !clean) || length(clean)>max)throw new Error(`${label}은 ${empty?'0':'1'}~${max.toLocaleString()}자로 입력하세요.`);
  if(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(clean) || Array.from(clean).some(c=>c.length===1 && c.charCodeAt(0)>=0xd800 && c.charCodeAt(0)<=0xdfff))throw new Error('텍스트에 지원하지 않는 제어 문자나 잘못된 문자가 있습니다. UTF-8 텍스트로 다시 저장하세요.');
  return clean;
}
function keys(value:Record<string,any>,allowed:string[]){
  if(Object.keys(value).some(key=>!allowed.includes(key)))throw new Error('사건 JSON에 지원하지 않는 항목이 있습니다. 예시 JSON 형식을 사용하세요.');
}
export function normalizeDraft(value:unknown):CaseDraft{
  const input=record(value);keys(input,['title','summary','claims','evidence']);
  if(!Array.isArray(input.claims) || input.claims.length<1 || input.claims.length>8)throw new Error('검토할 주장은 1~8개여야 합니다.');
  const claims=input.claims.map((claim:unknown)=>text(claim,'주장',700));
  if(claims.some((claim:string)=>/[\r\n]/.test(claim)))throw new Error('JSON의 각 주장은 줄바꿈 없이 한 항목으로 작성하세요.');
  if(!Array.isArray(input.evidence) || input.evidence.length<1 || input.evidence.length>24)throw new Error('자료는 1~24개여야 합니다.');
  const evidence=input.evidence.map((value:unknown)=>{
    const item=record(value);keys(item,['title','text','kind','initially_released']);
    const kind=item.kind===undefined?'record':item.kind,released=item.initially_released===undefined?true:item.initially_released;
    if(!kinds.has(kind) || typeof released!=='boolean')throw new Error('자료 종류와 처음부터 공개 여부를 확인하세요.');
    return {title:text(item.title,'자료 제목',120),text:text(item.text,'자료 원문',8000),kind,initially_released:released};
  });
  if(evidence.reduce((sum:number,item:DraftEvidence)=>sum+length(item.text),0)>24000)throw new Error('전체 자료 원문은 24,000자까지 불러올 수 있습니다. 사건을 나누세요.');
  return {title:text(input.title,'사건 제목',120),summary:text(input.summary??'','사건 개요',2000,true),claims,evidence};
}
export function casePayload(draft:unknown,creationId:string){
  if(!/^[a-f0-9]{32}$/.test(creationId))throw new Error('저장 요청을 새로 준비해야 합니다.');
  const payload={creation_id:creationId,synthetic_only:true,...normalizeDraft(draft)};
  if(new TextEncoder().encode(JSON.stringify(payload)).length>65536)throw new Error('저장 요청의 64KiB 한도를 넘었습니다. 원문을 줄이거나 사건을 나누세요.');
  return payload;
}
function checked(draft:unknown){const value=normalizeDraft(draft);casePayload(value,'0'.repeat(32));return value;}
function practice(value:Record<string,any>):CaseDraft[]{
  if(value.source!=='AI_AUTHORED_SYNTHETIC' || value.actual_cases!==0 || value.human_reviewed!==false || value.training_eligible!==false || value.independent_final_set!==false)throw new Error('이 불러오기는 가상 연습 자료만 지원합니다. 실제 자료는 승인·검수 경로를 사용하세요.');
  if(!Array.isArray(value.cases) || !value.cases.length || value.cases.length>24)throw new Error('연습 묶음은 1~24개 사건을 지원합니다.');
  return value.cases.map((item:unknown)=>{
    const source=record(item);
    if(!Array.isArray(source.claims) || !Array.isArray(source.evidence))throw new Error('연습 사건의 주장과 자료를 확인하세요.');
    const evidence=source.evidence.map((v:unknown)=>{
      const e=record(v);
      if(![1,2,3].includes(e.release_at) || record(e.origin).type!=='synthetic_authored')throw new Error('연습 자료의 출처와 공개 순서를 확인하세요.');
      return {...e};
    }).sort((a:any,b:any)=>a.release_at-b.release_at);
    return checked({title:source.title,summary:source.summary,claims:source.claims.map((c:unknown)=>record(c).text),
      evidence:evidence.map((e:any)=>({title:e.title,text:e.text,kind:e.kind,initially_released:e.release_at===1}))});
  });
}
export function parseCaseFile(name:string,raw:string):CaseFile{
  const extension=name.toLowerCase().match(/\.(txt|md|json)$/)?.[1];
  if(!extension)throw new Error('TXT·MD·JSON 파일을 선택하세요. PDF·HWP·DOCX는 현재 지원하지 않습니다.');
  if(!raw.trim())throw new Error('빈 파일입니다. 사건 자료가 들어 있는 파일을 선택하세요.');
  if(extension==='json'){
    let value:Record<string,any>;
    try{value=record(JSON.parse(raw.replace(/^\uFEFF/,'')));}catch{throw new Error('JSON을 읽지 못했습니다. 예시 파일처럼 사건 객체로 작성하세요.');}
    if(/"(?:expected_label|proposed_relation|next_check|answer_key|gold_label)"\s*:/.test(raw))throw new Error('정답·평가 참고표가 포함된 파일은 사건 입력으로 불러올 수 없습니다.');
    if(value.schema==='recase_user_practice_v1')return {name,cases:practice(value),format:'practice'};
    keys(value,['schema','synthetic_only','title','summary','claims','evidence']);
    if(value.schema!=='recase_case_file_v1' || value.synthetic_only!==true)throw new Error('예시의 recase_case_file_v1 형식과 synthetic_only: true를 확인하세요.');
    const {schema,synthetic_only,...draft}=value;
    return {name,cases:[checked(draft)],format:'json'};
  }
  const content=text(raw,'파일 원문',24000),points=Array.from(content),pieces:string[]=[];
  for(let offset=0;offset<points.length;offset+=8000)pieces.push(points.slice(offset,offset+8000).join(''));
  const stem=Array.from(name.replace(/^.*[\\/]/,'').replace(/\.[^.]+$/,'')).slice(0,100).join('').trim()||'불러온 가상 사건';
  const draft=checked({title:stem,summary:'',claims:['공개 자료에서 확인할 수 있는 사실과 추가 확인할 점은 무엇인가?'],
    evidence:pieces.map((part,index)=>({title:pieces.length===1?stem:`${stem} (${index+1}/${pieces.length})`,text:part,kind:'record',initially_released:true}))});
  return {name,cases:[draft],format:'text'};
}
export async function readCaseFile(file:Pick<File,'name'|'size'|'arrayBuffer'>):Promise<CaseFile>{
  if(file.size>MAX_FILE_BYTES)throw new Error('파일은 256KiB까지 선택할 수 있습니다. 사건별로 나누세요.');
  if(!/\.(txt|md|json)$/i.test(file.name))throw new Error('TXT·MD·JSON 파일을 선택하세요. PDF·HWP·DOCX는 현재 지원하지 않습니다.');
  const buffer=await file.arrayBuffer();
  if(buffer.byteLength>MAX_FILE_BYTES)throw new Error('파일은 256KiB까지 선택할 수 있습니다.');
  let raw:string;
  try{raw=new TextDecoder('utf-8',{fatal:true}).decode(buffer);}catch{throw new Error('UTF-8 텍스트를 읽지 못했습니다. 파일을 UTF-8로 다시 저장하세요.');}
  return parseCaseFile(file.name,raw);
}
