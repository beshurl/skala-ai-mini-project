<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import {api} from '../api';
import SiteHeader from '../components/SiteHeader.vue';
import type {CaseSummary, Session, Job} from '../types';
const props = defineProps<{view:string}>();
const session = ref<Session|null>(null), records=ref<(Job & {title:string})[]>([]), error=ref(''), loading=ref(true);
const ctrl = new AbortController();
onBeforeUnmount(()=>ctrl.abort());
onMounted(async()=>{
 try {
  session.value=await api<Session>('/api/session',{signal:ctrl.signal});
  if(props.view==='history'){
   const cases = await api<CaseSummary[]>('/api/cases',{signal:ctrl.signal});
   const lists = await Promise.all(cases.map(async c => (await api<Job[]>(`/api/cases/${c.id}/analyses`,{signal:ctrl.signal})).map(j=>({...j,title:c.title}))));
   records.value=lists.flat().sort((a,b)=>b.created-a.created);
  }
 } catch(e){if(!ctrl.signal.aborted) error.value=(e as Error).message;} finally {loading.value=false;}
});
const statuses:Record<string,string>={QUEUED:'대기',RUNNING:'진행 중',COMPLETED:'완료',PARTIAL:'부분 완료',FAILED:'실패',STALE:'증거 변경',CANCELLED:'취소'};
</script>
<template><div class="records-page">
 <a class="skip" href="#records-main">본문으로 이동</a>
 <SiteHeader :active="view" />
 <main id="records-main" tabindex="-1"><p class="eyebrow">RE:CASE / 나의 기록실</p><h1>{{view==='history'?'분석 이력':'실행 정보'}}</h1>
 <p v-if="loading" role="status">현재 세션을 확인하고 있습니다.</p>
 <div v-else-if="error" role="alert"><p>{{error}}</p><a href="/cases">사건 기록에서 다시 입장하기</a></div>
 <template v-else-if="view==='history'">
 <p class="muted">이 브라우저의 현재 계정에 속한 기록입니다. 사건별 최신100개까지 조회합니다.</p>
 <div v-if="!records.length" class="empty"><h2>아직 분석 기록이 없습니다.</h2><p>공개된 증거를 읽고 첫 분석을 시작해보세요.</p><a href="/cases">사건 선택하기 ↗</a></div>
 <ul v-else><li v-for="j in records" :key="j.id"><a :href="`/cases/${j.case_id}?job=${j.id}`"><strong>{{j.title}}</strong><span>증거 v{{j.version}} · {{statuses[j.status]||j.status}}</span><time>{{new Date(j.created*1000).toLocaleString('ko-KR')}}</time></a></li></ul>
 </template>
 <template v-else><dl v-if="session"><dt>모델</dt><dd>{{session.model.model}}</dd><dt>백엔드</dt><dd>{{session.model.backend}}</dd><dt>리비전</dt><dd>{{session.model.revision}}</dd><dt>어댑터</dt><dd>{{session.model.adapter_loaded?'적용 확인':'적용 안 됨'}}</dd><dt>프롬프트</dt><dd>{{session.model.prompt_version}}</dd></dl>
 <section><h2>현재 이용 범위</h2><p>준비된 합성 사건 선택, TXT·MD·JSON 파일의 사건 초안 불러오기, 공개 증거 분석, 사건별 질문·후속 대화, 새 자료 공개와 판단 비교를 지원합니다. 사건을 선택한 뒤 ‘사건에 질문하기’에서 공개 기록에 관해 물어볼 수 있습니다. PDF·HWP·DOCX와 참고 판례 검색 화면은 제공하지 않습니다.</p><p>결과는 실제 사건이나 유죄를 판단하지 않습니다. 이 화면에서 모델 설정과 보안 권한을 변경할 수 없습니다.</p></section></template>
 </main></div></template>
<style scoped>
.records-page{min-height:100vh;background:var(--bg)}main{max-width:1120px;margin:auto;padding:64px 40px 80px}h1{font-size:38px;line-height:1.4;letter-spacing:-.03em;font-weight:550;margin:16px 0 26px}.eyebrow{font-size:11px;letter-spacing:.12em;color:var(--accent)}.muted{color:var(--muted);font-size:13px;line-height:1.9}.empty,section{padding:32px 0;border-top:1px solid var(--line);margin-top:32px}.empty h2,section h2{font-size:20px;font-weight:550;margin:0 0 12px}.empty p,section p{font-size:14px;color:var(--muted);line-height:1.95;max-width:75ch}.empty a{display:inline-block;color:var(--accent);padding:12px 0;text-decoration:none;min-height:44px}ul{padding:0;list-style:none;border-top:1px solid var(--line);margin-top:28px}li a{display:grid;grid-template-columns:minmax(0,1fr) 150px 170px;gap:24px;align-items:center;padding:25px 10px;border-bottom:1px solid var(--line);text-decoration:none}li a:hover{background:var(--panel)}li strong{font-size:15px;font-weight:550}li span,li time{color:var(--muted);font-size:12px}li span{color:var(--accent)}dl{display:grid;grid-template-columns:150px 1fr;gap:0;margin-top:34px;border-top:1px solid var(--line)}dd,dt{padding:19px 0;border-bottom:1px solid var(--line);font-size:13px}dd{margin:0;overflow-wrap:anywhere}dt{color:var(--muted)}@media(max-width:760px){main{padding:40px 20px 60px}h1{font-size:30px}li a{grid-template-columns:1fr;gap:8px;padding:22px 0}li time{font-size:11px}dl{grid-template-columns:100px minmax(0,1fr);gap:0 16px}dd,dt{font-size:12px}section h2,.empty h2{font-size:18px}}
</style>
<style scoped>
li a>* {min-width:0}
li strong {overflow-wrap:anywhere}
</style>
