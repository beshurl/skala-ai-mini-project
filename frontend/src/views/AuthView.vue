<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from 'vue';
import BrandMark from '../components/BrandMark.vue';
import { api } from '../api';
import { account, authReady, safeNext, type Account } from '../auth';
import { navigate, query } from '../navigation';

const props = defineProps<{signup:boolean}>();
const name = ref(''), email = ref(''), password = ref(''), confirmation = ref('');
const visible = ref(false), busy = ref(false), error = ref('');
let controller = new AbortController(), generation = 0;
const next = computed(() => safeNext(new URLSearchParams(query.value).get('next')));
const alternate = computed(() => `${props.signup?'/login':'/signup'}?next=${encodeURIComponent(next.value)}`);
watch(() => props.signup, () => {
  generation++; controller.abort(); controller = new AbortController();
  busy.value=false;password.value='';confirmation.value='';error.value='';visible.value=false;
  document.title=`${props.signup?'회원가입':'로그인'} · RE:CASE`;
},{immediate:true});
async function submit() {
  if(busy.value) return;
  error.value='';
  if(props.signup && password.value !== confirmation.value) {error.value='비밀번호가 서로 다릅니다. 다시 확인해주세요.';return;}
  busy.value=true;
  const current = ++generation;
  try {
    const body = {email:email.value.trim(),password:password.value,...(props.signup?{name:name.value.trim()}:{})};
    const profile = await api<Account>(props.signup?'/api/auth/register':'/api/auth/login', {method:'POST',body:JSON.stringify(body),signal:controller.signal});
    if(current !== generation) return;
    account.value = profile;
    authReady.value=true;
    navigate(next.value);
  } catch(e) {if(current === generation)error.value=(e as Error).message;}
  finally {if(current === generation){busy.value=false;password.value='';confirmation.value='';}}
}
onBeforeUnmount(()=>{generation++;controller.abort();password.value='';confirmation.value='';});
</script>

<template>
<div class="auth-page">
  <header class="auth-header"><BrandMark /><a href="/">서비스 소개</a></header>
  <main class="auth-layout">
    <aside class="auth-intro" aria-label="계정 안내">
      <p class="auth-context">증거 기반 미제사건 재수사 지원</p>
      <h2>기록을 이어서<br>검토하세요.</h2>
      <p>사건의 증거와 분석 이력을<br>하나의 계정에서 관리하세요.</p>
      <p class="auth-local">현재는 이 Mac에서 합성 사건을 제공합니다.</p>
    </aside>
    <section class="auth-form" aria-labelledby="auth-title">
      <h1 id="auth-title">{{signup?'회원가입':'로그인'}}</h1>
      <p class="auth-description">{{signup?'사건 기록을 검토할 계정을 만드세요.':'이메일과 비밀번호를 입력해주세요.'}}</p>
      <form @submit.prevent="submit" :aria-busy="busy">
        <label v-if="signup" for="account-name">이름<input id="account-name" v-model="name" autocomplete="name" required maxlength="40" :disabled="busy"></label>
        <label for="account-email">이메일<input id="account-email" v-model="email" type="email" autocomplete="username" inputmode="email" required maxlength="254" :disabled="busy" autocapitalize="none" spellcheck="false"></label>
        <label for="account-password">비밀번호
          <span class="password-field"><input id="account-password" v-model="password" :type="visible?'text':'password'" :autocomplete="signup?'new-password':'current-password'" required :minlength="signup?12:1" maxlength="128" :disabled="busy" :aria-describedby="signup?'password-help':undefined"><button type="button" class="password-toggle" @click="visible=!visible" :aria-pressed="visible" :disabled="busy">{{visible?'숨기기':'표시'}}</button></span>
        </label>
        <p v-if="signup" id="password-help" class="field-help">공백을 포함해 12자 이상 입력하세요.</p>
        <label v-if="signup" for="account-confirmation">비밀번호 확인<input id="account-confirmation" v-model="confirmation" :type="visible?'text':'password'" autocomplete="new-password" required minlength="12" maxlength="128" :disabled="busy"></label>
        <p v-if="error" class="auth-error" role="alert">{{error}}</p>
        <button class="rc-button auth-submit" type="submit" :disabled="busy">{{busy?(signup?'계정을 만들고 있습니다…':'로그인 중…'):(signup?'계정 만들기':'로그인')}}</button>
      </form>
      <p class="auth-alternate">{{signup?'이미 계정이 있나요?':'처음 이용하시나요?'}} <a :href="alternate" @click="busy && $event.preventDefault()">{{signup?'로그인':'회원가입'}}</a></p>
      <p class="auth-storage">가입 정보는 이 Mac에 저장됩니다.</p>
    </section>
  </main>
</div>
</template>

<style scoped>
.auth-page {
  min-height:100svh;
  background:var(--bg);
}
.auth-header {
  min-height:90px;
  max-width:1280px;
  margin:auto;
  padding:24px 48px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:24px;
}
.auth-header>a {
  font-size:13px;
  color:var(--muted);
  text-decoration:none;
  min-height:44px;
  display:flex;
  align-items:center;
}
.auth-header>a:hover {
  color:var(--text);
}
.auth-layout {
  max-width:1000px;
  margin:0 auto;
  padding:64px 48px 80px;
  display:grid;
  grid-template-columns:1fr 360px;
  gap:100px;
  align-items:center;
  min-height:calc(100svh - 90px);
}
.auth-context {
  font-size:12px;
  color:var(--accent);
  margin:0 0 26px;
}
.auth-intro h2 {
  font-size:clamp(32px,3.8vw,47px);
  line-height:1.45;
  font-weight:500;
  letter-spacing:-.03em;
  margin:0 0 24px;
}
.auth-intro>p:not(.auth-context) {
  font-size:14px;
  line-height:1.9;
  color:var(--muted);
}
.auth-intro .auth-local {
  margin-top:64px;
  font-size:12px!important;
}
.auth-form h1 {
  font-size:27px;
  font-weight:550;
  letter-spacing:-.025em;
  line-height:1.4;
  margin:0 0 10px;
}
.auth-description {
  font-size:13px;
  color:var(--muted);
  margin:0 0 32px;
}
.auth-form form {
  display:flex;
  flex-direction:column;
  gap:22px;
}
.auth-form label {
  display:flex;
  flex-direction:column;
  gap:9px;
  font-size:13px;
  font-weight:500;
}
.auth-form input {
  width:100%;
  min-width:0;
  min-height:48px;
  padding:11px 13px;
  background:var(--panel);
  color:var(--text);
  border:1px solid var(--line-strong);
  border-radius:var(--radius);
}
.password-field {
  position:relative;
  display:flex;
  align-items:center;
}
.password-field input {
  padding-right:66px;
}
.password-toggle {
  position:absolute;
  right:3px;
  min-width:54px;
  min-height:44px;
  border:0;
  background:transparent;
  color:var(--muted);
  font-size:12px;
}
.password-toggle:hover {
  color:var(--text);
}
.field-help {
  font-size:12px;
  color:var(--muted);
  margin:-14px 0 0;
}
.auth-error {
  font-size:13px;
  color:var(--danger);
  line-height:1.7;
  margin:0;
}
.auth-submit {
  width:100%;
  background:var(--accent);
  color:var(--accent-ink);
  border-color:var(--accent);
  font-weight:600;
  margin-top:4px;
}
.auth-submit:hover {
  background:var(--accent-hover);
}
.auth-alternate {
  font-size:13px;
  text-align:center;
  color:var(--muted);
  margin:26px 0 0;
}
.auth-alternate a {
  display:inline-flex;
  align-items:center;
  min-height:44px;
  margin-left:9px;
  color:var(--accent);
  text-underline-offset:4px;
}
.auth-storage {
  font-size:12px;
  color:var(--muted);
  text-align:center;
  margin:24px 0 0;
}
@media(max-width:800px) {
  .auth-layout {
    max-width:460px;
    grid-template-columns:1fr;
    gap:0;
    padding:36px 28px 60px;
    min-height:auto;
  }
  .auth-intro {
    display:none;
  }
  .auth-header {
    padding:20px 28px;
    min-height:80px;
  }
  .auth-form h1 {
    font-size:26px;
  }
}
@media(max-width:360px) {
  .auth-layout {
    padding-inline:20px;
  }
  .auth-header {
    padding-inline:20px;
  }
}
</style>
