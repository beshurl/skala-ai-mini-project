<script setup lang="ts">
withDefaults(defineProps<{href?:string;hero?:boolean;compact?:boolean}>(),{href:'/',hero:false,compact:false});
</script>
<template><a :href="href" class="rc-brand" :class="{'rc-brand--compact':compact}" :id="hero?'brand-link':undefined" aria-label="RE:CASE 첫 화면"><span class="rc-brand__seal" aria-hidden="true">R</span><span class="rc-brand__word">RE<span>:</span>CASE</span></a></template>
<style scoped>
.rc-brand{min-height:44px;display:inline-flex;align-items:center;gap:11px;text-decoration:none;flex-shrink:0;color:var(--text)}.rc-brand__seal{display:grid;place-items:center;width:31px;height:37px;border:1px solid var(--accent);font:22px/1 var(--font-display);color:var(--accent);border-radius:1px 1px 10px 1px}.rc-brand__word{font:20px/1 var(--font-display);letter-spacing:.06em;white-space:nowrap}.rc-brand__word>span{color:var(--accent)}.rc-brand--compact .rc-brand__seal{width:27px;height:33px}.rc-brand--compact .rc-brand__word{font-size:18px}@media(max-width:400px){.rc-brand__word{font-size:18px}.rc-brand__seal{width:27px;height:33px}}
</style>
