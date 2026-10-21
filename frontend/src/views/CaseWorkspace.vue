<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from "vue";
import { createApiClient, errors } from "../api";
import { navigate, query } from "../navigation";
import SiteHeader from "../components/SiteHeader.vue";
import ModelDetails from "../components/ModelDetails.vue";
import CaseLifecycle from "../components/CaseLifecycle.vue";
import GeneralReview from "../components/GeneralReview.vue";
import GeneralCaseComposer from "../components/GeneralCaseComposer.vue";
import CaseConversation from "../components/CaseConversation.vue";
import {quoteParts} from "../quotes";
const props = defineProps({ caseId: String });

const session = ref(null),
  cases = ref([]),
  detail = ref(null),
  jobs = ref([]),
  job = ref(null);
const events = ref([]),
  error = ref(""),
  busy = ref(false),
  booting = ref(true),
  model = ref(null);
const connected = ref(""),
  comparison = ref(null),
  beforeId = ref(""),
  selectedEvidence = ref("");
const search = ref("");
const composer = ref(null);
const selectedQuote = ref(null);
const selectedQuoteParts = computed(()=>{
  const source=detail.value?.evidence.find(e=>e.id===selectedQuote.value?.evidence_id);
  return source && selectedQuote.value ? quoteParts(source.text,selectedQuote.value) : null;
});
const reviewFor = id => job.value?.result?.reasoning?.reviews.find(r=>r.claim_id===id);
const practiceNotice = ref("");
const lifecycle = ref(null), lifecycleBusy = ref(false), workspaceHeading = ref(null);
const lifecycleRefreshKey = ref(0);
const conversationActive = ref(false);
const filteredCases = computed(() => cases.value.filter(c => `${c.title} ${c.summary}`.toLocaleLowerCase().includes(search.value.trim().toLocaleLowerCase())));
let stream = null,
  selection = 0;
const terminal = new Set([
  "COMPLETED",
  "PARTIAL",
  "FAILED",
  "CANCELLED",
  "STALE",
]);
const active = computed(() => job.value && !terminal.has(job.value.status));
const activeCaseJob = computed(() => conversationActive.value || active.value || jobs.value.some(j => !terminal.has(j.status)));
const provenanceReadOnly = computed(() => detail.value?.read_only === true);
const caseReadOnly = computed(() => provenanceReadOnly.value || !lifecycle.value || !!lifecycle.value.closed_at || lifecycle.value.evidence_version !== detail.value?.evidence_version);
const caseWriteBlocked = computed(() => busy.value || lifecycleBusy.value || activeCaseJob.value || caseReadOnly.value);
const completed = computed(() => jobs.value.filter((j) => j.result));
const eligibleBefore = computed(() =>
  completed.value.filter(
    (j) => job.value && j.id !== job.value.id && j.created < job.value.created,
  ),
);
const labels = {
  SUPPORTED: "뒷받침됨",
  CONTRADICTED: "자료 간 충돌",
  INSUFFICIENT: "추가 확인 필요",
};
const statuses = {
  QUEUED: "분석 대기",
  RUNNING: "분석 중",
  COMPLETED: "분석 완료",
  PARTIAL: "부분 완료",
  FAILED: "분석 실패",
  CANCELLED: "취소됨",
  STALE: "증거 버전 변경됨",
};
const eventNames = {
  queued: "분석 작업 저장",
  running: "작업 시작",
  scope_checked: "공개 증거와 권한 확인",
  general_plan_ready: "공개 자료와 분석 범위 확정",
  general_model_started: "주장과 여러 공개 자료 검토",
  retrieval_complete: "관련 기록 검색 완료",
  model_started: "모델 분석 시작",
  claim_checked: "주장 검토 완료",
  validation_complete: "출력과 근거 검증 완료",
  completed: "결과 저장 완료",
  partial: "일부 검증 실패",
  failed: "작업 실패",
  cancelled: "작업 취소",
  stale: "이전 증거 버전의 작업 종료",
};
const viewAbort = new AbortController();
const request = createApiClient(() => session.value?.csrf);
const api = (path, options = {}) => request(path, {signal:viewAbort.signal, ...options});
async function addPractice() {
  await action(async () => {
    const added = await api('/api/practice', {method:'POST'});
    cases.value = await api('/api/cases');
    practiceNotice.value = added.created ? '테스트 사건 3개를 추가했습니다. 목록에서 사건을 선택하세요.' : '기존 테스트 사건을 불러왔습니다. 이전 분석과 증거 버전은 유지됩니다.';
  });
}
async function addGeneralPractice() {
  await action(async()=>{
    const added=await api('/api/practice/general',{method:'POST'});
    cases.value=await api('/api/cases');
    practiceNotice.value=added.created?'다중 증거 검토용 가상 사건 12개를 추가했습니다. 실제 추론 성능은 별도 검증이 필요합니다.':'기존 다중 증거 검토 사건을 불러왔습니다. 이력과 공개 버전은 유지됩니다.';
  });
}
async function createGeneralCase(payload) {
  if(busy.value)throw new Error('현재 요청이 끝난 뒤 다시 시도하세요.');
  busy.value=true;
  try{
    const created=await api('/api/cases',{method:'POST',body:JSON.stringify(payload)});
    if(!cases.value.some(c=>c.id===created.case_id))cases.value.unshift({id:created.case_id,title:created.title,summary:created.summary,version:created.evidence_version});
    await selectCase(created.case_id);
  }finally{busy.value=false;}
}
async function showCitation(citation) {
  await showEvidence(citation.evidence_id);
  const source=detail.value.evidence.find(e=>e.id===citation.evidence_id);
  if(!source || !quoteParts(source.text,citation)){error.value='인용 구간이 현재 원문과 일치하지 않습니다. 분석 버전과 원문을 확인하세요.';return;}
  selectedQuote.value=citation;
  await nextTick();
  const target=document.getElementById(`quote-${citation.evidence_id}`);
  target?.scrollIntoView({behavior:'auto',block:'center'});
  target?.focus({preventScroll:true});
}
async function action(fn) {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    await fn();
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}
function disconnect() {
  stream?.close();
  stream = null;
  connected.value = "";
}
async function loadHistory() {
  if (detail.value)
    jobs.value = await api(`/api/cases/${detail.value.case_id}/analyses`);
}
async function refreshJob() {
  if (!job.value) return;
  const id = job.value.id,
    updated = await api(`/api/jobs/${id}`);
  if (job.value?.id !== id) return;
  job.value = updated;
  if (terminal.has(updated.status)) {
    disconnect();
    await loadHistory();
  }
}
function subscribe(id) {
  disconnect();
  events.value = [];
  connected.value = "진행 이벤트에 연결 중입니다.";
  let retries = 0;
  stream = new EventSource(`/api/jobs/${id}/events`);
  stream.onopen = () => {
    connected.value = "서버의 실제 진행 이벤트를 수신하고 있습니다.";
  };
  for (const name of Object.keys(eventNames))
    stream.addEventListener(name, async (e) => {
      if (job.value?.id !== id) return;
      const data = JSON.parse(e.data);
      if (!events.value.some((x) => x.id === data.id)) events.value.push(data);
      if (name === "running") job.value.status = "RUNNING";
      if (
        ["completed", "partial", "failed", "cancelled", "stale"].includes(name)
      ) {
        try {
          await refreshJob();
        } catch (err) {
          error.value = err.message;
        }
      }
    });
  stream.onerror = async () => {
    if (job.value?.id !== id) return;
    retries += 1;
    try {
      await refreshJob();
    } catch (err) {
      error.value = err.message;
    }
    if (terminal.has(job.value?.status)) return;
    if (retries >= 3) {
      disconnect();
      connected.value =
        "진행 연결이 끊겼습니다. 상태 새로고침으로 결과를 확인하세요.";
    } else connected.value = `진행 연결이 끊겨 재접속 중입니다 (${retries}/3).`;
  };
}
async function selectCase(id) {
  const requestedJob = new URLSearchParams(window.location.search).get('job');
  const token = ++selection;
  disconnect();
  comparison.value = null;
  job.value = null;
  events.value = [];
  beforeId.value = "";
  selectedEvidence.value = "";
  selectedQuote.value=null;
  lifecycle.value = null;
  lifecycleBusy.value = false;
  const data = await api(`/api/cases/${id}`);
  const history = await api(`/api/cases/${id}/analyses`);
  if (token !== selection) return;
  detail.value = data;
  lifecycleRefreshKey.value++;
  document.title = `${data.title} · RE:CASE`;
  jobs.value = history;
  const requested = jobs.value.find(j=>j.id === requestedJob);
  job.value = requested || jobs.value[0] || null;
  navigate(`/cases/${encodeURIComponent(id)}${requested ? `?job=${encodeURIComponent(requested.id)}` : ''}`);
  if (active.value) subscribe(job.value.id);
  if(!booting.value) {await nextTick();workspaceHeading.value?.focus();}
}
function lifecycleState(value) {
  if(value.caseId === detail.value?.case_id) lifecycle.value = value.data;
}
function lifecyclePending(value) {
  if(value.caseId === detail.value?.case_id) lifecycleBusy.value = value.busy;
}
async function enter() {
  await action(async () => {
    session.value = await api("/api/demo", { method: "POST" });
    await initialize();
  });
}
async function freshDemo() {
  await action(async () => {
    disconnect();
    session.value = await api("/api/demo/new", { method: "POST" });
    clearCase();
    navigate("/cases");
    await nextTick();
    await initialize();
  });
}
async function initialize() {
  const s = await api("/api/session");
  session.value = s;
  model.value = s.model;
  cases.value = await api("/api/cases");
  if(!props.caseId) document.title = '사건 기록 · RE:CASE';
  if (props.caseId) {
    if(cases.value.some(c => c.id === props.caseId)) await selectCase(props.caseId);
    else error.value = "이 계정에서 접근할 수 없는 사건입니다. 사건 기록에서 다시 선택하세요.";
  }

}
async function analyze() {
  if(caseWriteBlocked.value) return;
  await action(async () => {
    job.value = await api(`/api/cases/${detail.value.case_id}/analyses`, {
      method: "POST",
      body: JSON.stringify({ evidence_version: detail.value.evidence_version }),
    });
    navigate(`/cases/${encodeURIComponent(detail.value.case_id)}?job=${encodeURIComponent(job.value.id)}`);
    comparison.value = null;
    beforeId.value = "";
    subscribe(job.value.id);
    await loadHistory();
  });
}
async function release() {
  if(caseWriteBlocked.value) return;
  await action(async () => {
    detail.value = await api(`/api/cases/${detail.value.case_id}/release`, {
      method: "POST",
      body: JSON.stringify({ evidence_version: detail.value.evidence_version }),
    });
    const c = cases.value.find((c) => c.id === detail.value.case_id);
    if (c) c.version = detail.value.evidence_version;
  });
}
async function cancel() {
  if(provenanceReadOnly.value) return;
  await action(async () => {
    await api(`/api/jobs/${job.value.id}/cancel`, { method: "POST" });
    await refreshJob();
  });
}
async function inspectJob(item) {
  job.value = item;
  comparison.value = null;
  beforeId.value = "";
  events.value = [];
  selectedEvidence.value = "";
  selectedQuote.value = null;
  disconnect();
  navigate(`/cases/${encodeURIComponent(detail.value.case_id)}?job=${encodeURIComponent(item.id)}`);
  if (active.value) subscribe(item.id);
}
async function compare() {
  await action(async () => {
    comparison.value = await api(
      `/api/cases/${detail.value.case_id}/compare?before=${encodeURIComponent(beforeId.value)}&after=${encodeURIComponent(job.value.id)}`,
    );
  });
}
async function showEvidence(id) {
  selectedQuote.value=null;
  selectedEvidence.value = id;
  await nextTick();
  const target = document.getElementById(`evidence-${id}`);
  target?.scrollIntoView({ behavior: "auto", block: "center" });
  target?.focus();
}
function claimText(id) {
  return detail.value?.claims.find((c) => c.id === id)?.text || id;
}
function evidenceTitle(id) {
  return detail.value?.evidence.find((e) => e.id === id)?.title || id;
}
function formatTime(t) {
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date(t * 1000));
}
onMounted(async () => {
  try {
    await initialize();
  } catch (err) {
    if (err.code !== 'AUTH_REQUIRED' && err.code !== 'CLIENT_CANCELLED') error.value = err.message;
  } finally {
    booting.value = false;
    if(props.caseId && detail.value) {await nextTick();workspaceHeading.value?.focus();}
  }
});
function clearCase() {
  ++selection;
  disconnect();
  detail.value = null;
  job.value = null;
  jobs.value = [];
  events.value = [];
  comparison.value = null;
  beforeId.value = "";
  selectedEvidence.value = "";
  error.value = "";
  lifecycle.value = null;
  lifecycleBusy.value = false;
  conversationActive.value = false;
  document.title = '사건 기록 · RE:CASE';
}
watch(() => props.caseId, id => {
  if(!id) {clearCase();nextTick(()=>workspaceHeading.value?.focus());}
  else if(session.value && id !== detail.value?.case_id) action(() => selectCase(id));
});
watch(query, value => {
  if(booting.value || !detail.value || active.value || window.location.pathname!==`/cases/${encodeURIComponent(detail.value.case_id)}`)return;
  const requested = new URLSearchParams(value).get('job');
  const selected = requested ? jobs.value.find(item=>item.id===requested) : jobs.value[0];
  if(selected && selected.id!==job.value?.id) void inspectJob(selected);
});
onBeforeUnmount(()=>{disconnect();viewAbort.abort();});
</script>

<template>
<div class="workspace-app">
  <a class="skip" href="#workspace">본문으로 이동</a>
  <SiteHeader active="cases" />
  <div v-if="error" class="error-banner" role="alert">
    <p>{{ error }}</p>
    <a v-if="error.includes('로그인')" href="/login">로그인하기</a>
    <button class="subtle" @click="error = ''" aria-label="오류 알림 닫기">
      닫기
    </button>
  </div>
  <main v-if="booting" id="workspace" class="entry" aria-live="polite">
    <p>계정과 사건 기록을 확인하고 있습니다.</p>
  </main>
  <main v-else-if="!session || !cases.length" id="workspace" class="entry">
    <h1>합성 사건 시작하기</h1>
    <p class="entry-description">준비된 사건의 공개 증거를 읽고 분석 결과를 비교할 수 있습니다.</p>
    <button class="primary" aria-label="합성 사건 열기" :disabled="busy" @click="enter">{{busy ? "사건을 준비하고 있습니다…" : "합성 사건 열기"}}</button>
    <button class="secondary" :disabled="busy" @click="addPractice">테스트 사건 3개 추가</button>
    <GeneralCaseComposer :create-case="createGeneralCase" :disabled="busy" />
    <section class="entry-help" aria-labelledby="entry-help-heading">
      <h2 id="entry-help-heading">이용 방법</h2>
      <ol><li>사건을 선택하고 공개된 증거를 확인합니다.</li><li>분석을 시작해 주장과 기록의 관계, 인용된 근거를 살펴봅니다.</li><li>새 증거를 공개한 뒤 다시 분석하면 이전 결과와 비교할 수 있습니다.</li></ol>
    </section>
    <p class="fineprint">준비된 합성 사건을 열거나 직접 가상 자료를 작성할 수 있습니다. 파일 업로드는 지원하지 않습니다.<br />분석 결과는 실제 사건의 사실·유죄 판단을 대신하지 않습니다.</p>
  </main>
  <main v-else-if="!caseId" id="workspace" class="case-library">
    <div class="library-heading">
      <div>
      <h1 ref="workspaceHeading" tabindex="-1">사건 기록</h1>
      <p>미제사건 재수사를 위한 진술·증거 대조와 새 증거 전후의 분석 비교를 체험합니다.</p>
      </div>
      <button class="secondary library-create" :disabled="busy" aria-label="새 가상 사건 작성 폼 열기" aria-controls="library-composer" @click="composer?.open()">새 가상 사건 작성 <span aria-hidden="true">＋</span></button>
    </div>
    <p v-if="model?.backend==='fixture'" class="fixture-notice" role="status">테스트 모드 · 실제 모델을 호출하지 않는 예시 분석입니다.</p>
    <p v-if="practiceNotice" class="practice-notice" role="status">{{practiceNotice}}</p>
    <div class="library-toolbar">
      <h2>{{search.trim() ? `검색 결과 ${filteredCases.length}건` : `전체 ${cases.length}건`}}</h2>
      <label class="case-search"><span class="sr-only">사건 검색</span><input v-model="search" aria-label="사건 검색" type="search" placeholder="제목·내용 검색" /></label>
    </div>
    <div class="case-list" v-if="filteredCases.length">
      <div class="case-list-head" aria-hidden="true"><span>사건</span><span>증거 버전</span><span></span></div>
      <button v-for="c in filteredCases" :key="c.id" class="case-file" :disabled="busy" @click="action(()=>selectCase(c.id))" :aria-label="`${c.title} 사건 기록 · 증거 v${c.version}`">
        <span class="file-content"><strong>{{c.title}}</strong><span class="file-summary">{{c.summary}}</span></span>
        <span class="file-version">v{{c.version}}</span>
        <span class="file-open">{{busy?'불러오는 중':'열기'}} <span aria-hidden="true">→</span></span>
      </button>
    </div>
    <div v-else class="library-empty"><h3>{{search?'일치하는 사건이 없습니다.':'아직 사건이 없습니다.'}}</h3><p>{{search?'다른 검색어로 찾아보세요.':'새 합성 데모를 시작해 사건을 불러오세요.'}}</p><button v-if="search" class="subtle" @click="search=''">검색 초기화</button></div>
    <div class="library-tools">
      <GeneralCaseComposer id="library-composer" ref="composer" :create-case="createGeneralCase" :disabled="busy" />
      <details class="practice-entry">
        <summary>연습 사건 더 불러오기</summary>
        <p>신원 확인, 증거 부족, 다른 날짜의 기록을 다루는 가상 사건입니다. 각 사건에서 새 증거를 두 번 공개해 판단을 비교하세요.</p>
        <div class="practice-options">
          <button class="secondary" :disabled="busy" @click="addPractice">테스트 사건 3개 추가</button>
          <button class="secondary" :disabled="busy" @click="addGeneralPractice">다중 증거 검토용 사건 12개 추가</button>
        </div>
      </details>
    </div>
    <div class="library-bottom"><div class="library-context"><p>사건과 분석 기록은 로그인한 계정에 저장됩니다.</p><ModelDetails :model="model" /></div><button class="secondary" aria-label="새 합성 사건 추가" :disabled="busy" @click="freshDemo">새 합성 사건 추가</button></div>
  </main>
  <div v-else class="shell">
    <aside class="sidebar" aria-label="사건 선택">
      <a class="back-library" href="/cases">← 사건 기록실</a>
      <h2>
        사건 목록 <span>{{ cases.length }}</span>
      </h2>
      <nav>
        <button
          v-for="c in cases"
          :key="c.id"
          class="case-button"
          :class="{ selected: detail?.case_id === c.id }"
          :aria-current="detail?.case_id === c.id ? 'page' : undefined"
          :disabled="busy || active || lifecycleBusy"
          @click="action(() => selectCase(c.id))"
        >
          <strong>{{ c.title }}</strong
          ><span>사건 기록 · 증거 v{{ c.version }}</span>
        </button>
      </nav>
      <p class="sidebar-note">
        기록은 로그인한 계정에 저장됩니다.
      </p>
      <button class="subtle" :disabled="busy || active || lifecycleBusy" @click="freshDemo">
        새 합성 사건 추가
      </button>
      <ModelDetails :model="model" />
    </aside>
    <main id="workspace" class="workspace" v-if="detail">
      <div
        v-if="model?.backend === 'fixture'"
        class="fixture-notice"
        role="status"
      >
        테스트 모드 · 실제 모델을 호출하지 않는 예시 분석입니다.
      </div>
      <section class="case-header">
        <div>
          <p class="breadcrumb"><a href="/cases">사건 기록</a><span>/</span>검토실</p>
          <h1 ref="workspaceHeading" tabindex="-1">{{ detail.title }}</h1>
          <p class="summary">{{ detail.summary }}</p>
        </div>
        <span class="version">증거 v{{ detail.evidence_version }}</span
        ><button
          class="primary mobile-analysis"
          :disabled="caseWriteBlocked"
          @click="analyze"
        >
          {{
            active ? "분석 진행 중" : job ? "현재 증거로 재분석" : "분석 시작"
          }}
        </button>
      </section>
      <p v-if="provenanceReadOnly" class="version-notice" role="status">읽기 전용 사건입니다. 자료 출처와 처리 승인을 확인하기 전까지 공개 기록과 과거 분석만 열람할 수 있습니다. 새 질문·분석·증거 공개·사건 상태 변경은 잠겨 있습니다.</p>
      <nav class="workspace-jumps" aria-label="사건 검토 영역"><a href="#evidence-heading">공개 증거 ↓</a><a href="#conversation-heading">사건에 질문 ↓</a><a href="#analysis-heading">분석과 판단 ↓</a></nav>
      <CaseLifecycle :key="detail.case_id" :case-id="detail.case_id" :evidence-version="detail.evidence_version" :refresh-key="lifecycleRefreshKey" :api="api" :active="!!activeCaseJob" :busy="busy" :read-only="provenanceReadOnly" @state="lifecycleState" @pending="lifecyclePending" @refresh-case="action(()=>selectCase(detail.case_id))" />
      <div class="workspace-grid">
        <section class="evidence-column" aria-labelledby="evidence-heading">
          <div class="section-heading">
            <h2 id="evidence-heading">
              공개 증거 <span>{{ detail.evidence.length }}</span>
            </h2>
          </div>
          <article
            v-for="(e, i) in detail.evidence"
            :key="e.id"
            :id="`evidence-${e.id}`"
            tabindex="-1"
            class="evidence-record"
            :class="{ highlighted: selectedEvidence === e.id }"
          >
            <div class="record-meta">
              <span
                >{{ e.kind === "statement" ? "진술" : "기록" }}
                {{ String(i + 1).padStart(2, "0") }}</span
              ><span>공개 v{{ e.released_version }}</span>
            </div>
            <h3>{{ e.title }}</h3>
            <p v-if="selectedQuote?.evidence_id===e.id && selectedQuoteParts">{{selectedQuoteParts.before}}<mark :id="`quote-${e.id}`" tabindex="-1">{{selectedQuoteParts.quote}}</mark>{{selectedQuoteParts.after}}</p>
            <p v-else>{{ e.text }}</p>
            <small :title="e.id">{{ e.id }}</small>
          </article>
          <div class="release-panel">
            <h3>
              {{
                detail.pending_count
                  ? `공개 대기 증거 ${detail.pending_count}건`
                  : "증거 공개 완료"
              }}
            </h3>
            <p>
              {{
                provenanceReadOnly
                  ? "읽기 전용으로 새 증거 공개가 잠겨 있습니다."
                  : detail.pending_count
                  ? "새 증거가 공개되면 현재 증거로 다시 분석할 수 있습니다."
                  : "이전 분석과 현재 결과를 비교할 수 있습니다."
              }}
            </p>
            <button
              v-if="detail.pending_count"
              class="secondary"
              :disabled="caseWriteBlocked"
              @click="release"
            >
              새 증거 공개 <span>({{ detail.pending_count }}건 대기)</span>
            </button>
          </div>
        </section>
        <section class="analysis-column" aria-labelledby="analysis-heading">
          <CaseConversation :key="detail.case_id" :case-id="detail.case_id" :version="detail.evidence_version" :api="api" :read-only="caseReadOnly" :busy="busy || lifecycleBusy || !!active" :evidence-title="evidenceTitle" @cite="showCitation" @active="conversationActive=$event" />
          <div class="section-heading">
            <h2 id="analysis-heading">분석과 판단</h2>
            <button
              class="primary analysis-action"
              :disabled="caseWriteBlocked"
              @click="analyze"
            >
              {{
                active
                  ? "분석 진행 중"
                  : job
                    ? "현재 증거로 재분석"
                    : "분석 시작"
              }}
            </button>
          </div>
          <div v-if="!job" class="empty-state">
            <h3>아직 분석 결과가 없습니다.</h3>
            <p>
              {{ provenanceReadOnly ? '읽기 전용 사건에는 새 분석을 요청할 수 없습니다. 현재 공개 기록을 확인하세요.' : '공개 증거를 확인한 뒤 ‘분석 시작’을 누르세요.' }}
            </p>
          </div>
          <template v-else>
            <div class="job-header" :data-job-id="job.id">
              <strong role="status">{{ statuses[job.status] }}</strong
              ><span>증거 v{{ job.version }}</span
              ><button
                v-if="active"
                class="subtle"
                :disabled="provenanceReadOnly || busy || !!job.cancel_requested"
                @click="cancel"
              >
                {{job.cancel_requested ? '취소 요청됨' : '분석 취소'}}</button
              ><button
                class="subtle"
                :disabled="busy"
                @click="action(refreshJob)"
              >
                상태 새로고침
              </button>
            </div>
            <p v-if="active && job.cancel_requested" class="version-notice" role="status">취소를 요청했습니다. 모델 연산이 중지되고 서버가 종료 상태를 확인할 때까지 기다립니다.</p>
            <p
              v-if="job.version !== detail.evidence_version"
              class="version-notice"
            >
              이 결과에 사용된 증거는 v{{ job.version }}입니다. 현재 v{{
                detail.evidence_version
              }}입니다. {{ provenanceReadOnly ? '읽기 전용 사건에서는 과거 결과를 그대로 확인할 수 있습니다.' : '새 증거를 반영하려면 재분석하세요.' }}
            </p>
            <p v-if="job.error" class="job-error" role="alert">
              {{ errors[job.error] || job.error }}
            </p>
            <details v-if="active || events.length" class="event-panel" :open="!!active">
              <summary>{{active ? "분석 진행 기록" : "실행 기록 보기"}}</summary>
              <p v-if="connected" class="muted" role="status">
                {{ connected }}
              </p>
              <ol aria-label="실제 분석 진행 기록">
                <li v-for="e in events" :key="e.id">
                  <time>{{ formatTime(e.created) }}</time
                  ><span>{{ eventNames[e.type] || e.type }}</span>
                </li>
              </ol>
            </details>
            <template v-if="Array.isArray(job.result?.findings)">
              <article
                v-for="finding in job.result.findings"
                :key="finding.claim_id"
                class="finding"
              >
                <div class="finding-title">
                  <span class="label" :class="finding.label">{{
                    labels[finding.label]
                  }}</span
                  ><span class="muted">주장 검토</span>
                </div>
                <h3>{{ claimText(finding.claim_id) }}</h3>
                <p>{{ finding.rationale }}</p>
                <GeneralReview v-if="reviewFor(finding.claim_id)" :review="reviewFor(finding.claim_id)" :finding="finding" :evidence-title="evidenceTitle" @cite="showCitation" />
                <div class="citations">
                  <span>근거</span
                  ><button
                    v-for="id in finding.evidence_ids"
                    :key="id"
                    class="citation"
                    @click="showEvidence(id)"
                  >
                    {{ evidenceTitle(id) }} ↗</button
                  ><span v-if="!finding.evidence_ids.length" class="muted"
                    >검증된 인용 없음</span
                  >
                </div>
                <div v-if="finding.missing_information.length" class="missing">
                  <h4>추가 확인</h4>
                  <ul>
                    <li v-for="item in finding.missing_information" :key="item">
                      {{ item }}
                    </li>
                  </ul>
                </div>
                <p
                  v-if="
                    finding.validation_notes.includes('MODEL_OUTPUT_INVALID')
                  "
                  class="job-error"
                >
                  모델 출력 검증 실패로 판단을 보류했습니다.
                </p>
                <p
                  v-if="
                    finding.validation_notes.includes(
                      'IDENTITY_PRECONDITION_UNMET',
                    )
                  "
                  class="fineprint"
                >
                  검증 단계에서 동일인 식별에 필요한 전제가 없는 점을
                  확인했습니다.
                </p>
              </article>
              <details v-if="!job.result.reasoning" class="hypotheses">
                <summary>추가 가설 확인</summary>
                <p v-if="!job.result.hypotheses.length" class="muted">
                  이 분석에서는 검증 가능한 추가 가설을 제시하지 않았습니다.
                </p>
                <p v-for="h in job.result.hypotheses" :key="h">{{ h }}</p>
              </details>
              <details class="limitations">
                <summary>분석의 범위와 한계</summary>
                <ul>
                  <li v-for="l in job.result.limitations" :key="l">
                    {{ errors[l] || l }}
                  </li>
                </ul>
                <p>
                  {{
                    job.result.provenance === "local_mlx"
                      ? "실제 모델 호출"
                      : "모의 모델 호출"
                  }}
                  {{ job.result.usage.model_calls }}회 · 입력
                  {{ job.result.usage.prompt_tokens }} / 출력
                  {{ job.result.usage.generation_tokens }} 토큰 · 생성
                  {{ job.result.usage.seconds.toFixed(2) }}초
                </p>
                <p>결과 출처: {{ job.result.provenance }}</p>
              </details>
              <section v-if="eligibleBefore.length" class="comparison">
                <h3>이전 결과와 비교</h3>
                <div class="compare-controls">
                  <label for="before">비교할 이전 분석</label
                  ><select id="before" v-model="beforeId">
                    <option value="" disabled>분석을 선택하세요</option>
                    <option
                      v-for="j in eligibleBefore"
                      :key="j.id"
                      :value="j.id"
                    >
                      증거 v{{ j.version }} · {{ formatTime(j.created) }}
                    </option></select
                  ><button
                    class="secondary"
                    :disabled="!beforeId || busy"
                    @click="compare"
                  >
                    결과 비교
                  </button>
                </div>
                <div v-if="comparison" class="diff" data-testid="comparison">
                  <p>
                    증거 v{{ comparison.before_version }} → v{{
                      comparison.after_version
                    }}
                  </p>
                  <div v-for="f in comparison.findings" :key="f.claim_id">
                    <h4>{{ claimText(f.claim_id) }}</h4>
                    <strong>{{ f.changed ? "판단 변경" : "판단 유지" }}</strong>
                    <p>
                      {{ labels[f.before?.label] || "이전 판단 없음" }} →
                      {{ labels[f.after.label] }}
                    </p>
                    <div class="diff-columns">
                      <section><span class="diff-caption">이전 · 증거 v{{comparison.before_version}}</span><h4>이전 판단 근거</h4><p>{{f.before?.rationale || "이전 결과가 없습니다."}}</p><div class="citations"><button v-for="id in f.before?.evidence_ids || []" :key="id" class="citation" @click="showEvidence(id)">{{evidenceTitle(id)}} ↗</button></div></section>
                      <section><span class="diff-caption">현재 · 증거 v{{comparison.after_version}}</span><h4>현재 판단 근거</h4><p>{{f.after.rationale}}</p><div class="citations"><button v-for="id in f.after.evidence_ids" :key="id" class="citation" @click="showEvidence(id)">{{evidenceTitle(id)}} ↗</button></div></section>
                    </div>
                    <p class="muted">{{ comparison.reason }}</p>
                  </div>
                  <p v-if="comparison.model_changed">
                    실행 모델도 변경되었습니다. 증거만의 효과로 해석할 수
                    없습니다.
                  </p>
                  <p v-if="comparison.analysis_contract_changed">분석 방식도 변경되었습니다. 증거만의 효과로 해석할 수 없습니다.</p>
                </div>
              </section>
            </template>
            <p v-else-if="job.result" class="version-notice" role="status">이전 형식으로 저장된 결과라 현재 화면에서 상세 표시할 수 없습니다. 저장된 결과와 분석 이력은 그대로 보존하며, 형식 호환 확인이 필요합니다.</p>
          </template>
          <section class="history" v-if="jobs.length">
            <h3>분석 이력</h3>
            <ul>
              <li v-for="j in jobs" :key="j.id">
                <button
                  class="history-button"
                  :class="{ selected: job?.id === j.id }"
                  :disabled="active || busy"
                  @click="inspectJob(j)"
                >
                  <span>증거 v{{ j.version }}</span
                  ><span>{{ statuses[j.status] }}</span
                  ><time>{{ formatTime(j.created) }}</time>
                </button>
              </li>
            </ul>
          </section>
        </section>
      </div>
    </main>
    <main v-else id="workspace" class="entry">
      <div><h1>사건을 확인할 수 없습니다.</h1><a href="/cases" class="rc-button">사건 기록으로 돌아가기</a></div>
    </main>
  </div>
  <footer>
    RE:CASE · 분석 결과는 실제 사건의 사실·유죄 판단을 대신하지 않습니다.
  </footer>
</div>
</template>

<style scoped src="../style.css"></style>
<style scoped>
mark {background:var(--accent);color:var(--accent-ink);padding-inline:2px}
.case-library,.workspace {overflow-wrap:anywhere}
.file-summary {display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;line-clamp:2;overflow:hidden}
.library-heading {display:flex;align-items:flex-start;justify-content:space-between;gap:28px}
.library-heading>div {min-width:0;max-width:72ch}
.library-create {display:inline-flex;align-items:center;gap:18px;flex-shrink:0}
.library-tools {margin-block-start:32px}
.practice-entry {margin-block:16px}
.practice-entry summary {padding-block:12px;font-size:14px;font-weight:550;cursor:pointer}
.practice-entry p {max-width:66ch;font-size:13px;line-height:1.8;color:var(--muted);margin:8px 0 0}
.practice-options {display:flex;flex-wrap:wrap;gap:12px;margin-block-start:16px}
.practice-notice {font-size:13px;line-height:1.8;margin-block:12px;color:var(--text)}
@media(max-width:700px){.library-heading{flex-direction:column;gap:16px}.library-create{align-self:flex-start}.practice-options{align-items:flex-start;flex-direction:column}.practice-options button{max-width:100%;text-align:left;white-space:normal}}
</style>
