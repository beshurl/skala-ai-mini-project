<!-- THESIS: Review a model assessment through its exact sources and open questions.
OWN-WORLD: Inherit the workspace's charcoal, ivory, gold, spacing and text controls.
STORY: Read observations, inspect counter-sources, then choose what a person checks.
FIRST VIEWPORT: Extend the existing finding below its conclusion and citations.
FORM: Local Operate/Read extension; no replacement composition or visual identity. -->
<script setup lang="ts">
import type { Citation, GeneralReview, Finding } from '../types';
defineProps<{ review: GeneralReview; finding: Finding; evidenceTitle: (id: string) => string }>();
const emit = defineEmits<{ cite: [citation: Citation] }>();
</script>

<template>
  <section class="general-review" aria-label="다중 증거 검토 상세">
    <p v-if="review.status==='SOURCE_CHECKED_MODEL_ASSESSMENT'" class="review-scope">원문 인용 구간을 확인한 모델 검토입니다. 자료 해석과 판단의 정확성은 별도 확인이 필요합니다.</p>
    <p v-else-if="review.status==='NO_EVIDENCE'" class="review-scope">공개된 증거가 없어 모델 검토를 실행하지 않았습니다.</p>
    <p v-if="review.status==='INVALID' || review.status==='BUDGET_BLOCKED'" role="status">분석 실행을 검증하지 못했습니다. 아래 실행 정보와 처리 범위를 확인하세요.</p>
    <section v-if="finding.citations?.length">
      <h4>판단에 연결한 원문</h4>
      <figure v-for="(c,index) in finding.citations" :key="`${c.evidence_id}-${index}`">
        <blockquote>{{c.quote}}</blockquote>
        <figcaption><button class="citation" @click="emit('cite',c)">{{evidenceTitle(c.evidence_id)}} · 원문 구간 열기 ↗</button></figcaption>
      </figure>
    </section>
    <section v-if="finding.counter_citations?.length">
      <h4>함께 확인할 반대 자료</h4>
      <figure v-for="(c,index) in finding.counter_citations" :key="`${c.evidence_id}-${index}`">
        <blockquote>{{c.quote}}</blockquote><figcaption><button class="citation" @click="emit('cite',c)">{{evidenceTitle(c.evidence_id)}} ↗</button></figcaption>
      </figure>
    </section>
    <section v-for="group in [{title:'자료에서 검토한 내용',items:review.observations},{title:'자료 사이의 충돌',items:review.conflicts}]" :key="group.title" v-show="group.items.length">
      <h4>{{group.title}}</h4>
      <ul><li v-for="(item,index) in group.items" :key="index"><p>{{item.text}}</p><button v-for="(c,i) in item.citations" :key="i" class="citation" @click="emit('cite',c)">{{evidenceTitle(c.evidence_id)}} ↗</button></li></ul>
    </section>
    <section v-if="finding.assumptions?.length"><h4>판단에 필요한 전제</h4><ul><li v-for="item in finding.assumptions" :key="item">{{item}}</li></ul></section>
    <section v-if="review.time_checks.length"><h4>시간 조건 계산</h4><div v-for="(item,index) in review.time_checks" :key="index"><p>{{item.reason}}</p><p class="review-scope">{{item.scope}}</p><button v-for="(c,i) in item.citations" :key="i" class="citation" @click="emit('cite',c)">{{evidenceTitle(c.evidence_id)}} ↗</button></div></section>
    <section v-if="review.hypotheses.length">
      <h4>검토 가설 <span class="muted">· 미검증</span></h4>
      <ol><li v-for="(h,index) in review.hypotheses" :key="index"><p>{{h.text}}</p><p class="review-scope">재검토 조건: {{h.reconsider_when}}</p><div><button v-for="(c,i) in h.citations" :key="i" class="citation" @click="emit('cite',c)">근거 · {{evidenceTitle(c.evidence_id)}} ↗</button></div><div v-if="h.counter_citations.length"><button v-for="(c,i) in h.counter_citations" :key="i" class="citation" @click="emit('cite',c)">반대 자료 · {{evidenceTitle(c.evidence_id)}} ↗</button></div></li></ol>
    </section>
    <section v-if="review.next_checks.length">
      <h4>사람이 확인할 항목</h4>
      <ol><li v-for="(item,index) in review.next_checks" :key="index"><p>{{item.text}}</p><p class="review-scope">{{item.purpose}}</p><p class="review-scope">재검토 시점: {{item.reconsider_when}}</p><button v-for="(c,i) in item.citations" :key="i" class="citation" @click="emit('cite',c)">{{evidenceTitle(c.evidence_id)}} ↗</button></li></ol>
    </section>
  </section>
</template>

<style scoped>
.citation{min-height:44px;font:inherit;font-size:12px;font-weight:600;color:var(--accent);background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:7px 10px;line-height:1.6;cursor:pointer}.citation:hover{border-color:var(--accent)}
.general-review{margin-block-start:var(--space);overflow-wrap:anywhere}.general-review section+section{margin-block-start:28px}.general-review h4{font-size:14px;margin-block:0 12px;color:var(--text)}.general-review p{line-height:1.8;margin-block:8px}.review-scope{color:var(--muted);font-size:13px}.general-review figure{margin:0 0 16px}.general-review blockquote{margin:0;padding:12px 16px;background:var(--surface-raised);font-size:14px;line-height:1.9;white-space:pre-wrap}.general-review figcaption{margin-block-start:4px}.general-review ul,.general-review ol{padding-inline-start:20px;margin:0}.general-review li+li{margin-block-start:16px}.general-review .citation{white-space:normal;text-align:start;margin-inline-end:8px}.general-review .citation:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
</style>
