import { reactive } from 'vue';
import { ApiError } from './api.ts';
import type { CaseLifecycle } from './types.ts';

export type LifecycleAction = 'close'|'reopen'|'hold'|'release_hold';
type Request = (path:string, options?:{method?:string;body?:string})=>Promise<unknown>;
const messages: Record<LifecycleAction,string> = {
  close:'사건을 종료했습니다. 이전 분석과 공개 증거는 계속 볼 수 있습니다.',
  reopen:'검토를 재개했습니다. 새 분석과 증거 공개를 진행할 수 있습니다.',
  hold:'보존을 보류했습니다. 이 사건을 포함하는 백업도 만료 대상에서 제외합니다.',
  release_hold:'이 사건의 보존 보류를 해제했습니다. 자동 삭제는 실행하지 않았습니다.',
};
function parsed(value: unknown, caseId:string):CaseLifecycle {
  const v = value as CaseLifecycle;
  const date = (s:unknown)=>s===null || typeof s==='string' && /(?:Z|[+-]\d{2}:\d{2})$/.test(s) && Number.isFinite(Date.parse(s));
  if (!v || v.case_id!==caseId || !date(v.created_at) || !date(v.closed_at)
    || typeof v.hold!=='boolean' || !['synthetic_fixture','unclassified'].includes(v.data_class)
    || !Number.isInteger(v.revision) || v.revision<1 || !Number.isInteger(v.evidence_version) || v.evidence_version<1)
    throw new ApiError('INVALID_RESPONSE');
  return v;
}
export function createLifecycleController(api:Request) {
  const state = reactive({caseId:'',data:null as CaseLifecycle|null,loading:false,saving:false,error:'',notice:''});
  let epoch = 0;
  const path = (id:string)=>`/api/cases/${encodeURIComponent(id)}/lifecycle`;
  async function select(caseId:string) {
    const token=++epoch;
    Object.assign(state,{caseId,data:null,loading:true,saving:false,error:'',notice:''});
    try {
      const data=parsed(await api(path(caseId)),caseId);
      if(token===epoch) state.data=data;
    } catch(error) {
      if(token===epoch) state.error=error instanceof Error ? error.message : '사건 상태를 확인하지 못했습니다.';
    } finally { if(token===epoch) state.loading=false; }
  }
  async function refresh() { if(!state.saving && state.caseId) await select(state.caseId); }
  async function submit(action:LifecycleAction, reason:string, evidenceVersion:number) {
    const before=state.data, target=state.caseId, token=epoch;
    if(state.loading || state.saving || !before) return false;
    if(before.evidence_version!==evidenceVersion) {
      state.error='새 증거가 공개되었습니다. 사건 내용을 새로고침한 뒤 상태를 변경하세요.'; return false;
    }
    if(!Object.hasOwn(messages,action) || !reason.trim() || [...reason.trim()].length>500) {
      state.error='변경할 상태와 사유를 확인하세요. 사유는 1~500자입니다.'; return false;
    }
    state.saving=true; state.error=''; state.notice='';
    try {
      const data=parsed(await api(path(target),{method:'POST',body:JSON.stringify({action,reason:reason.trim(),evidence_version:evidenceVersion,lifecycle_revision:before.revision})}),target);
      const matches={close:data.closed_at!==null,reopen:data.closed_at===null,hold:data.hold,release_hold:!data.hold}[action];
      if(!matches || data.revision<before.revision || data.evidence_version!==evidenceVersion) throw new ApiError('INVALID_RESPONSE');
      if(token!==epoch) return false;
      state.data=data; state.notice=messages[action]; return true;
    } catch(error) {
      if(token!==epoch) return false;
      state.data=null;
      state.error=error instanceof Error ? error.message : '상태 변경 응답을 확인하지 못했습니다.';
      // A failed/late write may have committed. Read back once; never retry POST.
      try {
        const data=parsed(await api(path(target)),target);
        if(token===epoch) {state.data=data;state.notice='현재 상태를 다시 읽었습니다. 확인한 뒤 변경할 항목을 다시 선택하세요.';}
      } catch {
        if(token===epoch) state.notice='현재 상태도 확인하지 못했습니다. 상태 다시 확인을 눌러 확인하세요.';
      }
      return false;
    } finally { if(token===epoch) state.saving=false; }
  }
  return {state,select,refresh,submit,dispose:()=>{++epoch;}};
}
