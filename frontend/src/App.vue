<!-- Scope: extend the supplied Vue/SSE working-screen pattern into the requested case workflow.
     Dark system type and violet actions inherit the reference; evidence, real state and provenance lead. -->
<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from "vue";

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
const errors = {
  EVIDENCE_VERSION_CHANGED:
    "증거 버전이 바뀌었습니다. 사건을 새로고침한 뒤 다시 분석하세요.",
  MODEL_NOT_READY:
    "모델 준비에 실패했습니다. 서버의 /ready 상태와 실행 기록을 확인하세요.",
  ANALYSIS_QUEUE_FULL:
    "분석 대기열이 가득 찼습니다. 진행 중인 작업이 끝난 뒤 다시 시도하세요.",
  JOB_ALREADY_ACTIVE:
    "이 사건의 분석이 이미 진행 중입니다. 상태를 새로고침하세요.",
  SERVER_RESTARTED:
    "서버가 다시 시작되어 작업이 종료되었습니다. 새 분석을 요청하세요.",
  ANALYSIS_TIMEOUT:
    "분석 시간 제한을 초과했습니다. 작업을 다시 요청할 수 있습니다.",
  MCP_TOOL_FAILED:
    "증거 도구 연결에 실패했습니다. 서버 상태를 확인한 뒤 다시 요청하세요.",
  ANALYSIS_FAILED:
    "분석을 완료하지 못했습니다. 서버 실행 기록을 확인한 뒤 다시 요청하세요.",
  CSRF_REQUIRED: "세션이 변경되었습니다. 페이지를 새로고침하세요.",
  DEMO_SESSION_REQUIRED: "데모 세션이 만료되었습니다. 다시 입장하세요.",
  LOCAL_AUTH_REQUIRED: "로컬 로그인이 만료되었습니다. 페이지를 새로고침한 뒤 접근키로 다시 로그인하세요.",
  NOT_FOUND: "접근 가능한 자료를 찾지 못했습니다.",
  MODEL_OUTPUT_INVALID: "모델의 출력 형식이나 근거 검증에 실패했습니다.",
};

Object.assign(errors, {
  CANCELLED: "분석 요청이 취소되었습니다.",
  RETRIEVAL_INSUFFICIENT:
    "관련 공개 증거를 충분히 찾지 못했습니다. 자료 공개 상태를 확인하세요.",
});

async function api(path, options = {}) {
  const controller = new AbortController(),
    timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(path, {
      credentials: "same-origin",
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(session.value ? { "X-Recase-CSRF": session.value.csrf } : {}),
        ...options.headers,
      },
    });
    const data = await response.json();
    if (!response.ok) {
      const code = typeof data.detail === "string" ? data.detail : data.error;
      throw new Error(
        errors[code] ||
          {
            CHRONOLOGICAL_RESULTS_REQUIRED:
              "현재 분석보다 이전에 실행한 결과를 선택하세요.",
            COMPARABLE_RESULTS_REQUIRED:
              "같은 사건에서 결과가 저장된 분석을 선택하세요.",
          }[code] ||
          `요청을 처리하지 못했습니다 (${response.status}). 상태를 새로고침하고 다시 시도하세요.`,
      );
    }
    return data;
  } catch (err) {
    if (err.name === "AbortError")
      throw new Error(
        "서버 응답 시간이 초과되었습니다. 서버 연결을 확인한 뒤 다시 시도하세요.",
      );
    if (err instanceof TypeError)
      throw new Error(
        "서버에 연결할 수 없습니다. 서버 실행 상태를 확인하고 다시 시도하세요.",
      );
    throw err;
  } finally {
    clearTimeout(timeout);
  }
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
  const token = ++selection;
  disconnect();
  comparison.value = null;
  job.value = null;
  events.value = [];
  beforeId.value = "";
  selectedEvidence.value = "";
  const data = await api(`/api/cases/${id}`);
  if (token !== selection) return;
  detail.value = data;
  await loadHistory();
  job.value = jobs.value[0] || null;
  if (active.value) subscribe(job.value.id);
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
    await initialize();
  });
}
async function initialize() {
  const s = await api("/api/session");
  session.value = s;
  model.value = s.model;
  cases.value = await api("/api/cases");
  if (cases.value.length) await selectCase(cases.value[0].id);
}
async function analyze() {
  await action(async () => {
    job.value = await api(`/api/cases/${detail.value.case_id}/analyses`, {
      method: "POST",
      body: JSON.stringify({ evidence_version: detail.value.evidence_version }),
    });
    comparison.value = null;
    beforeId.value = "";
    subscribe(job.value.id);
    await loadHistory();
  });
}
async function release() {
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
  disconnect();
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
    const response = await fetch("/api/session");
    if (response.ok) await initialize();
  } catch {
    error.value = "서버 연결을 확인한 뒤 다시 시도하세요.";
  } finally {
    booting.value = false;
  }
});
onBeforeUnmount(disconnect);
</script>

<template>
  <a class="skip" href="#workspace">본문으로 이동</a>
  <header class="topbar">
    <a class="wordmark" href="/">RE<span>:</span>CASE</a
    ><span class="product-name">증거 검토실</span
    ><span class="demo-tag">로컬 · 합성 사건</span>
  </header>
  <div v-if="error" class="error-banner" role="alert">
    <p>{{ error }}</p>
    <button class="subtle" @click="error = ''" aria-label="오류 알림 닫기">
      닫기
    </button>
  </div>
  <main v-if="booting" id="workspace" class="entry" aria-live="polite">
    <p>로컬 세션을 확인하고 있습니다.</p>
  </main>
  <main v-else-if="!session" id="workspace" class="entry">
    <div class="entry-copy">
      <span class="eyebrow">증거에 따라, 판단을 다시.</span>
      <h1>기록을 대조하고<br />변화를 확인하세요.</h1>
      <p>
        공개된 증거를 분석하고, 새 자료가 판단을 어떻게 바꾸는지 살펴보는 재수사
        시뮬레이터입니다.
      </p>
      <button class="primary" :disabled="busy" @click="enter">
        {{ busy ? "사건을 준비하고 있습니다…" : "로컬 데모 입장" }}
      </button>
      <p class="fineprint">
        합성 사건만 사용합니다. 분석 결과는 실제 범행이나 유죄를 판단하지
        않습니다.
      </p>
    </div>
    <div class="entry-flow" aria-label="검토 순서">
      <span>공개 증거 확인</span><b>↓</b><span>근거가 연결된 분석</span><b>↓</b
      ><span>새 증거 공개 · 재검토</span><b>↓</b><span>판단의 변화 비교</span>
    </div>
  </main>
  <div v-else class="shell">
    <aside class="sidebar" aria-label="사건 선택">
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
          :disabled="busy || active"
          @click="action(() => selectCase(c.id))"
        >
          <strong>{{ c.title }}</strong
          ><span>합성 기록 · 증거 v{{ c.version }}</span>
        </button>
      </nav>
      <p class="sidebar-note">
        기록은 이 브라우저의 로컬 데모 세션에 연결됩니다.
      </p>
      <button class="subtle" :disabled="busy || active" @click="freshDemo">
        새 합성 데모 시작
      </button>
      <details class="model-info">
        <summary>실행 모델 정보</summary>
        <dl v-if="model">
          <dt>모델</dt>
          <dd>{{ model.model }}</dd>
          <dt>백엔드</dt>
          <dd>{{ model.backend }}</dd>
          <dt>리비전</dt>
          <dd>{{ model.revision }}</dd>
          <dt>어댑터 적용</dt>
          <dd>{{ model.adapter_loaded ? "확인됨" : "적용 안 됨" }}</dd>
          <dt>프롬프트</dt>
          <dd>{{ model.prompt_version }}</dd>
        </dl>
      </details>
    </aside>
    <main id="workspace" class="workspace" v-if="detail">
      <div
        v-if="model?.backend === 'fixture'"
        class="fixture-notice"
        role="status"
      >
        모의 모델 테스트 모드입니다. 실제 LLM을 실행하지 않습니다.
      </div>
      <section class="case-header">
        <div>
          <p class="breadcrumb">사건 기록 / 합성 시뮬레이션</p>
          <h1>{{ detail.title }}</h1>
          <p class="summary">{{ detail.summary }}</p>
        </div>
        <span class="version">증거 v{{ detail.evidence_version }}</span
        ><button
          class="primary mobile-analysis"
          :disabled="busy || active"
          @click="analyze"
        >
          {{
            active ? "분석 진행 중" : job ? "현재 증거로 재분석" : "분석 시작"
          }}
        </button>
      </section>
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
            <p>{{ e.text }}</p>
            <small :title="e.id">{{ e.id }}</small>
          </article>
          <div class="release-panel">
            <h3>
              {{
                detail.pending_count
                  ? "다음 자료를 검토할 준비가 됐나요?"
                  : "모든 증거가 공개되었습니다."
              }}
            </h3>
            <p>
              {{
                detail.pending_count
                  ? "새 증거를 공개하면 증거 버전이 갱신됩니다. 분석은 직접 다시 시작하세요."
                  : "현재 증거와 분석 이력을 대조해 판단의 변화를 확인하세요."
              }}
            </p>
            <button
              v-if="detail.pending_count"
              class="secondary"
              :disabled="busy || active"
              @click="release"
            >
              새 증거 공개 <span>({{ detail.pending_count }}건 대기)</span>
            </button>
          </div>
        </section>
        <section class="analysis-column" aria-labelledby="analysis-heading">
          <div class="section-heading">
            <h2 id="analysis-heading">분석과 판단</h2>
            <button
              class="primary analysis-action"
              :disabled="busy || active"
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
            <h3>공개된 기록에서 시작합니다.</h3>
            <p>
              분석을 시작하면 주장과 기록의 관계, 연결된 근거, 추가로 확인할
              사항을 볼 수 있습니다.
            </p>
          </div>
          <template v-else>
            <div class="job-header">
              <strong role="status">{{ statuses[job.status] }}</strong
              ><span>증거 v{{ job.version }}</span
              ><button
                v-if="active"
                class="subtle"
                :disabled="busy"
                @click="cancel"
              >
                분석 취소</button
              ><button
                class="subtle"
                :disabled="busy"
                @click="action(refreshJob)"
              >
                상태 새로고침
              </button>
            </div>
            <p
              v-if="job.version !== detail.evidence_version"
              class="version-notice"
            >
              이 결과에 사용된 증거는 v{{ job.version }}입니다. 현재 v{{
                detail.evidence_version
              }}의 새 증거를 반영하려면 재분석하세요.
            </p>
            <p v-if="job.error" class="job-error" role="alert">
              {{ errors[job.error] || job.error }}
            </p>
            <div v-if="active || events.length" class="event-panel">
              <p v-if="connected" class="muted" role="status">
                {{ connected }}
              </p>
              <ol aria-label="실제 분석 진행 기록">
                <li v-for="e in events" :key="e.id">
                  <time>{{ formatTime(e.created) }}</time
                  ><span>{{ eventNames[e.type] || e.type }}</span>
                </li>
              </ol>
            </div>
            <template v-if="job.result">
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
              <div class="hypotheses">
                <h3>가설</h3>
                <p v-if="!job.result.hypotheses.length" class="muted">
                  이 분석에서는 검증 가능한 추가 가설을 제시하지 않았습니다.
                </p>
                <p v-for="h in job.result.hypotheses" :key="h">{{ h }}</p>
              </div>
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
                    <h4>이전 판단 근거</h4>
                    <p>{{ f.before?.rationale || "이전 결과가 없습니다." }}</p>
                    <div class="citations">
                      <button
                        v-for="id in f.before?.evidence_ids || []"
                        :key="id"
                        class="citation"
                        @click="showEvidence(id)"
                      >
                        {{ evidenceTitle(id) }} ↗
                      </button>
                    </div>
                    <h4>현재 판단 근거</h4>
                    <p>{{ f.after.rationale }}</p>
                    <div class="citations">
                      <button
                        v-for="id in f.after.evidence_ids"
                        :key="id"
                        class="citation"
                        @click="showEvidence(id)"
                      >
                        {{ evidenceTitle(id) }} ↗
                      </button>
                    </div>
                    <p class="muted">{{ comparison.reason }}</p>
                  </div>
                  <p v-if="comparison.model_changed">
                    실행 모델도 변경되었습니다. 증거만의 효과로 해석할 수
                    없습니다.
                  </p>
                </div>
              </section>
            </template>
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
      <p>접근 가능한 사건이 없습니다.</p>
    </main>
  </div>
  <footer>
    RE:CASE · 근거가 부족하면 판단을 보류합니다. 모든 사건과 인물은 합성
    자료입니다.
  </footer>
</template>
