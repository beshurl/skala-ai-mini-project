<!-- THESIS: Ask a follow-up beside the evidence and inspect the answer's sources.
OWN-WORLD: Existing charcoal/ivory/gold, text roles and spacious record rows.
STORY: Ask, inspect citations, continue with the same case and versioned history.
FIRST VIEWPORT: Heading/version, transcript, then a labelled question composer.
FORM: Local Operate extension; no new identity or decorative chat avatars. -->
<script setup lang="ts">
import {computed,nextTick,onBeforeUnmount,onMounted,ref,watch} from 'vue';
import {ConversationController,activeTurn,initialConversation} from '../conversation';
import type {ConversationState} from '../conversation';
import type {Citation} from '../types';
import {errors} from '../api';
const props=defineProps<{caseId:string;version:number;api:(path:string,options?:any)=>Promise<any>;readOnly:boolean;busy:boolean;evidenceTitle:(id:string)=>string}>();
const emit=defineEmits<{cite:[citation:Citation];active:[active:boolean]}>();
const state=ref<ConversationState>(initialConversation()),question=ref(''),field=ref<HTMLTextAreaElement|null>(null);
const transcript=ref<HTMLDivElement|null>(null);
let acknowledged=0;
const controller=new ConversationController(props.api,props.caseId,props.version,value=>{
  const area=transcript.value;
  const follow=value.acknowledgements!==acknowledged || !area || area.scrollHeight-area.scrollTop-area.clientHeight<64;
  state.value={...value,turns:[...value.turns]};
  if(follow)void nextTick(()=>{if(transcript.value)transcript.value.scrollTop=transcript.value.scrollHeight;});
  if(value.acknowledgements!==acknowledged){if(question.value.trim()===value.acknowledgedQuestion)question.value='';acknowledged=value.acknowledgements;}
  emit('active',!!activeTurn(value) || value.submitting || !!value.pending);
});
const active=computed(()=>activeTurn(state.value));
const disabled=computed(()=>props.readOnly || props.busy || state.value.loading || !state.value.ready || !!active.value || state.value.submitting || !!state.value.pending);
const canSend=computed(()=>!disabled.value && !!question.value.trim() && Array.from(question.value.trim()).length<=1500);
const statusNames:Record<string,string>={QUEUED:'답변 대기',RUNNING:'공개 증거 검토 중',COMPLETED:'답변 저장됨',PARTIAL:'답변 검증 실패',FAILED:'답변 생성 실패',CANCELLED:'취소됨',STALE:'증거 버전이 바뀌어 종료됨'};
function suggest(text:string){if(disabled.value)return;question.value=text;field.value?.focus();}
async function send(){if(canSend.value)await controller.send(question.value);}
function keydown(event:KeyboardEvent){if(event.key==='Enter' && !event.shiftKey && !event.isComposing && event.keyCode!==229){event.preventDefault();void send();}}
onMounted(()=>void controller.refresh());
watch(()=>props.version,version=>controller.setVersion(version));
onBeforeUnmount(()=>{controller.dispose();emit('active',false);});
</script>
<template>
  <section class="case-conversation" aria-labelledby="conversation-heading" :aria-busy="state.loading || state.submitting">
    <div class="conversation-heading"><div><h2 id="conversation-heading">사건에 질문하기</h2><p>현재 공개 증거 v{{version}} 기준으로 대화를 이어갑니다.</p></div><button class="subtle" :disabled="state.loading || state.submitting" @click="controller.refresh()">대화 새로고침</button></div>
    <p class="conversation-scope">최근 답변 완료 대화 최대 3개를 참고하며, 문맥 한도에 따라 더 적게 사용할 수 있습니다. 이전 답변은 증거가 아닙니다.</p>
    <button v-if="state.nextBefore" class="subtle" :disabled="state.loading || state.submitting" @click="controller.refresh(true)">이전 대화 불러오기</button>
    <div ref="transcript" class="conversation-transcript" aria-label="이 사건의 대화 기록" tabindex="0">
      <p v-if="state.loading && !state.turns.length" class="conversation-empty">저장된 대화를 확인하고 있습니다.</p>
      <div v-else-if="!state.turns.length" class="conversation-empty"><p>공개 기록에서 궁금한 점을 물어보세요.<br />답변의 인용을 누르면 연결된 원문을 확인할 수 있습니다.</p><div class="conversation-suggestions"><button class="subtle" :disabled="disabled" @click="suggest('공개 자료 사이에 충돌하는 내용이 있나요?')">충돌하는 기록 살펴보기</button><button class="subtle" :disabled="disabled" @click="suggest('현재 자료에서 무엇을 더 확인해야 하나요?')">추가 확인 사항 물어보기</button></div></div>
      <article v-for="turn in state.turns" :key="turn.id" class="conversation-turn" :data-turn-id="turn.id">
        <div class="question-record"><p class="conversation-meta">내 질문 · 증거 v{{turn.version}}</p><p class="question-text">{{turn.question}}</p></div>
        <div class="answer-record"><p class="conversation-meta">{{statusNames[turn.status]}}<span v-if="turn.version!==version"> · 이전 증거 버전의 대화</span></p>
          <p v-if="turn.result?.provenance==='deterministic_fixture'" class="conversation-scope">테스트 모드 · 실제 모델을 호출하지 않은 모의 답변입니다.</p>
          <template v-if="turn.result && turn.result.conversation.status!=='UNAVAILABLE'">
            <p v-if="turn.result.conversation.status==='INSUFFICIENT'" class="insufficient-answer">현재 공개 자료로는 질문에 답할 근거가 충분하지 않습니다.</p>
            <div v-for="(paragraph,index) in turn.result.conversation.paragraphs" :key="index" class="answer-paragraph"><p>{{paragraph.text}}</p><div class="answer-citations"><button v-for="(citation,i) in paragraph.citations" :key="i" class="citation" :aria-label="`${evidenceTitle(citation.evidence_id)}의 인용 원문 열기`" @click="emit('cite',citation)">{{evidenceTitle(citation.evidence_id)}} · 원문 ↗</button></div></div>
            <div v-if="turn.result.conversation.missing_information.length" class="missing-information"><h3>더 확인할 자료</h3><ul><li v-for="item in turn.result.conversation.missing_information" :key="item">{{item}}</li></ul></div>
            <div v-if="turn.result.conversation.follow_up_questions.length" class="follow-up"><h3>이어서 물어보기</h3><button v-for="item in turn.result.conversation.follow_up_questions" :key="item" class="subtle" :disabled="disabled" @click="suggest(item)">{{item}}</button></div>
            <p class="conversation-scope">원문 인용 구간을 검사한 답변입니다. 자료 해석의 정확성은 별도 확인이 필요합니다.</p>
          </template>
          <p v-else-if="turn.error || turn.result?.limitations?.length" role="status">{{errors[turn.error || turn.result?.limitations?.[0] || ''] || '답변을 완료하지 못했습니다. 상태를 확인하고 새 질문을 작성하세요.'}}</p>
          <p v-else-if="turn.status==='QUEUED' || turn.status==='RUNNING'" class="conversation-scope">같은 모델의 작업 순서에 따라 처리합니다. 대화를 나가도 요청한 작업은 유지됩니다.</p>
        </div>
      </article>
    </div>
    <p class="conversation-status" aria-live="polite">{{active ? statusNames[active.status] : state.loading ? '대화 기록 확인 중' : state.ready ? '저장된 대화를 확인했습니다.' : '대화 새로고침으로 현재 상태를 확인하세요.'}}</p>
    <div v-if="state.error" class="conversation-error" role="alert"><p>{{state.error}}</p></div>
    <div v-if="state.pending && !state.submitting" class="uncertain-request"><p>전송 여부를 확인하지 못한 질문이 있습니다. 같은 요청을 확인하면 중복 답변 생성을 방지할 수 있습니다.</p><button class="secondary" :disabled="state.submitting || state.loading" @click="controller.retryPending()">같은 요청 확인하기</button></div>
    <form @submit.prevent="send"><label :for="`question-${caseId}`">질문</label><textarea :id="`question-${caseId}`" ref="field" v-model="question" rows="3" maxlength="1500" placeholder="두 기록이 충돌하는 이유를 설명해줘" :disabled="props.readOnly || state.submitting" :aria-describedby="`question-help-${caseId}`" @keydown="keydown" />
      <div class="composer-actions"><p :id="`question-help-${caseId}`">Enter 전송 · Shift+Enter 줄바꿈<br />{{props.readOnly ? '사건 검토를 재개하면 질문할 수 있습니다.' : '질문은 사실로 간주하지 않으며, 공개 증거에 연결해 검토합니다.'}}</p><button v-if="active" type="button" class="secondary" :disabled="state.submitting" @click="controller.cancel()">답변 생성 취소</button><button type="submit" class="primary" :disabled="!canSend">{{state.submitting ? '전송 확인 중…' : '질문 보내기'}}</button></div>
    </form>
  </section>
</template>
<style scoped>
.case-conversation{margin-block-end:48px;min-width:0;overflow-wrap:anywhere}.conversation-heading{display:flex;align-items:start;justify-content:space-between;gap:16px}.conversation-heading h2{font-size:18px;line-height:1.5;margin:0}.conversation-heading p{color:var(--muted);font-size:13px;margin:6px 0 0}.conversation-heading button{flex-shrink:0}.conversation-scope,.conversation-meta,.conversation-status{color:var(--muted);font-size:12px;line-height:1.8}.conversation-scope{margin:12px 0}.conversation-transcript{max-height:560px;overflow-y:auto;overscroll-behavior:contain;scrollbar-gutter:stable;padding-inline-end:8px;margin-block:20px 12px}.conversation-empty{color:var(--text-secondary);font-size:14px;line-height:1.9;padding-block:12px 20px}.conversation-empty p{margin-block:0 12px}.conversation-suggestions{display:flex;flex-wrap:wrap;gap:4px 12px}.conversation-turn+.conversation-turn{border-block-start:1px solid var(--line);margin-block-start:28px;padding-block-start:28px}.question-record{padding:16px 20px;background:var(--surface-raised);border-radius:var(--radius)}.conversation-meta{margin:0 0 6px}.question-text{margin:0;white-space:pre-wrap;font-size:14px;line-height:1.9}.answer-record{padding-block:20px 0}.answer-paragraph p{font-size:14px;line-height:1.9;white-space:pre-wrap;margin:12px 0 4px}.answer-citations{display:flex;flex-wrap:wrap;gap:4px 12px}.case-conversation .citation{font:inherit;font-size:12px;min-height:44px;padding:6px 0;color:var(--accent);border:0;background:transparent;cursor:pointer;text-align:start;line-height:1.7}.case-conversation .citation:hover{text-decoration:underline}.missing-information,.follow-up{margin-block-start:20px}.case-conversation h3{font-size:13px;margin:0 0 8px}.missing-information ul{padding-inline-start:20px;font-size:13px;color:var(--text-secondary);line-height:1.9;margin:0}.follow-up .subtle{display:block;text-align:start;white-space:normal;line-height:1.8}.insufficient-answer{font-size:14px;color:var(--warning);line-height:1.9}.conversation-status{min-height:22px;margin:0 0 12px}.conversation-error{color:var(--danger);font-size:13px;line-height:1.8}.uncertain-request{padding-block:12px;font-size:13px;line-height:1.8;color:var(--warning)}.case-conversation label{display:block;font-size:13px;font-weight:600;margin-block-end:8px}.case-conversation textarea{width:100%;box-sizing:border-box;resize:vertical;min-height:100px;max-height:280px;background:var(--panel);color:var(--text);border:1px solid var(--line-strong);border-radius:var(--radius);font:inherit;font-size:14px;line-height:1.8;padding:12px 14px}.case-conversation textarea::placeholder{color:var(--muted)}.composer-actions{display:flex;flex-wrap:wrap;align-items:center;justify-content:flex-end;gap:12px;margin-block-start:12px}.composer-actions p{flex:1;min-width:160px;font-size:12px;line-height:1.8;color:var(--muted);margin:0}.case-conversation :is(button,textarea,.conversation-transcript):focus-visible{outline:2px solid var(--accent);outline-offset:3px}.case-conversation button{min-height:44px}.case-conversation button:disabled{cursor:not-allowed}@media(max-width:480px){.conversation-heading{flex-wrap:wrap;gap:8px}.conversation-transcript{max-height:480px;padding-inline-end:4px}.question-record{padding:12px 14px}.composer-actions p{flex-basis:100%}.composer-actions .primary{flex:1}}
</style>
