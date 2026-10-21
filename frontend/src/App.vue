<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, onBeforeUnmount, watch } from 'vue';
import {location, followLink, navigate} from './navigation';
import {account, authReady, authError, refreshAccount, loginPath} from './auth';
const Landing = defineAsyncComponent(() => import('./views/LandingView.vue'));
const Workspace = defineAsyncComponent(() => import('./views/CaseWorkspace.vue'));
const Records = defineAsyncComponent(() => import('./views/RecordsView.vue'));
const Admin = defineAsyncComponent(() => import('./views/AdminView.vue'));
const Auth = defineAsyncComponent(() => import('./views/AuthView.vue'));
const route = computed(() => location.value);
watch(route, path => {
  // Workspace sets the loaded case title; keep it when its SPA path changes.
  if(path.startsWith('/cases/')) return;
  const title = path === '/' ? '증거 기반 AI 미제사건 재수사 지원'
    : path === '/login' ? '로그인' : path === '/signup' ? '회원가입'
    : path === '/history' ? '분석 이력' : path === '/settings' ? '실행 정보'
    : path.startsWith('/admin') ? '운영자 콘솔' : '사건 기록';
  document.title = `${title} · RE:CASE`;
}, {immediate:true});
const protectedRoute = computed(() => /^\/(?:cases|history|settings|admin)(?:\/|$)/.test(route.value));
const caseId = computed(() => route.value.startsWith('/cases/') ? decodeURIComponent(route.value.slice(7)) : undefined);
watch([route, authReady, account],()=>{if(protectedRoute.value && authReady.value && !authError.value && !account.value) navigate(loginPath());});
function expired(){account.value=null; if(protectedRoute.value)navigate(loginPath());}
onMounted(()=>{void refreshAccount();window.addEventListener('recase-auth-required',expired);});
onBeforeUnmount(()=>window.removeEventListener('recase-auth-required',expired));
</script>
<template>
<div @click="followLink">
  <Landing v-if="route === '/'" />
  <Auth v-else-if="route === '/login' || route === '/signup'" :signup="route === '/signup'" />
  <main v-else-if="protectedRoute && (!authReady || !account)" class="auth-check" role="status"><h1>{{authError?'로그인 상태를 확인하지 못했습니다.':'로그인 상태를 확인하고 있습니다.'}}</h1><p v-if="authError">{{authError}}</p><button v-if="authError" class="rc-button" @click="refreshAccount">다시 확인</button></main>
  <Admin v-else-if="route === '/admin' || route.startsWith('/admin/')" :section="route.slice(7) || 'overview'" />
  <Workspace v-else-if="route === '/cases' || route.startsWith('/cases/')" :case-id="caseId" />
  <Records v-else-if="route === '/history' || route === '/settings'" :view="route.slice(1)" :key="route" />
  <main v-else class="route-missing"><h1>페이지를 찾을 수 없습니다.</h1><a href="/cases">사건 기록으로 돌아가기</a></main>
</div>
</template>
<style src="./styles/system.css"></style>
<style>.auth-check{max-width:650px;margin:16vh auto;padding:24px}.auth-check h1{font-size:23px;line-height:1.6;font-weight:500}</style>
