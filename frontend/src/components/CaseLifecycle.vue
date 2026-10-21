<!--
THESIS: 사건 검토를 방해하지 않는 명시적 종료·보존 설정.
OWN-WORLD: 기존 차콜·웜 골드 토큰과 기본 조작부를 그대로 사용한다.
STORY: 현재 상태를 읽고 사유와 함께 한 번 변경한 뒤 서버 상태를 확인한다.
FIRST VIEWPORT: 증거·분석 위의 접힌 한 줄, 오류와 종료 안내는 항상 보인다.
FORM: 기존 작업실의 국소 확장. 새로운 시각 방향이나 seed를 사용하지 않는다.
-->
<script setup lang="ts">
import {computed,nextTick,onBeforeUnmount,ref,watch} from 'vue';
import {createLifecycleController} from '../lifecycle';
import type {LifecycleAction} from '../lifecycle';
import type {CaseLifecycle} from '../types';
const props=defineProps<{caseId:string;evidenceVersion:number;refreshKey:number;api:(path:string,options?:{method?:string;body?:string})=>Promise<unknown>;active:boolean;busy:boolean;readOnly?:boolean}>();
const emit=defineEmits<{
  state:[{caseId:string;data:CaseLifecycle|null}];
  pending:[{caseId:string;busy:boolean}];
  refreshCase:[];
}>();
const controller=createLifecycleController((path,options)=>props.api(path,options));
const state=controller.state;
const opened=ref(false), action=ref<LifecycleAction|''>(''),reason=ref(''),message=ref<HTMLElement|null>(null);
const labels:Record<LifecycleAction,string>={close:'사건 종료',reopen:'검토 재개',hold:'보존 보류',release_hold:'보존 보류 해제'};
const help:Record<LifecycleAction,string>={
  close:'종료하면 새 분석과 증거 공개가 잠깁니다. 이전 분석과 공개 증거는 계속 볼 수 있습니다.',
  reopen:'새 분석과 증거 공개를 다시 허용합니다. 이후 다시 종료한 날짜가 보존기간의 새 기준이 됩니다.',
  hold:'이 사건과 이 사건을 포함하는 이전 백업을 만료 대상에서 제외합니다.',
  release_hold:'이 사건의 보존 보류를 해제합니다. 별도로 보류된 백업은 운영자의 확인이 더 필요할 수 있습니다.',
};
const choices=computed<LifecycleAction[]>(()=>state.data ? [state.data.closed_at?'reopen':'close',state.data.hold?'release_hold':'hold'] : []);
const changedVersion=computed(()=>!!state.data && state.data.evidence_version!==props.evidenceVersion);
const reasonLength=computed(()=>[...reason.value.trim()].length);
const locked=computed(()=>props.readOnly || props.busy || state.loading || state.saving || !state.data || changedVersion.value);
const closeBlocked=computed(()=>action.value==='close' && props.active);
const status=computed(()=>state.loading?'상태 확인 중':!state.data?'상태 확인 필요':`${state.data.closed_at?'종료 사건':'진행 사건'}${state.data.hold?' · 보존 보류 중':''}`);
const date=(value:string|null)=>value ? new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',dateStyle:'medium',timeStyle:'short'}).format(new Date(value)):'기록 없음';
watch(()=>props.caseId,id=>{action.value='';reason.value='';opened.value=false;void controller.select(id);},{immediate:true});
watch(()=>[props.evidenceVersion,props.refreshKey],()=>{action.value='';void controller.refresh();});
watch(()=>state.data,data=>emit('state',{caseId:props.caseId,data}),{immediate:true});
watch(()=>state.saving,busy=>emit('pending',{caseId:props.caseId,busy}),{immediate:true});
watch(()=>state.error,value=>{if(value) opened.value=true;});
watch(choices,available=>{if(action.value && !available.includes(action.value)) action.value='';});
async function submit() {
  if(!action.value || locked.value || closeBlocked.value) return;
  const success=await controller.submit(action.value,reason.value,props.evidenceVersion);
  action.value='';
  if(success) reason.value='';
  await nextTick();message.value?.focus();
}
onBeforeUnmount(()=>controller.dispose());
</script>

<template>
  <section class="case-lifecycle" aria-labelledby="lifecycle-heading">
    <h2 id="lifecycle-heading" class="sr-only">사건 관리</h2>
    <details :open="opened" @toggle="opened=($event.target as HTMLDetailsElement).open">
      <summary><span>사건 관리</span><span class="lifecycle-state" role="status">{{status}}</span></summary>
      <div class="lifecycle-body">
        <div class="lifecycle-overview">
          <dl v-if="state.data"><div><dt>생성</dt><dd>{{date(state.data.created_at)}}</dd></div><div><dt>종료</dt><dd>{{date(state.data.closed_at)}}</dd></div></dl>
          <button type="button" class="rc-button" :disabled="props.busy || state.loading || state.saving" @click="controller.refresh">{{state.loading?'상태 확인 중…':'상태 다시 확인'}}</button>
        </div>
        <p class="lifecycle-note">현재 자동 삭제는 꺼져 있습니다. 상태를 변경해도 기록을 삭제하지 않습니다.</p>
        <p v-if="state.data?.data_class==='unclassified'" class="lifecycle-note">이전 사건의 생성 시각·출처는 미확정 상태로 보존합니다. 자동 만료 대상으로 처리하지 않습니다.</p>
        <form @submit.prevent="submit">
          <fieldset :disabled="locked">
            <legend class="sr-only">종료·보존 상태 변경</legend>
            <div class="lifecycle-fields">
              <div><label for="lifecycle-action">변경할 상태</label><select id="lifecycle-action" v-model="action" required><option disabled value="">선택하세요</option><option v-for="item in choices" :key="item" :value="item" :disabled="item==='close' && active">{{labels[item]}}</option></select></div>
              <div><label for="lifecycle-reason">변경 사유 <span>(필수)</span></label><textarea id="lifecycle-reason" v-model="reason" rows="3" required aria-describedby="lifecycle-reason-help lifecycle-reason-count" :aria-invalid="reasonLength>500 || undefined"/><div class="lifecycle-reason-meta"><p id="lifecycle-reason-help">사유는 변경 이력에 저장됩니다. 1~500자로 입력하세요.</p><span id="lifecycle-reason-count">{{reasonLength}} / 500자</span></div></div>
            </div>
            <p v-if="action" class="lifecycle-help">{{help[action]}}</p>
            <p v-if="active" class="lifecycle-note">진행 중인 분석이 있어 사건 종료는 잠겨 있습니다. 보존 보류는 설정할 수 있습니다.</p>
            <button type="submit" class="rc-button rc-button--primary" :disabled="locked || !action || !reasonLength || reasonLength>500 || closeBlocked">{{state.saving?'상태 저장 중…':action?labels[action]:'상태 변경'}}</button>
          </fieldset>
        </form>
      </div>
    </details>
    <div v-if="state.error || state.notice" ref="message" tabindex="-1" class="lifecycle-message">
      <p v-if="state.error" role="alert">{{state.error}}</p>
      <p v-if="state.notice" role="status">{{state.notice}}</p>
    </div>
    <p v-if="changedVersion" class="lifecycle-guard" role="status">새 증거가 공개되었습니다. <button type="button" class="rc-button" :disabled="props.busy || state.saving" @click="emit('refreshCase')">사건 내용 새로고침</button></p>
    <p v-if="state.data?.closed_at && !props.readOnly" class="lifecycle-guard" role="status">종료된 사건입니다. 새 분석과 증거 공개를 하려면 사건 관리에서 검토를 재개하세요.</p>
    <p v-else-if="!state.data && !state.loading" class="lifecycle-guard">사건 상태를 확인한 뒤 분석·증거 공개를 진행할 수 있습니다.</p>
  </section>
</template>

<style scoped>
.case-lifecycle{margin-block:8px 28px;min-width:0}.case-lifecycle details{background:var(--panel);border-radius:var(--radius)}summary{padding:12px 16px;font-size:13px;min-height:48px;overflow-wrap:anywhere}summary>span:first-child{font-weight:600;margin-inline-end:20px}.lifecycle-state{color:var(--muted)}.lifecycle-body{padding:8px 20px 20px}.lifecycle-overview{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}dl{display:flex;gap:24px;flex-wrap:wrap;margin:0}dl>div{display:flex;gap:12px;align-items:baseline}dt{color:var(--muted);font-size:12px}dd{margin:0;font-size:13px}.lifecycle-note,.lifecycle-help{font-size:13px;line-height:1.8;max-width:75ch;margin-block:12px;color:var(--muted)}fieldset{padding:0;border:0;margin:20px 0 0;min-inline-size:0}.lifecycle-fields{display:grid;grid-template-columns:minmax(140px,1fr) minmax(0,3fr);gap:24px}.lifecycle-fields>div{min-width:0}label{display:block;font-size:13px;font-weight:600;margin-block-end:8px}label span{color:var(--muted);font-weight:400}select,textarea{width:100%;min-width:0;padding:10px 12px;border:1px solid var(--line-strong);border-radius:var(--radius);background:var(--bg);color:var(--text);font:inherit;font-size:14px;line-height:1.6}select{min-height:46px}textarea{resize:vertical;min-height:96px;overflow-wrap:anywhere}textarea:focus-visible{outline:2px solid var(--accent);outline-offset:4px}.lifecycle-reason-meta{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;color:var(--muted);font-size:12px;line-height:1.7;margin-block-start:6px}.lifecycle-reason-meta p{margin:0}.lifecycle-fields+button{margin-block-start:20px}.lifecycle-message{margin-block-start:12px;padding:12px 16px;background:var(--surface-raised);border-radius:var(--radius);font-size:13px;overflow-wrap:anywhere}.lifecycle-message p{margin:0}.lifecycle-message p+p{margin-block-start:8px}.lifecycle-message [role=alert]{color:var(--danger)}.lifecycle-guard{margin-block:12px 0;font-size:13px;color:var(--warning);line-height:1.8}.lifecycle-guard button{margin-inline-start:8px}.lifecycle-help+button,.lifecycle-note+button{margin-block-start:12px}@media(max-width:600px){.lifecycle-fields{grid-template-columns:minmax(0,1fr);gap:16px}.lifecycle-body{padding:4px 16px 16px}summary>span:first-child{margin-inline-end:12px}.lifecycle-overview{align-items:flex-start}dl{gap:8px;flex-direction:column}.lifecycle-guard button{margin-inline-start:0;margin-block-start:8px;display:flex}form button[type=submit]{width:100%}}
</style>
