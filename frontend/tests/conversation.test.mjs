import {test} from 'node:test';
import assert from 'node:assert/strict';
import {ApiError} from '../src/api.ts';
import {ConversationController,validTurn} from '../src/conversation.ts';
const id='JOB-'+ 'a'.repeat(16),rid='b'.repeat(32);
const turn=(extra={})=>({id,case_id:'CASE-A',kind:'conversation',version:1,question:'자료를 설명해줘',request_id:rid,status:'COMPLETED',created:1,error:null,result:{conversation:{status:'INSUFFICIENT',paragraphs:[],missing_information:['추가 자료'],follow_up_questions:[],history_turn_ids:[],history_turns_omitted:0},provenance:'deterministic_fixture',limitations:[]},...extra});
const page=(turns=[],extra={})=>({case_id:'CASE-A',evidence_version:1,turns,latest_turn_id:turns.at(-1)?.id||null,next_before:null,...extra});
const deferred=()=>{let resolve;const promise=new Promise(r=>{resolve=r;});return {promise,resolve};};
const controller=api=>new ConversationController(api,'CASE-A',1,()=>{},()=>rid,100000);

test('one double-click write is tied to history and draft clears only after acknowledged result',async()=>{
  const pending=deferred();const writes=[];let saved=false;
  const c=controller(async(_path,options)=>{if(options?.method==='POST'){writes.push(JSON.parse(options.body));return pending.promise;}return saved?page([turn()]):page();});
  await c.refresh();const send=c.send('  자료를 설명해줘  ');await c.send('duplicate');
  assert.equal(writes.length,1);assert.equal(c.state.acknowledgements,0);
  saved=true;pending.resolve(turn());await send;
  assert.equal(c.state.acknowledgedQuestion,'자료를 설명해줘');assert.equal(c.state.latestTurnId,id);assert.equal(c.state.pending,null);
  assert.deepEqual(writes[0],{request_id:rid,question:'자료를 설명해줘',evidence_version:1,after_turn_id:null});c.dispose();
});

test('timeout never retries automatically and manual recovery preserves exact request ID and payload',async()=>{
  const writes=[];let attempt=0,saved=false;
  const c=controller(async(_path,options)=>{if(options?.method==='POST'){writes.push(JSON.parse(options.body));if(++attempt===1)throw new ApiError('REQUEST_TIMEOUT');saved=true;return turn();}return saved?page([turn()]):page();});
  await c.refresh();await c.send('자료를 설명해줘');await c.send('different question');
  assert.equal(writes.length,1);assert.equal(c.state.acknowledgements,0);assert.ok(c.state.pending);assert.equal(c.state.ready,false);
  await c.retryPending();assert.equal(writes.length,2);assert.deepEqual(writes[0],writes[1]);assert.equal(c.state.acknowledgements,1);c.dispose();
});

test('readback can acknowledge committed timeout without a second model POST',async()=>{
  let writes=0,saved=false;
  const c=controller(async(_path,options)=>{if(options?.method==='POST'){writes++;saved=true;throw new ApiError('NETWORK_ERROR');}return saved?page([turn()]):page();});
  await c.refresh();await c.send('자료를 설명해줘');await c.refresh();assert.equal(writes,1);assert.equal(c.state.pending,null);assert.equal(c.state.acknowledgements,1);c.dispose();
});

test('wrong-case, wrong-version and malformed results never enable sending or acknowledge a write',async()=>{
  for(const value of [page([],{case_id:'CASE-B'}),page([],{evidence_version:2}),page([turn({kind:'analysis'})])]){
    let writes=0;const c=controller(async(_path,options)=>{if(options?.method==='POST')writes++;return value;});
    await c.refresh();await c.send('no');assert.equal(c.state.ready,false);assert.equal(writes,0);c.dispose();
  }
  const c=controller(async(_path,options)=>options?.method==='POST'?turn({case_id:'CASE-B'}):page());
  await c.refresh();await c.send('자료를 설명해줘');assert.ok(c.state.pending);assert.equal(c.state.acknowledgements,0);c.dispose();
  assert.equal(validTurn(turn({result:null}),'CASE-A'),false);
});

test('leaving the case discards late reads and write acknowledgements',async()=>{
  const pending=deferred();let changes=0;
  const c=new ConversationController(async()=>pending.promise,'CASE-A',1,()=>changes++,()=>rid,100000);
  const reading=c.refresh();c.dispose();const atDispose=changes;pending.resolve(page([turn()]));await reading;
  assert.equal(changes,atDispose);assert.equal(c.state.turns.length,0);
});

test('a newer evidence version cannot be overwritten by an older in-flight page',async()=>{
  const old=deferred();let reads=0;
  const c=controller(async()=>++reads===1?old.promise:page([],{evidence_version:2}));
  const read=c.refresh();c.setVersion(2);await new Promise(r=>setImmediate(r));old.resolve(page([turn()]));await read;
  assert.equal(c.state.turns.length,0);assert.equal(c.state.ready,true);c.dispose();
});
