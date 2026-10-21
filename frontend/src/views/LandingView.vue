<script setup>
import {ref,onMounted,onBeforeUnmount} from 'vue';
import SiteHeader from '../components/SiteHeader.vue';
import {mountHero} from '../landing/hero';
const root=ref(null);let cleanup;
onMounted(()=>{cleanup=mountHero(root.value);});
onBeforeUnmount(()=>cleanup?.());
</script>
<template><div ref="root" class="recase-landing">
  <a class="skip" href="#files">체험 안내로 건너뛰기</a>
  <div class="scroll-progress" id="scroll-progress" aria-hidden="true"></div>
  <main>
    <div class="story-scroll" id="story-scroll">
      <section class="scene" id="hero" aria-label="RE:CASE 증거 기반 사건 검토 소개">
        <img src="/assets/landing/hero-db207630c5b009e3.webp" id="room" class="scene-background" alt="" />
        <div class="ambient"></div>
        <div class="intro-spotlight" id="spotlight"></div>
        <div class="world-dim" id="world-dim"></div>
        <img src="/assets/landing/hero-934b6588ac70bfd6.webp" class="low-haze" id="fog" alt="" />
        <div class="detective-glow" id="detective-glow"></div>
        <img src="/assets/landing/hero-9c5acf38f5c68a30.webp" class="detective-image" id="detective" alt="기록을 검토하는 인물을 표현한 소개용 일러스트" />
        <img src="/assets/landing/hero-f4e6a9cc579e0c11.webp" class="crime-strip" id="crime-props" alt="" />
        <img src="/assets/landing/hero-938fdbfd9df700e7.webp" class="evidence-image" id="evidence" alt="여러 기록 사이의 관계를 표현한 소개용 증거 보드" />
        <div class="scanlines"></div><div class="grain"></div>
        <div class="scene-heading" id="story-one">
          <div class="chapter-rule"></div><div class="eyebrow">01 / READ THE RECORDS</div>
          <h2>기록을 열고,<br/><em>맥락을</em> 읽다.</h2>
          <p>진술과 시간, 남겨진 증거를 함께 살펴보세요. RE:CASE는 현재 공개된 자료를 바탕으로 주장과 증거의 관계를 검토합니다.</p>
          <button class="tiny-pill" data-jump="1800">판단의 근거 살펴보기 ↗</button>
        </div>
        <div class="scene-heading" id="story-two">
          <div class="chapter-rule"></div><div class="eyebrow">02 / REVIEW THE EVIDENCE</div>
          <h2>판단은<br/><em>근거에서</em><br/>시작됩니다.</h2>
          <p>일치하는 기록과 서로 어긋나는 진술을 구분합니다. 확인할 수 없는 부분은 판단을 보류하고, 결과에 인용된 원문을 함께 보여줍니다.</p>
          <button class="tiny-pill" data-jump="2640">증거의 연결 살펴보기 ↗</button>
        </div>
        <div class="evidence-label" id="evidence-label">
          <div class="eyebrow">03 / COMPARE THE CHANGE</div>
          <h2>새로운 증거,<br/>판단을 다시.</h2>
          <div class="sub">새 자료가 공개되면 다시 검토합니다. 바뀐 판단과 유지된 판단을 이전 결과의 근거와 나란히 비교하세요.</div>
        </div>
        <div class="gallery-shadow" id="gallery-shadow"></div>
        <section class="gallery-shell" id="gallery-shell" aria-label="RE:CASE의 검토 방식 살펴보기">
          <div class="gallery-title"><div>
            <div class="eyebrow">04 / INSIDE RE:CASE</div>
            <h2>판단의 <em>근거들.</em></h2>
          </div><p class="gallery-right-note">카드를 눌러 검토 방식을 살펴보세요.<br/>READ · REVIEW · COMPARE</p></div>
          <div class="cards-window"><div class="cards-track" id="cards-track"></div></div>
          <div class="gallery-controls" id="gallery-controls">
            <button type="button" id="gallery-prev" aria-label="이전 검토 방식">←</button>
            <button type="button" id="gallery-next" aria-label="다음 검토 방식">→</button>
            <div class="counter"><span id="gallery-page">01</span> / 05</div>
          </div>
        </section>
        <div class="lower-note" id="gallery-note">공개된 증거만으로 검토합니다 · 화면 이미지는 소개용 연출입니다</div>
        <div class="doors-layer" id="doors">
          <div class="door left" id="door-left"><img src="/assets/landing/hero-7b7bdc914e97a68e.webp" alt="" /></div>
          <div class="door right" id="door-right"><img src="/assets/landing/hero-b2e0125dbe8e1e10.webp" alt="" /></div>
        </div>
        <div class="door-seam" id="door-seam"></div>
        <div class="door-arc" id="door-arc"></div>
        <div class="title-entry" id="title-entry">
          <div class="entry-top eyebrow center">증거 기반 AI</div>
          <h1 aria-label="RE:CASE"><span>RE:</span><span class="case-word">CASE</span></h1>
          <p class="opening-subtitle">미제사건 재수사 지원<br/><span class="purpose-detail">기록과 증거를 대조해 단서를 검토합니다.</span></p><div class="opening-actions"><a href="/cases" class="rc-button rc-button--primary">사건 기록 열기 <span aria-hidden="true">↗</span></a><button type="button" data-jump="1000" class="opening-explore">검토 방식 살펴보기 <span aria-hidden="true">↓</span></button></div><p class="opening-note">현재 체험은 합성 사건 2종을 사용합니다.</p>
        </div>
        <div class="corner-meta" id="corner-meta">RE:CASE&nbsp; · &nbsp;공개 증거 기반 사건 검토</div>
        <div class="volume-label" id="volume-label">READ THE RECORDS. REVIEW THE EVIDENCE.</div>
        <div class="scroll-prompt" id="scroll-prompt"><span>스크롤해서 기록 열기</span><span class="scroll-line"></span></div>
        <div class="phase-number" id="phase-number"><strong id="phase-value">00</strong><div class="tick"></div><small>04</small></div>
        <SiteHeader hero />
      </section>
    </div>
    <section id="files" class="afterword" aria-label="RE:CASE 합성 사건 체험 안내">
      <div>
        <p class="eyebrow">YOUR NEXT CASE / RE:CASE</p>
        <h2>사건 기록과 증거를<br/>다시 검토합니다.</h2>
        <p>RE:CASE는 증거를 바탕으로 미제사건의 재수사 검토를 지원하는 것을 목표로 합니다.<br/>현재 체험에서는 합성 사건의 진술과 기록, 새 증거 전후의 분석을 비교할 수 있습니다.</p>
      </div>
      <div class="afterword-actions"><a class="experience-link" href="/cases">사건 기록 열기 &nbsp; ↗</a><button id="return-files" class="review-again" type="button">검토 방식 다시 보기</button><p class="experience-note">로컬 합성 사건 검토실로 이동합니다.</p></div>
    </section>
  </main>
  <footer class="site-footer"><span>© RE:CASE · AI COLD CASE REVIEW</span><span>합성 사건 체험 · 실제 사건의 사실·유죄 판단을 대신하지 않습니다</span></footer>
  <dialog id="clue-dialog" class="case-dialog" aria-label="검토 방식 상세 안내">
    <button type="button" class="dialog-close" id="dialog-close" aria-label="검토 방식 안내 닫기">×</button>
    <div class="dialog-grid">
      <img id="dialog-image" src="/assets/landing/hero-715ea986f352d281.webp" alt="" />
      <div class="dialog-content">
        <div class="eyebrow" id="dialog-index">REVIEW METHOD / 01</div>
        <h2 id="dialog-title">증거의 원문</h2>
        <p id="dialog-description"></p>
        <span class="confidential">RE:CASE · 현재 공개된 자료를 기준으로 검토합니다</span>
      </div>
    </div>
  </dialog>
  </div></template>
<style src="../landing/landing.css"></style>
