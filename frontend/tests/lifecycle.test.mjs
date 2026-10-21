import {test} from 'node:test';
import assert from 'node:assert/strict';
import {ApiError} from '../src/api.ts';
import {createLifecycleController} from '../src/lifecycle.ts';

const example=(case_id='CASE-A',extra={})=>({case_id,created_at:'2026-10-20T00:00:00Z',closed_at:null,hold:false,data_class:'synthetic_fixture',revision:1,evidence_version:1,...extra});
const deferred=()=>{let resolve;const promise=new Promise(r=>{resolve=r;});return {promise,resolve};};

test('double submission sends one version-bound write and reads confirmed server state',async()=>{
  const pending=deferred(),writes=[];
  const controller=createLifecycleController(async(path,options)=>{
    if(options?.method==='POST'){writes.push({path,body:JSON.parse(options.body)});return pending.promise;}
    return example();
  });
  await controller.select('CASE-A');
  const first=controller.submit('close','  합성 검토 완료  ',1);
  assert.equal(await controller.submit('close','중복 클릭',1),false);
  pending.resolve(example('CASE-A',{revision:2,closed_at:'2026-10-20T01:00:00Z'}));
  assert.equal(await first,true);
  assert.deepEqual(writes,[{path:'/api/cases/CASE-A/lifecycle',body:{action:'close',reason:'합성 검토 완료',evidence_version:1,lifecycle_revision:1}}]);
  assert.equal(controller.state.data.revision,2);
});

test('a timed-out write is never retried or reported successful even after committed readback',async()=>{
  let reads=0,writes=0;
  const controller=createLifecycleController(async(_path,options)=>{
    if(options?.method==='POST'){writes++;throw new ApiError('REQUEST_TIMEOUT');}
    return ++reads===1?example():example('CASE-A',{revision:2,closed_at:'2026-10-20T01:00:00Z'});
  });
  await controller.select('CASE-A');
  assert.equal(await controller.submit('close','검토 완료',1),false);
  assert.equal(writes,1);assert.equal(reads,2);
  assert.ok(controller.state.data.closed_at);
  assert.match(controller.state.error,/응답 시간이 초과/);
  assert.doesNotMatch(controller.state.notice,/사건을 종료했습니다/);
});

test('failed readback leaves changes unavailable until an explicit read-only refresh',async()=>{
  let reads=0,writes=0;
  const controller=createLifecycleController(async(_path,options)=>{
    if(options?.method==='POST'){writes++;throw new ApiError('NETWORK_ERROR');}
    if(++reads===2)throw new ApiError('NETWORK_ERROR');
    return example();
  });
  await controller.select('CASE-A');
  await controller.submit('hold','확인 중 보존',1);
  assert.equal(controller.state.data,null);
  assert.equal(await controller.submit('hold','다시 클릭',1),false);
  await controller.refresh();
  assert.equal(writes,1);assert.equal(reads,3);assert.equal(controller.state.data.case_id,'CASE-A');
});

test('old case read and write responses cannot overwrite a newly selected case',async()=>{
  const oldRead=deferred(),oldWrite=deferred();let first=true;
  const controller=createLifecycleController(async(path,options)=>{
    if(options?.method==='POST')return oldWrite.promise;
    if(path.includes('CASE-A') && first){first=false;return oldRead.promise;}
    return example(path.includes('CASE-A')?'CASE-A':'CASE-B');
  });
  const selection=controller.select('CASE-A');await controller.select('CASE-B');oldRead.resolve(example());await selection;
  assert.equal(controller.state.data.case_id,'CASE-B');
  await controller.select('CASE-A');const saving=controller.submit('close','이전 사건 종료',1);
  await controller.select('CASE-B');oldWrite.resolve(example('CASE-A',{closed_at:'2026-10-20T01:00:00Z',revision:2}));
  assert.equal(await saving,false);assert.equal(controller.state.data.case_id,'CASE-B');assert.equal(controller.state.notice,'');
});

test('invalid or wrong-case responses never enable a write',async()=>{
  for(const response of [example('CASE-B'),example('CASE-A',{hold:'false'}),example('CASE-A',{revision:0}),example('CASE-A',{closed_at:'2026-10-20'})]){
    let writes=0;
    const controller=createLifecycleController(async(_path,options)=>{if(options?.method==='POST')writes++;return response;});
    await controller.select('CASE-A');
    assert.equal(controller.state.data,null);assert.ok(controller.state.error);
    assert.equal(await controller.submit('close','검토 완료',1),false);assert.equal(writes,0);
  }
});

test('new evidence requires refreshed content and reason limits count Unicode code points',async()=>{
  let writes=0;
  const controller=createLifecycleController(async(_path,options)=>{
    if(options?.method==='POST'){writes++;const body=JSON.parse(options.body);assert.equal([...body.reason].length,500);return example('CASE-A',{evidence_version:2,hold:true,revision:2});}
    return example('CASE-A',{evidence_version:2});
  });
  await controller.select('CASE-A');
  assert.equal(await controller.submit('hold','새 증거 미확인',1),false);
  assert.equal(await controller.submit('hold','😀'.repeat(501),2),false);assert.equal(writes,0);
  assert.equal(await controller.submit('hold','😀'.repeat(500),2),true);assert.equal(writes,1);
});

test('a syntactically valid response that does not fulfill the action is not success',async()=>{
  let writes=0,reads=0;
  const controller=createLifecycleController(async(_path,options)=>{if(options?.method==='POST')writes++;else reads++;return example();});
  await controller.select('CASE-A');
  assert.equal(await controller.submit('hold','보존 요청',1),false);
  assert.equal(writes,1);assert.equal(reads,2);assert.equal(controller.state.data.hold,false);assert.ok(controller.state.error);
});
