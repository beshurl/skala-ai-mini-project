import {ApiError} from './api.ts';
import type {Citation} from './types.ts';
export interface ConversationAnswer {
  status:'ANSWERED'|'INSUFFICIENT'|'UNAVAILABLE'; paragraphs:{text:string;citations:Citation[]}[];
  missing_information:string[]; follow_up_questions:string[]; history_turn_ids:string[]; history_turns_omitted:number;
}
export interface ConversationTurn {
  id:string;case_id:string;kind:'conversation';version:number;question:string;request_id:string;
  status:string;error:string|null;created:number;
  result:{conversation:ConversationAnswer;provenance:string;limitations:string[]}|null;
}
interface SendRequest {request_id:string;question:string;evidence_version:number;after_turn_id:string|null}
export interface ConversationState {
  turns:ConversationTurn[];latestTurnId:string|null;nextBefore:string|null;ready:boolean;loading:boolean;submitting:boolean;
  error:string;pending:SendRequest|null;acknowledgedQuestion:string|null;acknowledgements:number;
}
type Api=(path:string,options?:{method?:string;body?:string;signal?:AbortSignal})=>Promise<any>;
const running=new Set(['QUEUED','RUNNING']);
const statuses=new Set([...running,'COMPLETED','PARTIAL','FAILED','CANCELLED','STALE']);
export const activeTurn=(state:ConversationState)=>state.turns.find(t=>running.has(t.status));
export const initialConversation=():ConversationState=>({turns:[],latestTurnId:null,nextBefore:null,ready:false,loading:false,submitting:false,error:'',pending:null,acknowledgedQuestion:null,acknowledgements:0});
export function validTurn(value:any,caseId:string):value is ConversationTurn {
  if(!value || value.case_id!==caseId || value.kind!=='conversation' || !/^JOB-[a-f0-9]{16}$/.test(value.id)
    || !/^[a-f0-9]{32}$/.test(value.request_id) || typeof value.question!=='string'
    || !Number.isInteger(value.version) || value.version<1 || !Number.isFinite(value.created) || !statuses.has(value.status))return false;
  if(['COMPLETED','PARTIAL'].includes(value.status) && !value.result)return false;
  if(value.result){
    if(!['local_mlx','deterministic_fixture'].includes(value.result.provenance) || !Array.isArray(value.result.limitations))return false;
    const answer=value.result.conversation;
    if(!answer || !['ANSWERED','INSUFFICIENT','UNAVAILABLE'].includes(answer.status) || !Array.isArray(answer.paragraphs)
      || !Array.isArray(answer.missing_information) || !answer.missing_information.every((v:any)=>typeof v==='string')
      || !Array.isArray(answer.follow_up_questions) || !answer.follow_up_questions.every((v:any)=>typeof v==='string'))return false;
    if(answer.status==='ANSWERED' && !answer.paragraphs.length)return false;
    if(!answer.paragraphs.every((p:any)=>typeof p.text==='string' && Array.isArray(p.citations) && p.citations.length
      && p.citations.every((c:any)=>typeof c.evidence_id==='string' && typeof c.quote==='string' && Number.isInteger(c.start) && Number.isInteger(c.end) && c.start>=0 && c.end>c.start)))return false;
  }
  return true;
}
/** One explicit POST; uncertain writes keep the same ID for manual recovery. */
export class ConversationController {
  state=initialConversation();private disposed=false;private reads=0;private abort=new AbortController();private timer:ReturnType<typeof setTimeout>|undefined;
  private api:Api; readonly caseId:string; private version:number; private notify:(s:ConversationState)=>void;
  private makeId:()=>string; private pollMs:number;
  constructor(api:Api,caseId:string,version:number,notify:(s:ConversationState)=>void,
    makeId=()=>crypto.randomUUID().replaceAll('-',''),pollMs=1000){
    this.api=api;this.caseId=caseId;this.version=version;this.notify=notify;this.makeId=makeId;this.pollMs=pollMs;
  }
  private emit(){if(!this.disposed)this.notify(this.state);}
  private merge(turns:ConversationTurn[]){
    const byId=new Map(this.state.turns.map(t=>[t.id,t]));for(const turn of turns)byId.set(turn.id,turn);
    this.state.turns=[...byId.values()].sort((a,b)=>a.created-b.created || a.id.localeCompare(b.id));
  }
  private acknowledge(turn:ConversationTurn){
    if(this.state.pending?.request_id===turn.request_id){this.state.acknowledgedQuestion=this.state.pending.question;this.state.acknowledgements++;this.state.pending=null;}
  }
  async refresh(older=false,silent=false){
    if(this.disposed)return;clearTimeout(this.timer);
    const seq=++this.reads,version=this.version;if(!silent)this.state.loading=true;this.state.error='';this.emit();
    const suffix=older && this.state.nextBefore?'?before='+encodeURIComponent(this.state.nextBefore):'';
    try{
      const page=await this.api(`/api/cases/${encodeURIComponent(this.caseId)}/conversation${suffix}`,{signal:this.abort.signal});
      if(this.disposed || seq!==this.reads || version!==this.version)return;
      if(!page || page.case_id!==this.caseId || page.evidence_version!==version || !Array.isArray(page.turns) || !page.turns.every((t:any)=>validTurn(t,this.caseId))
        || !(page.latest_turn_id===null || /^JOB-[a-f0-9]{16}$/.test(page.latest_turn_id))
        || !(page.next_before===null || /^JOB-[a-f0-9]{16}$/.test(page.next_before)))throw new ApiError('INVALID_RESPONSE');
      this.merge(page.turns);this.state.latestTurnId=page.latest_turn_id;
      if(older || this.state.turns.length<=20)this.state.nextBefore=page.next_before;
      this.state.ready=true;for(const turn of page.turns)this.acknowledge(turn);
      if(activeTurn(this.state))this.timer=setTimeout(()=>void this.refresh(false,true),this.pollMs);
    }catch(error){
      if(this.disposed || seq!==this.reads)return;this.state.ready=false;
      if(error instanceof ApiError && ['AUTH_REQUIRED','NOT_FOUND'].includes(error.code))this.state.turns=[];
      this.state.error=error instanceof Error?error.message:'대화 기록을 확인하지 못했습니다.';
    }finally{if(!this.disposed && seq===this.reads){this.state.loading=false;this.emit();}}
  }
  async send(question:string){
    if(!this.state.ready || this.state.loading || this.state.pending || this.state.submitting || activeTurn(this.state) || !question.trim())return;
    this.state.pending={request_id:this.makeId(),question:question.trim(),evidence_version:this.version,after_turn_id:this.state.latestTurnId};await this.submitPending();
  }
  async retryPending(){if(this.state.pending && !this.state.submitting)await this.submitPending();}
  private async submitPending(){
    if(!this.state.pending || this.disposed)return;const payload={...this.state.pending};++this.reads;clearTimeout(this.timer);
    this.state.loading=false;this.state.submitting=true;this.state.error='';this.emit();
    try{
      const turn=await this.api(`/api/cases/${encodeURIComponent(this.caseId)}/conversation`,{method:'POST',body:JSON.stringify(payload),signal:this.abort.signal});
      if(this.disposed)return;
      if(!validTurn(turn,this.caseId) || turn.request_id!==payload.request_id || turn.question!==payload.question || turn.version!==payload.evidence_version)throw new ApiError('INVALID_RESPONSE');
      this.merge([turn]);this.state.latestTurnId=turn.id;this.acknowledge(turn);await this.refresh(false,true);
    }catch(error){
      if(this.disposed)return;
      if(error instanceof ApiError && error.status>=400 && error.status<500)this.state.pending=null;
      this.state.ready=false;this.state.error=error instanceof Error?error.message:'질문 전송 결과를 확인하지 못했습니다.';
    }finally{if(!this.disposed){this.state.submitting=false;this.emit();}}
  }
  async cancel(){
    const turn=activeTurn(this.state);if(!turn || this.state.submitting || this.disposed)return;
    ++this.reads;clearTimeout(this.timer);this.state.loading=false;this.state.submitting=true;this.state.error='';this.emit();
    try{
      const result=await this.api(`/api/jobs/${turn.id}/cancel`,{method:'POST',signal:this.abort.signal});if(this.disposed)return;
      if(!validTurn(result,this.caseId) || result.id!==turn.id)throw new ApiError('INVALID_RESPONSE');this.merge([result]);await this.refresh(false,true);
    }catch(error){if(!this.disposed){this.state.ready=false;this.state.error=error instanceof Error?error.message:'취소 상태를 확인하지 못했습니다.';}}
    finally{if(!this.disposed){this.state.submitting=false;this.emit();}}
  }
  setVersion(version:number){this.version=version;this.state.ready=false;void this.refresh();}
  dispose(){this.disposed=true;++this.reads;clearTimeout(this.timer);this.abort.abort();}
}
