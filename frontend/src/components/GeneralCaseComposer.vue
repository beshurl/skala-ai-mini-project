<!-- Local Operate extension: explicit synthetic input, retained drafts, no retry. -->
<script setup lang="ts">
import { ref, reactive, useId } from 'vue';
const props=defineProps<{ createCase:(payload:Record<string,unknown>)=>Promise<void>; disabled?:boolean }>();
const prefix=useId(), busy=ref(false), error=ref(''), confirmed=ref(false);
const title=ref(''), summary=ref(''), claims=ref('');
const creationId=ref(crypto.randomUUID().replaceAll('-',''));
const evidence=reactive([{title:'',text:'',kind:'record',initially_released:true}]);
async function submit(){
  if(busy.value || props.disabled)return;
  busy.value=true;error.value='';
  try {
    const items=claims.value.split('\n').map(s=>s.trim()).filter(Boolean);
    if(!confirmed.value || !items.length || items.length>8 || items.some(c=>c.length>700))throw new Error('가상 자료 여부와 주장 1~8개, 주장당 700자 한도를 확인하세요.');
    if(evidence.reduce((sum,e)=>sum+e.text.length,0)>24000)throw new Error('전체 자료 원문은 24,000자까지 입력할 수 있습니다.');
    await props.createCase({creation_id:creationId.value,synthetic_only:true,title:title.value,summary:summary.value,claims:items,evidence:evidence.map(e=>({...e}))});
    creationId.value=crypto.randomUUID().replaceAll('-','');
    title.value='';summary.value='';claims.value='';confirmed.value=false;evidence.splice(0,evidence.length,{title:'',text:'',kind:'record',initially_released:true});
  } catch(e) {error.value=e instanceof Error?e.message:'사건을 저장하지 못했습니다. 목록을 확인한 뒤 다시 시도하세요.';}
  finally{busy.value=false;}
}
</script>

<template>
  <details class="case-composer">
    <summary>새 가상 사건 작성</summary>
    <p class="composer-help">여러 주장과 자료를 함께 검토할 수 있습니다. 실제 사건·판결문·개인정보를 넣지 마세요. 작성한 자료는 학습이나 검수 완료 데이터로 등록되지 않습니다.</p>
    <form @submit.prevent="submit">
      <fieldset :disabled="busy || disabled"><legend class="sr-only">가상 사건 입력</legend>
        <label :for="`${prefix}-title`">사건 제목</label><input :id="`${prefix}-title`" v-model="title" required maxlength="120" />
        <label :for="`${prefix}-summary`">사건 개요</label><textarea :id="`${prefix}-summary`" v-model="summary" maxlength="2000" rows="2" />
        <label :for="`${prefix}-claims`">검토할 주장 <span>한 줄에 하나, 최대 8개</span></label><textarea :id="`${prefix}-claims`" v-model="claims" required rows="3" />
        <fieldset v-for="(item,index) in evidence" :key="index" class="evidence-input"><legend>자료 {{index+1}}</legend>
          <label :for="`${prefix}-e${index}-title`">자료 제목</label><input :id="`${prefix}-e${index}-title`" v-model="item.title" required maxlength="120" />
          <label :for="`${prefix}-e${index}-kind`">자료 종류</label><select :id="`${prefix}-e${index}-kind`" v-model="item.kind"><option value="record">기록</option><option value="statement">진술</option><option value="note">메모</option><option value="correction">정정 자료</option><option value="test_result">검사 결과</option></select>
          <label :for="`${prefix}-e${index}-text`">자료 원문</label><textarea :id="`${prefix}-e${index}-text`" v-model="item.text" required maxlength="8000" rows="4" />
          <label class="composer-checkbox"><input v-model="item.initially_released" type="checkbox" /> 처음부터 공개</label>
          <button v-if="evidence.length>1" type="button" class="subtle" @click="evidence.splice(index,1)" :aria-label="`자료 ${index+1} 삭제`">이 자료 삭제</button>
        </fieldset>
        <button type="button" class="secondary" :disabled="evidence.length>=24" @click="evidence.push({title:'',text:'',kind:'record',initially_released:true})">자료 추가</button>
        <p class="composer-help">나중에 공개할 자료는 체크를 해제하세요. 저장 후 ‘새 증거 공개’로 원문을 하나씩 추가 공개합니다. 전체 원문은 24,000자까지이며 모델 입력 한도를 넘으면 분석을 보류합니다.</p>
        <label class="composer-checkbox"><input v-model="confirmed" type="checkbox" required /> 직접 작성한 가상 자료이며 실제 개인정보를 포함하지 않았습니다.</label>
        <button type="submit" class="primary">{{busy?'사건 저장 중…':'가상 사건 저장'}}</button>
      </fieldset>
      <p v-if="error" role="alert" class="composer-error">{{error}} 입력 내용은 보존했습니다. 응답이 불확실하면 사건 목록도 확인하세요.</p>
    </form>
  </details>
</template>

<style scoped>
button{min-height:44px;border:1px solid var(--line-strong);border-radius:var(--radius);padding:10px 16px;font:inherit;font-size:13px;font-weight:600;cursor:pointer}button:disabled{opacity:.55;cursor:default}button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:3px}.primary{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}.secondary{background:var(--surface-raised);color:var(--text)}.subtle{background:transparent;color:var(--muted)}button:hover:not(:disabled){border-color:var(--accent)}
.case-composer{margin-block:24px;max-width:70ch}.case-composer summary{cursor:pointer;padding-block:12px;color:var(--text);font-weight:600;min-height:44px}.case-composer summary:focus-visible{outline:2px solid var(--accent);outline-offset:3px}.composer-help{color:var(--muted);font-size:13px;line-height:1.8;margin-block:12px 20px}.case-composer fieldset{border:0;padding:0;margin:0;min-width:0}.case-composer label:not(.composer-checkbox){display:block;margin-block:20px 8px;font-size:14px}.case-composer label span{color:var(--muted);font-size:13px}.case-composer input:not([type=checkbox]),.case-composer textarea,.case-composer select{box-sizing:border-box;width:100%;min-height:44px;padding:12px;background:var(--panel);color:var(--text);border:1px solid var(--line-strong);border-radius:var(--radius);font:inherit}.case-composer textarea{resize:vertical;line-height:1.7}.case-composer .evidence-input{margin-block:28px}.case-composer legend{font-size:15px;font-weight:600}.composer-checkbox{display:flex;align-items:center;gap:12px;min-height:44px;margin-block:16px;line-height:1.7;font-size:14px}.composer-checkbox input{flex:none;width:18px;height:18px;accent-color:var(--accent)}.composer-error{color:var(--danger);font-size:14px;line-height:1.8}.case-composer .primary{margin-block:8px 16px}
</style>
