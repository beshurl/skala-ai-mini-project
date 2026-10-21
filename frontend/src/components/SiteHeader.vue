<script setup lang="ts">
import {ref} from 'vue';
import BrandMark from './BrandMark.vue';
import {account, logout as signOut} from '../auth';
import {navigate} from '../navigation';
withDefaults(defineProps<{active?:string;hero?:boolean}>(),{active:'',hero:false});
const busy=ref(false), error=ref('');
async function logout(){if(busy.value)return;busy.value=true;error.value='';try{await signOut();navigate('/login');}catch(e){error.value=(e as Error).message;}finally{busy.value=false;}}
</script>
<template>
<header class="rc-header" :class="{'rc-header--hero':hero}">
  <BrandMark :href="hero?'#hero':'/'" :hero="hero"/>
  <nav v-if="hero" class="rc-header__story" aria-label="서비스 소개 바로가기"><button type="button" data-jump="1000">기록 읽기</button><button type="button" data-jump="1800">근거 검토</button><button type="button" data-jump="2640">변화 비교</button></nav>
  <nav v-else class="rc-header__nav" aria-label="사용자 메뉴"><a href="/cases" :aria-current="active==='cases'?'page':undefined">사건 기록</a><a href="/history" :aria-current="active==='history'?'page':undefined">분석 이력</a><a href="/settings" :aria-current="active==='settings'?'page':undefined">실행 정보</a></nav>
  <div class="rc-header__account">
    <template v-if="account"><span class="account-name" :title="account.name">{{account.name}}</span><a v-if="account.role==='admin'" href="/admin">관리자</a><button type="button" :disabled="busy" @click="logout">{{busy?'로그아웃 중…':'로그아웃'}}</button></template>
    <a v-else href="/login">로그인</a>
    <a v-if="hero" class="rc-button rc-header__action" href="/cases">사건 기록 열기 <span aria-hidden="true">↗</span></a>
  </div>
  <p v-if="error" class="header-error" role="alert">{{error}}</p>
</header>
</template>
<style scoped>
.rc-header{min-height:78px;padding:0 clamp(20px,4vw,64px);display:flex;align-items:center;gap:48px;border-bottom:1px solid var(--line);background:var(--bg)}.rc-header__nav{display:flex;align-self:stretch;gap:30px}.rc-header__nav a{position:relative;display:flex;align-items:center;min-height:46px;color:var(--muted);text-decoration:none;font-size:13px}.rc-header__nav a:hover,.rc-header__nav a[aria-current]{color:var(--text)}.rc-header__nav a[aria-current]::after{content:'';position:absolute;bottom:-1px;left:0;right:0;height:2px;background:var(--accent)}.rc-header--hero{position:absolute;z-index:90;inset:0 0 auto;min-height:98px;border:0;background:linear-gradient(180deg,#0c0d0cdc,transparent);justify-content:space-between}.rc-header__story{display:flex;gap:30px}.rc-header__story button{min-height:44px;border:0;background:none;color:var(--text);font-size:12px;padding:8px 4px}.rc-header__story button:hover{color:var(--accent)}.rc-header__action{font-size:12px;border-color:var(--accent);color:var(--accent);background:#11121066}@media(max-width:850px){.rc-header{gap:32px;padding-inline:24px}.rc-header--hero{min-height:82px}.rc-header__story{gap:16px}}@media(max-width:600px){.rc-header{min-height:72px;padding-inline:20px;gap:24px;flex-wrap:wrap}.rc-header__nav{gap:22px;width:100%;order:2;min-height:48px}.rc-header:has(.rc-header__nav){padding-top:20px;gap:12px}.rc-header__story{display:none}.rc-header--hero{gap:12px;flex-wrap:nowrap}.rc-header__action{min-height:44px;padding:8px 12px;font-size:11px}}
.rc-header__account{margin-left:auto;display:flex;gap:18px;align-items:center;font-size:12px}.rc-header__account>a:not(.rc-button),.rc-header__account>button{min-height:44px;display:inline-flex;align-items:center;border:0;background:none;color:var(--muted);text-decoration:none;padding:0}.rc-header__account>a:hover,.rc-header__account>button:hover{color:var(--text)}.account-name{max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.header-error{width:100%;font-size:12px;color:var(--danger);margin:0}@media(max-width:850px){.account-name{max-width:80px}.rc-header--hero .rc-header__story{display:none}}@media(max-width:600px){.rc-header__account{gap:12px}.account-name{display:none}.rc-header--hero .rc-header__account .rc-button{display:none}}
</style>
