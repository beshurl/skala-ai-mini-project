<script setup lang="ts">
import type {ModelInfo} from '../types';
defineProps<{model:ModelInfo|null}>();
</script>
<template><details class="rc-model"><summary>실행 모델 정보</summary><dl v-if="model"><dt>모델</dt><dd>{{model.model}}</dd><dt>백엔드</dt><dd>{{model.backend}}</dd><dt>리비전</dt><dd>{{model.revision}}</dd><dt>어댑터 적용</dt><dd>{{model.adapter_loaded?'확인됨':'적용 안 됨'}}</dd><dt>프롬프트</dt><dd>{{model.prompt_version}}</dd></dl></details></template>
<style scoped>.rc-model{font-size:11px;color:var(--muted);border-top:1px solid var(--line);margin-top:24px}.rc-model summary{cursor:pointer;min-height:44px;display:flex;align-items:center;gap:8px}.rc-model summary::before{content:'+';font-size:16px;color:var(--accent)}.rc-model[open] summary::before{content:'−'}.rc-model dl{display:grid;gap:5px;margin:0 0 16px}.rc-model dt{color:var(--muted);margin-top:8px}.rc-model dd{margin:0;color:var(--text);overflow-wrap:anywhere;font-size:11px}</style>
