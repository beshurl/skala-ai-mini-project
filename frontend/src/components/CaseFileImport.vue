<!-- THESIS: Inspect a local case file before changing the editable draft.
OWN-WORLD: Existing charcoal/gold tokens, labelled native file and select controls.
STORY: Choose file, select one case, inspect sources, apply then explicitly save.
FIRST VIEWPORT: File choice and supported formats; preview appears only after reading.
FORM: Local Operate extension; existing draft remains intact until explicit apply. -->
<script setup lang="ts">
import {computed,onBeforeUnmount,ref,useId} from 'vue';
import {readCaseFile} from '../caseFiles';
import type {CaseDraft,CaseFile} from '../caseFiles';
const props=defineProps<{disabled?:boolean;hasDraft:boolean}>();
const emit=defineEmits<{apply:[draft:CaseDraft,filename:string];reading:[value:boolean]}>();
const id=useId(),field=ref<HTMLInputElement|null>(null),reading=ref(false),error=ref(''),loaded=ref<CaseFile|null>(null),selected=ref(0);
const draft=computed(()=>loaded.value?.cases[selected.value]);
let generation=0;
defineExpose({focus:()=>field.value?.focus()});
onBeforeUnmount(()=>{generation++;});
async function choose(event:Event){
  const input=event.target as HTMLInputElement,file=input.files?.[0];if(!file || props.disabled)return;
  const current=++generation;reading.value=true;emit('reading',true);error.value='';loaded.value=null;selected.value=0;
  try{const result=await readCaseFile(file);if(current===generation)loaded.value=result;}
  catch(e){if(current===generation)error.value=e instanceof Error?e.message:'파일을 읽지 못했습니다. 텍스트 형식을 확인하세요.';}
  finally{if(current===generation){reading.value=false;emit('reading',false);input.value='';}}
}
function apply(){if(!draft.value || !loaded.value || props.disabled || reading.value)return;emit('apply',draft.value,loaded.value.name);loaded.value=null;}
</script>
<template>
  <section class="case-file-import" :aria-labelledby="`${id}-heading`" :aria-busy="reading">
    <h3 :id="`${id}-heading`">사건 파일 불러오기</h3>
    <p :id="`${id}-help`">TXT·MD·JSON · UTF-8 · 최대 256KiB. 파일 선택은 초안만 준비하며, 저장·분석은 시작하지 않습니다.</p>
    <label :for="`${id}-file`">불러올 사건 파일</label>
    <input ref="field" :id="`${id}-file`" type="file" accept=".txt,.md,.json,text/plain,text/markdown,application/json" :disabled="disabled || reading" :aria-describedby="`${id}-help`" @change="choose" />
    <div class="template-links" aria-label="가상 사건 예시 파일"><a class="template-download" href="/assets/recase-case-template.txt" download="recase-case-template.txt">TXT 예시 ↗</a><a class="template-download" href="/assets/recase-case-template.md" download="recase-case-template.md">MD 예시 ↗</a><a class="template-download" href="/assets/recase-case-template.json" download="recase-case-template.json">사건 JSON 예시 ↗</a></div>
    <p v-if="reading" role="status">파일을 읽고 입력 한도를 확인하고 있습니다.</p>
    <p v-if="error" class="import-error" role="alert">{{error}} 작성 중인 내용은 바꾸지 않았습니다.</p>
    <div v-if="loaded && draft" class="import-preview">
      <p class="import-filename">{{loaded.name}}</p>
      <template v-if="loaded.cases.length>1"><label :for="`${id}-case`">불러올 사건 선택 ({{loaded.cases.length}}개)</label><select :id="`${id}-case`" v-model="selected" :disabled="disabled"><option v-for="(item,index) in loaded.cases" :key="index" :value="index">{{item.title}}</option></select></template>
      <h4>{{draft.title}}</h4><p v-if="draft.summary">{{draft.summary}}</p>
      <p>주장 {{draft.claims.length}}개 · 자료 {{draft.evidence.length}}개 · 나중에 공개 {{draft.evidence.filter(e=>!e.initially_released).length}}개</p>
      <details><summary>주장과 자료 원문 확인</summary><div class="source-preview" tabindex="0" aria-label="불러온 사건 원문 미리보기"><h5>검토할 주장</h5><ul><li v-for="claim in draft.claims" :key="claim">{{claim}}</li></ul><article v-for="(item,index) in draft.evidence" :key="index"><h5>{{item.title}} · {{item.initially_released?'처음부터 공개':'나중에 공개'}}</h5><p>{{item.text}}</p></article></div></details>
      <p v-if="loaded.format==='text'">텍스트는 자료 원문으로 채웁니다. 기본 검토 질문과 자료 구분은 적용 후 수정할 수 있습니다.</p>
      <p v-if="hasDraft" class="replace-notice">적용하면 작성 중인 입력을 이 초안으로 바꿉니다. 적용 뒤 ‘이전 입력 복원’으로 되돌릴 수 있습니다.</p>
      <div class="import-actions"><button type="button" class="rc-button rc-button--primary" :disabled="disabled || reading" @click="apply">{{hasDraft?'현재 입력을 파일 초안으로 바꾸기':'파일 초안을 입력에 적용'}}</button><button type="button" class="rc-button" :disabled="disabled" @click="loaded=null">불러오기 취소</button></div>
    </div>
  </section>
</template>
<style scoped>
.case-file-import{margin-block:20px 32px;min-width:0;overflow-wrap:anywhere}.case-file-import h3{font-size:16px;margin:0 0 8px}.case-file-import p,.case-file-import li{font-size:13px;line-height:1.8;color:var(--muted)}.case-file-import label{display:block;font-size:13px;margin-block:16px 8px}.case-file-import input,.case-file-import select{width:100%;max-width:100%;min-height:44px;box-sizing:border-box;background:var(--panel);color:var(--text);border:1px solid var(--line-strong);border-radius:var(--radius);padding:10px;font:inherit;font-size:13px}.case-file-import input::file-selector-button{background:var(--surface-raised);color:var(--text);border:1px solid var(--line-strong);border-radius:var(--radius);min-height:36px;padding:6px 12px;margin-inline-end:12px;cursor:pointer}.template-download{display:inline-flex;align-items:center;min-height:44px;font-size:13px;color:var(--accent)}.import-preview{margin-block-start:20px;padding-block-start:4px}.import-filename{overflow-wrap:anywhere}.case-file-import h4{font-size:16px;margin:12px 0 8px}.case-file-import h5{font-size:13px;margin:18px 0 8px}.source-preview{max-height:280px;overflow:auto;padding-inline-end:12px}.source-preview p{white-space:pre-wrap;color:var(--text-secondary)}.source-preview ul{padding-inline-start:20px}.case-file-import summary{font-size:13px;line-height:1.8;padding-block:10px;cursor:pointer;min-height:44px}.import-actions{display:flex;flex-wrap:wrap;gap:12px;margin-block-start:16px}.import-actions button{white-space:normal;text-align:start}.case-file-import .import-error{color:var(--danger)}.case-file-import .replace-notice{color:var(--warning)}.case-file-import :is(input,select,summary,.source-preview):focus-visible{outline:2px solid var(--accent);outline-offset:3px}
</style>
<style scoped>.template-links{display:flex;flex-wrap:wrap;gap:4px 20px}</style>
