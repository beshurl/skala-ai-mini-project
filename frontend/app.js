/* Vue workspace. Only FinalAnswer renders a diagnosis; drafts stay internal. */
const { createApp, ref, computed, nextTick } = Vue;
const STORAGE = 'incident-workspace-v2';
function readLocal(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } }
function writeLocal(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* Server history remains available for this session. */ } }
const eventNames = {TargetResolved:'조사 대상 확인', PlanCreated:'전문 분석 계획 수립', ProcedureLoaded:'MCP 표준 절차 확인',ProcedureUnavailable:'기본 조사 절차 적용',ResearchCompleted:'시스템별 조사 완료',InvestigationStarted:'경쟁 가설 조사 시작',ProbePlanned:'반증 질문 선택',ProbeObserved:'추가 관측 수집',HypothesesUpdated:'사전 조건과 관측 대조',InvestigationStopped:'추가 조사 종료',EvidenceReady:'보고서 근거 구성',DraftWritten:'내부 보고서 작성',Validation:'시스템·수치·출처 검증',Finalize:'최종 보고서 확정'};
const InvestigationPanel = {
  props:{board:Object,compact:Boolean},
  methods:{tone(s){return ['supported','pending'].includes(s)?'success':s==='conflicted'?'danger':'warning';},signal(s){return {support:'지지',against:'반증',unknown:'판단 보류'}[s]||s;},before(step,id){return step.before.find(h=>h.id===id)?.status_label||'미확인';},stepStatus(step){return step.observation?.status==='failed'?'조회 실패':step.observation?.data?.available===false?'자료 없음':step.status==='completed'?'관측 대조 완료':step.status==='observed'?'가설 판단 중':'추가 근거 조회 중';}},
  template:`<section v-if="board?.hypotheses?.length" :class="['investigation-board',{compact}]" aria-label="반증 우선 추가 조사">
    <div class="investigation-heading"><h3>가설을 구별하는 추가 조사</h3><span class="badge">{{ board.used }} / {{ board.budget }}회</span></div>
    <p class="investigation-explainer">먼저 판정 조건을 정하고, 새 관측으로 지지·반증을 대조합니다.</p>
    <ul v-if="compact" class="hypothesis-mini"><li v-for="h in board.hypotheses" :key="h.id"><span><small>{{ h.target }}</small>{{ h.title }}</span><strong :class="tone(h.status)">{{ h.status_label }}</strong></li></ul>
    <div v-else class="hypothesis-rows"><div v-for="h in board.hypotheses" :key="h.id" class="hypothesis-row"><div class="hypothesis-title"><span>{{ h.target }}</span><strong>{{ h.title }}</strong><b :class="tone(h.status)">{{ h.status_label }}</b></div><ul class="hypothesis-evidence"><li v-for="e in h.support" :key="e.evidence_id">지지 · {{ e.detail }}<small>{{ e.evidence_id }}</small></li><li v-for="e in h.against" :key="e.evidence_id">반증 · {{ e.detail }}<small>{{ e.evidence_id }}</small></li><li v-if="!h.support.length&&!h.against.length" class="subtle">{{ h.unknown.length?'자료가 부족해 판단을 보류합니다.':'아직 이 가설의 구별 근거를 조회하지 않았습니다.' }}</li></ul></div></div>
    <ol class="probe-timeline"><li v-for="step in board.steps" :key="step.probe_id"><details :open="step.round===board.steps.length"><summary><span class="probe-round">{{ step.round }}차</span>{{ step.title }}<small>{{ step.target }} · {{ stepStatus(step) }}</small></summary><div class="probe-reason"><strong>왜 이 조사를 하나요?</strong><p>{{ step.reason }}</p></div><div class="probe-prediction"><strong>조회 전에 정한 조건</strong><p>{{ step.prediction }}</p><p class="subtle">{{ step.otherwise }}</p></div><div v-if="step.observation" class="probe-observation"><strong>확인한 결과</strong><p v-if="step.observation.status==='failed'" class="warning">{{ step.observation.error }} · 기존 근거는 유지합니다.</p><p v-else-if="!step.observation.data.available" class="warning">{{ step.observation.data.missing_reason }}</p><ul v-else><li v-for="outcome in step.outcomes" :key="outcome.hypothesis_id"><span :class="tone(outcome.status)">{{ signal(outcome.signal) }}</span> · {{ outcome.title }}<p>{{ outcome.detail }}</p><small>{{ before(step,outcome.hypothesis_id) }} → {{ outcome.status_label }}</small></li></ul><small class="probe-source">{{ step.evidence_id }}</small></div><p class="probe-method">{{ step.planner_mode==='actual-llm'?'실제 LLM이 질문 선택':'테스트용 결정론 선택' }} · 판정은 관측 조건으로 계산{{ step.reused?' · 저장한 관측 재사용':'' }}</p></details></li></ol>
    <p v-if="board.stop_reason" class="investigation-stop" role="status">{{ board.stop_reason }}</p>
    <p v-if="board.planner_error" class="warning">{{ board.planner_error }}</p>
    <p class="investigation-footnote">5분 구간의 교육용 합성 관측 · 교차 지지는 인과관계 확정을 뜻하지 않습니다.</p>
  </section>`
};
createApp({setup(){
  const tabs=[{id:'investigate',label:'장애 조사',icon:'⌕'},{id:'history',label:'문의 기록',icon:'≡'},{id:'evaluation',label:'개선 전후 평가',icon:'⇄'}];
  const specialistList=[{key:'metrics',label:'지표 분석',icon:'⌁'},{key:'logs',label:'로그 분석',icon:'≡'},{key:'runbooks',label:'런북 검색',icon:'⌕'}];
  const view=ref('investigate'),systems=ref([]),selected=ref([]),health=ref(null),catalogError=ref('');
  const mode=ref('helpdesk'),scenario=ref('stable'),evidenceCase=ref('batch'),input=ref(''),onset=ref(''),errorMessage=ref('');
  const investigation=ref(null),investigationEvaluation=ref(null);
  const composerExpanded=ref(true);
  const contextRecord=ref(null);
  const log=ref([]),records=ref([]),events=ref([]),specialistStatus=ref({}),latestValidation=ref(null);
  const sending=ref(false),requestError=ref(''),logEl=ref(null),lastRequest=ref(null),workflowStatus=ref('waiting');
  const evaluation=ref(null),evaluationError=ref(''),liveEvaluation=ref(null),liveEvaluationError=ref('');
  const judgeDimensions={groundedness:'근거 충실성',numerical_accuracy:'수치 정확성',action_conditions:'조치 조건',request_fulfillment:'요청 충족',next_action:'다음 행동'};
  const thread=ref(readLocal(STORAGE+':thread',null)||crypto.randomUUID());
  const savedSessions=ref(readLocal(STORAGE+':sessions',[]));
  let controller=null, counter=0, abortReason='';
  const backendLabel=computed(()=>health.value ? (health.value.llm_backend==='fake' ? '결정론 데모':'실제 LLM · '+health.value.quality_llm) : '연결 대기');
  const taskEvents=computed(()=>{const m=new Map();for(const e of events.value)if(['TaskCompleted','TaskFailed'].includes(e.type))m.set(e.id||e.target,e);return [...m.values()];});
  function saveSessionLabel(label){
    const existing=savedSessions.value.find(s=>s.id===thread.value);
    if(!existing)savedSessions.value.unshift({id:thread.value,label:label||'새 대화'});
    else if(label)existing.label=label.slice(0,45);
    savedSessions.value=savedSessions.value.slice(0,15);
    writeLocal(STORAGE+':thread',thread.value);writeLocal(STORAGE+':sessions',savedSessions.value);
  }
  saveSessionLabel();
  async function api(path){const r=await fetch(path);if(!r.ok)throw new Error((await r.json()).detail||'서버 응답 오류');return r.json();}
  async function loadHealth(){catalogError.value='';try{const [h,s]=await Promise.all([api('/health'),api('/systems')]);health.value=h;systems.value=s.systems;selected.value=selected.value.filter(s=>systems.value.includes(s));}catch(e){health.value=null;catalogError.value='시스템 목록을 불러오지 못했습니다. '+e.message;}}
  async function restore(){
    try{
      const requestedThread=thread.value;
      const session=await api('/sessions/'+encodeURIComponent(requestedThread));if(requestedThread!==thread.value)return;records.value=session.records;
      const byId=new Map(records.value.map(r=>[r.id,r]));const byReply=new Map();
      for(const record of records.value){if(!byReply.has(record.result.final))byReply.set(record.result.final,[]);byReply.get(record.result.final).push(record);}
      log.value=[...session.messages].reverse().map(m=>{let record=null;if(m.role==='assistant'){const matches=byReply.get(m.content)||[];record=m.record_id?byId.get(m.record_id):matches.shift();if(m.record_id){const i=matches.findIndex(r=>r.id===m.record_id);if(i>=0)matches.splice(i,1);}}return {...m,id:counter++,report:record?.result.report,validation:record?.result.validation,record_id:record?.id};}).reverse();
      composerExpanded.value=!log.value.length;
      selected.value=(session.context?.targets||[]).filter(s=>systems.value.includes(s));
      onset.value=session.context?.details?.onset||'';errorMessage.value=session.context?.details?.error_message||'';
      const latest=records.value[0];
      contextRecord.value=latest?.result?.report?latest.id:null;
      mode.value=latest?.mode||session.context?.pending?.mode||'helpdesk';scenario.value=latest?.result?.scenario||'stable';workflowStatus.value=latest?.status||'waiting';
      evidenceCase.value=latest?.result?.evidence_case||session.context?.pending?.evidence_case||'batch';investigation.value=latest?.result?.investigation||null;
      if(latest){latestValidation.value=latest.result.validation;events.value=latest.result.events||[];reconstructStatuses(latest.result.collected||[]);}else{latestValidation.value=null;events.value=[];specialistStatus.value={};}
      if(latest){await nextTick();document.getElementById('record-'+latest.id)?.scrollIntoView({block:'start',behavior:'auto'});}else await scroll();
    }catch(e){requestError.value='기록을 불러오지 못했습니다. '+e.message;}
  }
  function reconstructStatuses(collected){const mapping={monitoring:'metrics',snapshot:'metrics',logs:'logs',runbook:'runbooks'};const groups={};for(const c of collected){const k=mapping[c.source];if(k)(groups[k]??=[]).push(c.status);}specialistStatus.value=Object.fromEntries(Object.entries(groups).map(([k,ss])=>[k,ss.every(s=>s==='completed')?'completed':ss.every(s=>s==='failed')?'failed':'partial']));}
  async function scroll(){await nextTick();if(logEl.value)logEl.value.scrollTop=logEl.value.scrollHeight;}
  function example(text,targets){composerExpanded.value=true;input.value=text;selected.value=targets;mode.value='helpdesk';nextTick(()=>document.getElementById('question')?.focus());}
  function deploymentExample(){composerExpanded.value=true;mode.value='deployment';scenario.value='cpu-rise';selected.value=['web-01'];input.value='web-01 배포 전후 CPU와 알림 변화를 점검해주세요.';nextTick(()=>document.getElementById('question')?.focus());}
  function investigationExample(){evidenceCase.value='traffic';example('payments-service CPU가 91%이고 중복 배치 경고가 있습니다. 배치가 정말 원인인지 다른 가설과 구별해주세요.',['payments-service']);onset.value='2026-10-21 09:00~09:05';errorMessage.value='응답 지연';}
  function newChat(){contextRecord.value=null;composerExpanded.value=true;lastRequest.value=null;investigation.value=null;workflowStatus.value='waiting';thread.value=crypto.randomUUID();log.value=[];records.value=[];events.value=[];specialistStatus.value={};latestValidation.value=null;selected.value=[];onset.value='';errorMessage.value='';input.value='';requestError.value='';view.value='investigate';saveSessionLabel();}
  async function switchSession(id){if(sending.value)return;contextRecord.value=null;investigation.value=null;lastRequest.value=null;workflowStatus.value='waiting';thread.value=id;events.value=[];specialistStatus.value={};latestValidation.value=null;requestError.value='';saveSessionLabel();await restore();}
  function processEvent(e,assistantRef){
    if(e.type==='AnswerToken')return;
    if(e.investigation)investigation.value=e.investigation;
    if(e.type==='FinalAnswer'){
      const item={id:counter++,role:'assistant',content:e.reply,report:e.report,validation:e.validation,record_id:e.metadata?.record_id};
      log.value.push(item);assistantRef.done=true;assistantRef.recordId=item.record_id;workflowStatus.value=e.metadata?.status||'completed';
      if(workflowStatus.value==='rejected'){assistantRef.rejected=true;composerExpanded.value=true;return;}
      latestValidation.value=e.validation;
      if(e.events?.length)events.value=e.events;
      investigation.value=e.report?.investigation||null;
      contextRecord.value=e.report?item.record_id:null;
      return;
    }
    events.value.push(e);
    if(e.type==='SpecialistStatus')specialistStatus.value={...specialistStatus.value,[e.specialist]:e.status};
    if(e.type==='Validation')latestValidation.value={passed:e.verdict==='합격',attempts:e.attempt,rewrites:e.attempt-1,errors:e.errors||[],checks:['시스템명','수치','상태·알림','근거 ID','조치 조건','필수 항목']};
    if(e.type==='Error'){requestError.value=e.message;workflowStatus.value='failed';}
  }
  async function sendRequest(body,showUser=true){
    if(sending.value||body.thread_id!==thread.value)return;sending.value=true;investigation.value=null;workflowStatus.value='running';abortReason='';requestError.value='';events.value=[];specialistStatus.value={};latestValidation.value=null;
    composerExpanded.value=false;
    lastRequest.value=body;if(showUser)log.value.push({id:counter++,role:'user',content:body.message});
    await scroll();controller=new AbortController();const timer=setTimeout(()=>{abortReason='timeout';controller?.abort();},190000);
    const completion={done:false,recordId:null,rejected:false};let doneMarker=false;
    try{
      const response=await fetch('/chat/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:controller.signal});
      if(!response.ok||!response.body)throw new Error('서버 요청 실패 ('+response.status+')');
      const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
      function consume(block){const data=block.split('\n').filter(l=>l.startsWith('data:')).map(l=>l.slice(5).trimStart()).join('\n');if(!data)return;if(data==='[DONE]'){doneMarker=true;return;}processEvent(JSON.parse(data),completion);}
      while(true){const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true}).replace(/\r\n/g,'\n');let boundary;while((boundary=buffer.indexOf('\n\n'))>=0){consume(buffer.slice(0,boundary));buffer=buffer.slice(boundary+2);}if(!completion.done)await scroll();}
      buffer+=decoder.decode();if(buffer.trim())consume(buffer);
      if(!completion.done&&!requestError.value)throw new Error(doneMarker?'보고서가 완료되지 않았습니다.':'연결이 끊겨 결과를 받지 못했습니다.');
      if(completion.rejected){input.value=body.message;lastRequest.value=null;}else if(completion.done)saveSessionLabel(body.message);
      const session=await api('/sessions/'+encodeURIComponent(thread.value));records.value=session.records;
    }catch(e){const aborted=controller?.signal.aborted;workflowStatus.value=aborted&&abortReason==='cancel'?'interrupted':'failed';requestError.value=aborted?(abortReason==='timeout'?'처리 시간이 초과되었습니다. 서버 연결을 확인한 뒤 다시 시도하세요.':'요청을 중단했습니다. 저장된 확인 결과는 문의 기록에서 확인하세요.'):(e?.message||String(e));}
    finally{clearTimeout(timer);sending.value=false;controller=null;if(completion.done&&completion.recordId){await nextTick();document.getElementById('record-'+completion.recordId)?.scrollIntoView({block:'start',behavior:'auto'});}else await scroll();}
  }
  async function send(){const text=input.value.trim();if(!text||sending.value||!health.value)return;input.value='';await sendRequest({message:text,thread_id:thread.value,targets:[...selected.value],mode:mode.value,scenario:scenario.value,evidence_case:evidenceCase.value,context_record_id:contextRecord.value,details:{onset:onset.value,error_message:errorMessage.value}});}
  async function retryRequest(){if(lastRequest.value?.thread_id===thread.value)await sendRequest(lastRequest.value,false);}
  async function retryFailed(item){const record=records.value.find(r=>r.id===item.record_id);if(!record)return;await sendRequest({message:item.report.question,thread_id:thread.value,targets:item.report.targets,mode:record.mode,scenario:record.result.scenario||'stable',evidence_case:record.result.evidence_case||'batch',details:{onset:onset.value,error_message:errorMessage.value},retry_record_id:item.record_id});}
  function cancel(){abortReason='cancel';controller?.abort();}
  async function expandComposer(){composerExpanded.value=true;await nextTick();document.getElementById('question')?.focus();}
  function showInvestigation(id){document.getElementById('investigation-'+id)?.scrollIntoView({block:'start',behavior:'auto'});}
  async function openRecord(record){
    view.value='investigate';mode.value=record.mode;scenario.value=record.result.scenario||'stable';workflowStatus.value=record.status;
    evidenceCase.value=record.result.evidence_case||'batch';investigation.value=record.result.investigation||null;
    contextRecord.value=record.result.report?record.id:null;selected.value=[...record.targets];onset.value=record.result.details?.onset||'';errorMessage.value=record.result.details?.error_message||'';
    if(!log.value.some(l=>l.record_id===record.id))log.value.push({id:counter++,role:'assistant',content:record.result.final,report:record.result.report,validation:record.result.validation,record_id:record.id});
    events.value=record.result.events||[];latestValidation.value=record.result.validation;reconstructStatuses(record.result.collected||[]);
    await nextTick();const anchor=document.getElementById('record-'+record.id);anchor?.scrollIntoView({block:'start',behavior:'auto'});anchor?.focus({preventScroll:true});
  }
  function onQuestionKeydown(event){if(event.key==='Enter'&&!event.shiftKey&&!event.ctrlKey&&!event.metaKey&&!event.altKey&&!event.isComposing&&event.keyCode!==229){event.preventDefault();send();}}

  function downloadReport(item){const blob=new Blob([item.content],{type:'text/plain;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='incident-report-'+(item.record_id||'result')+'.txt';a.click();URL.revokeObjectURL(url);}
  async function loadEvaluation(){await Promise.all([
    (async()=>{try{evaluation.value=await api('/evaluation');evaluationError.value='';}catch{evaluation.value=null;evaluationError.value='저장된 개선 전후 비교가 없습니다.';}})(),
    (async()=>{try{liveEvaluation.value=await api('/evaluation/live');liveEvaluationError.value='';}catch{liveEvaluation.value=null;liveEvaluationError.value='실제 모델 평가 결과를 불러오지 못했습니다. 서버 연결을 확인하거나 평가를 실행한 뒤 새로고침하세요.';}})()
    ,(async()=>{try{investigationEvaluation.value=await api('/evaluation/investigation');}catch{investigationEvaluation.value=null;}})()
  ]);}
  const verdictClass=v=>v==='정상'?'success':v==='주의'?'warning':'danger';
  const statusLabel=s=>({waiting:'요청 대기',running:'조회 중',completed:'완료',partial:'일부 실패',failed:'실패',rejected:'입력 거절 · 0토큰',needs_clarification:'대상 확인 필요',validation_failed:'검증 미통과',interrupted:'중단'}[s]||s);
  const sourceLabel=s=>({monitoring:'모니터링',snapshot:'배포 스냅샷',logs:'로그',runbook:'런북',diagnostic:'가설 구별 관측'}[s]||s);
  const phaseLabel=p=>({before:'배포 전',after:'배포 후'}[p]||'조회 시점');
  const delta=n=>typeof n==='number'?(n>0?'+':'')+n:'—';
  const formatDate=t=>new Intl.DateTimeFormat('ko-KR',{dateStyle:'medium',timeStyle:'short',timeZone:'Asia/Seoul'}).format(new Date(t));
  const eventLabel=e=>e.type==='InputRejected'?'입력 거절 · LLM 미호출 (0토큰)':e.type==='SpecialistStatus'?`${specialistList.find(s=>s.key===e.specialist)?.label}: ${statusLabel(e.status)}`:(eventNames[e.type]||e.type)+(e.type==='Validation'?` · ${e.attempt}차 ${e.verdict}`:'');
  (async()=>{await loadHealth();await restore();await loadEvaluation();})();
  return {tabs,specialistList,view,systems,selected,health,catalogError,mode,scenario,evidenceCase,investigation,investigationEvaluation,composerExpanded,expandComposer,showInvestigation,input,onset,errorMessage,log,records,events,workflowStatus,specialistStatus,latestValidation,sending,requestError,logEl,lastRequest,evaluation,evaluationError,liveEvaluation,liveEvaluationError,judgeDimensions,thread,savedSessions,backendLabel,taskEvents,loadHealth,restore,example,deploymentExample,investigationExample,newChat,switchSession,send,onQuestionKeydown,retryRequest,retryFailed,cancel,openRecord,downloadReport,loadEvaluation,verdictClass,statusLabel,sourceLabel,phaseLabel,delta,formatDate,eventLabel};
}}).component('investigation-panel',InvestigationPanel).mount('#app');
