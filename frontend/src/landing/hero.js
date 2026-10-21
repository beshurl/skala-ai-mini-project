export function mountHero(root){

      const controller = new AbortController();
      const on = (target, type, fn, options={}) => target.addEventListener(type, fn, {...options, signal: controller.signal});
      let frame = 0;
      const stage = root.querySelector('#story-scroll');
      const refs = Object.fromEntries(['room','world-dim','fog','spotlight','detective-glow','detective','crime-props','evidence','story-one','story-two','evidence-label','gallery-shadow','gallery-shell','gallery-controls','gallery-note','doors','door-left','door-right','door-seam','door-arc','title-entry','corner-meta','volume-label','scroll-prompt','phase-number','phase-value','scroll-progress','cards-track','gallery-page','clue-dialog','dialog-index','dialog-title','dialog-description','dialog-image'].map(k => [k, root.querySelector('#'+k)]));
      const LIMIT = 4000;
      const clamp = (v,a=0,b=1)=>Math.max(a,Math.min(b,v));
      const norm = (v,a,b)=>clamp((v-a)/(b-a));
      const ease = x=>x*x*(3-2*x);
      const fi = (p,a,b)=>ease(norm(p,a,b));
      const windowFade = (p,appearA,appearB,leaveA,leaveB)=>fi(p,appearA,appearB)*(1-fi(p,leaveA,leaveB));
      const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
      let targetScroll = 0, displayedScroll=0;
      let mx=0,my=0,tx=0,ty=0;
      let rafRunning = false;
      let sceneActive = true;
      const clues = [
        {title:'증거의 원문',kind:'SOURCE / 01',img:'/assets/landing/hero-715ea986f352d281.webp',preview:'판단에 쓰인 기록을 직접 확인하세요.',description:'결과에 인용된 공개 증거의 원문을 열어, 기록된 사실과 분석의 설명을 직접 대조할 수 있습니다. 요약만으로 판단하지 않고 근거가 되는 문장까지 확인하세요.'},
        {title:'시간의 순서',kind:'TIME / 02',img:'/assets/landing/hero-ed9e0ccd5edefe5d.webp',preview:'같은 시각이 같은 사실을 뜻할까요?',description:'시간의 겹침만으로 인물이나 행위를 확정하지 않습니다. 기록된 시각과 간격, 신원 확인에 필요한 조건을 함께 살피고, 확인되지 않은 부분은 추가 정보가 필요한 상태로 남깁니다.'},
        {title:'진술의 관계',kind:'STATEMENT / 03',img:'/assets/landing/hero-a23e2ffde31d2b4d.webp',preview:'일치·모순·추가확인필요를 구분합니다.',description:'현재 공개된 증거를 기준으로 주장과 기록의 관계를 검토합니다. 서로 어긋나는 내용과 판단할 수 없는 내용을 구분하며, 관계 라벨로 진술자의 의도나 고의적 거짓말을 단정하지 않습니다.'},
        {title:'판단의 근거',kind:'CITATION / 04',img:'/assets/landing/hero-472e7fe42072025e.webp',preview:'설명과 인용을 함께 확인하세요.',description:'어떤 기록이 결과를 뒷받침하는지 인용과 설명을 함께 확인합니다. 결과에서 원문으로 돌아가 공개된 근거의 범위를 대조하고, 설명에 필요한 정보가 빠져 있는지도 살펴보세요.'},
        {title:'새 증거의 영향',kind:'COMPARE / 05',img:'/assets/landing/hero-d76fa045d7427b9b.webp',preview:'공개 전후의 결과를 나란히 비교하세요.',description:'새 자료를 공개한 뒤 다시 분석하면 이전 결과와 현재 결과를 비교할 수 있습니다. 무엇이 바뀌었고 무엇이 유지됐는지, 각 시점의 공개 증거와 판단의 근거를 함께 확인하세요.'}
      ];
      const track = refs['cards-track'];
      const gap = 17;
      let step=0, position=clues.length, moving=false, enabled=false;
      const cardHtml = (item, i)=>`<button class="clue-card" type="button" data-clue="${i}" aria-label="${item.title} 검토 방식 보기"><img src="${item.img}" alt="" loading="lazy"/><span class="card-index">REVIEW &nbsp; / &nbsp; 0${i+1}</span><div class="card-content"><span class="tag">${item.kind}</span><h3>${item.title}</h3><p>${item.preview}</p></div></button>`;
      track.innerHTML = Array.from({length:3},()=>clues.map(cardHtml).join('')).join('');
      const cards = Array.from(track.querySelectorAll('.clue-card'));
      function measureCards(){step=(cards[0]?.getBoundingClientRect().width||300)+gap; setTrack(false);}
      function setTrack(animate=true){track.style.transition=animate&&!reduced.matches?'transform 640ms cubic-bezier(.22,1,.36,1)':'none';track.style.transform=`translate3d(${-position*step}px,0,0)`;const width=root.querySelector('.cards-window').getBoundingClientRect().width;cards.forEach((c,i)=>{const visible=i>=position && i<position+Math.max(1,Math.floor((width+gap)/step));c.tabIndex=visible?0:-1;c.setAttribute('aria-hidden',visible?'false':'true');});refs['gallery-page'].textContent=String(((position%clues.length)+clues.length)%clues.length+1).padStart(2,'0');}
      function moveCard(dir){if(!enabled||moving)return;moving=true;position+=dir;setTrack(true);if(reduced.matches){normalise();}}
      function normalise(){const n=clues.length;if(position<n){position+=n;setTrack(false);}else if(position>=2*n){position-=n;setTrack(false);}moving=false;}
      on(track,'transitionend',e=>{if(e.propertyName==='transform')normalise();});
      on(root.querySelector('#gallery-prev'),'click',()=>moveCard(-1));
      on(root.querySelector('#gallery-next'),'click',()=>moveCard(1));
      on(track,'click',e=>{const el=e.target.closest('[data-clue]');if(!el||!enabled)return; const idx=Number(el.dataset.clue); const item=clues[idx]; refs['dialog-index'].textContent=`REVIEW METHOD / 0${idx+1}`;refs['dialog-title'].textContent=item.title;refs['dialog-description'].textContent=item.description;refs['dialog-image'].src=item.img;refs['dialog-image'].alt=`${item.title} 소개용 일러스트`;refs['clue-dialog'].showModal();});
      on(root.querySelector('#dialog-close'),'click',()=>refs['clue-dialog'].close());
      on(refs['clue-dialog'],'close',()=>schedule());
      on(refs['clue-dialog'],'click',e=>{if(e.target===refs['clue-dialog'])refs['clue-dialog'].close();});
      on(document,'keydown',e=>{if(refs['clue-dialog'].open)return;if((e.key==='ArrowRight'||e.key==='ArrowLeft')&&enabled){if(document.activeElement?.tagName==='INPUT')return;moveCard(e.key==='ArrowRight'?1:-1);}});
      function jumpTo(p){const stageY=stage.getBoundingClientRect().top+window.scrollY;window.scrollTo({top:stageY+clamp(p,0,LIMIT),behavior:reduced.matches?'instant':'smooth'});}
      root.querySelectorAll('[data-jump]').forEach(el=>on(el,'click',()=>jumpTo(Number(el.dataset.jump))));
      on(root.querySelector('#return-files'),'click',()=>jumpTo(3800));
      on(root.querySelector('#brand-link'),'click',e=>{e.preventDefault();jumpTo(0);});
      function setOpacity(el,a){el.style.opacity=String(clamp(a));el.inert=a<.05;el.setAttribute('aria-hidden',a<.05||(el.tagName==='IMG'&&el.getAttribute('alt')==='')?'true':'false');}
      function translateText(el,x,y,scale=1){el.style.transform=`translate3d(${x}px,${y}px,0) scale(${scale})`;}
      function render(p){
        const door=fi(p,150,1200), entryExit=fi(p,150,670), roomEnter=fi(p,380,1600);
        const phase1=windowFade(p,550,850,1230,1510);
        const phase2=windowFade(p,1280,1570,2120,2400);
        const detectiveIn=fi(p,1040,1630), detectiveOut=1-fi(p,2650,3140);
        const boardIn=fi(p,2130,2620), boardOut=1-fi(p,2900,3300);
        const galleryIn=fi(p,2980,3520), ctrlIn=fi(p,3430,3740);
        const layerDepth=1.00+roomEnter*.09+fi(p,1800,3500)*.20;
        const reducedMotion=reduced.matches;
        const pointerX=reducedMotion?0:mx, pointerY=reducedMotion?0:my;
        refs.room.style.transform=`translate3d(${pointerX*7-roomEnter*10}px,${pointerY*5-roomEnter*8}px,0) scale(${layerDepth})`;
        refs.room.style.filter=`brightness(${.76-fi(p,2300,3400)*.25}) saturate(${.94+fi(p,1300,3000)*.08})`;
        setOpacity(refs['world-dim'],1-fi(p,480,1100)*.40+fi(p,2800,3390)*.44);
        setOpacity(refs.spotlight,fi(p,350,1350)*(.75-fi(p,2700,3330)*.62));
        setOpacity(refs.fog,.08+fi(p,450,1700)*.40+fi(p,2850,3610)*.10);
        refs.fog.style.transform=`translate3d(${pointerX*-12}px,${pointerY*7+fi(p,900,2900)*-65}px,0) scale(${1+fi(p,900,2900)*.16})`;
        const pivot=reducedMotion?0:83*door;
        refs['door-left'].style.transform=`translate3d(${-door*9}vw,0,0) rotateY(${-pivot}deg)`;
        refs['door-right'].style.transform=`translate3d(${door*9}vw,0,0) rotateY(${pivot}deg)`;
        setOpacity(refs.doors,1-fi(p,960,1280));
        setOpacity(refs['door-seam'],1-fi(p,180,500));
        setOpacity(refs['door-arc'],1-fi(p,180,560));
        setOpacity(refs['title-entry'],1-entryExit);
        refs['title-entry'].style.transform=`translate3d(-50%,calc(-50% - ${entryExit*95}px),0) scale(${1-entryExit*.08})`;
        setOpacity(refs['scroll-prompt'],1-fi(p,60,350));
        setOpacity(refs['corner-meta'],1-fi(p,550,1100));
        setOpacity(refs['volume-label'],1-fi(p,550,1100));
        setOpacity(refs['story-one'],phase1);
        translateText(refs['story-one'],0,45*(1-fi(p,550,850))-110*fi(p,1230,1510));
        refs['story-one'].style.pointerEvents=phase1>.6?'auto':'none';
        setOpacity(refs['story-two'],phase2);
        translateText(refs['story-two'],0,45*(1-fi(p,1280,1570))-100*fi(p,2120,2400));
        refs['story-two'].style.pointerEvents=phase2>.6?'auto':'none';
        setOpacity(refs['detective-glow'],detectiveIn*detectiveOut);
        setOpacity(refs.detective,detectiveIn*detectiveOut*(window.innerWidth<601?(1-fi(p,2050,2450)):1));
        refs.detective.style.transform=`translate3d(${(1-detectiveIn)*135+pointerX*-10+fi(p,2190,2620)*156}px,${(1-detectiveIn)*100+pointerY*9+fi(p,2100,2860)*24}px,0) scale(${.83+detectiveIn*.17+fi(p,1700,3000)*.08})`;
        setOpacity(refs['crime-props'],windowFade(p,1070,1540,2600,3060)*.76);
        refs['crime-props'].style.transform=`translate3d(${pointerX*12}px,${90*(1-fi(p,1070,1540))}px,0) scale(${1.04+fi(p,1500,3000)*.14})`;
        setOpacity(refs.evidence,boardIn*boardOut);
        refs.evidence.style.transform=`translate3d(${(1-boardIn)*-145}px,${(1-boardIn)*75}px,0) rotate(${-9*(1-boardIn)}deg) scale(${.82+.18*boardIn+fi(p,2700,3150)*.09})`;
        setOpacity(refs['evidence-label'],windowFade(p,2300,2570,2930,3310));
        translateText(refs['evidence-label'],0,30*(1-fi(p,2300,2570)));
        setOpacity(refs['gallery-shadow'],galleryIn*.95);
        setOpacity(refs['gallery-shell'],galleryIn);
        refs['gallery-shell'].style.transform=`translate3d(${Math.pow(1-galleryIn,1.55)*window.innerWidth*2.25}px,${(1-galleryIn)*45}px,0)`;
        const controlOpacity=galleryIn*ctrlIn;
        setOpacity(refs['gallery-controls'],controlOpacity);
        refs['gallery-controls'].style.pointerEvents=controlOpacity>.97?'auto':'none';
        enabled=galleryIn>.98 && !refs['clue-dialog'].open;
        refs['gallery-shell'].style.pointerEvents=enabled?'auto':'none';
        setOpacity(refs['gallery-note'],galleryIn*ctrlIn);
        const segment=p<540?'00':p<1370?'01':p<2240?'02':p<3210?'03':'04';
        refs['phase-value'].textContent=segment;
        refs['scroll-progress'].style.transform=`scaleX(${clamp(p/LIMIT)})`;
        if(reducedMotion){
          ['room','fog','detective','crime-props','evidence','story-one','story-two','evidence-label','gallery-shell'].forEach(id=>refs[id].style.transform='none');
          refs['title-entry'].style.transform='translate(-50%,-50%)';
          refs['door-left'].style.transform='none';refs['door-right'].style.transform='none';setOpacity(refs.doors,1-fi(p,150,550));
        }
      }
      function tick(){
        const rect=stage.getBoundingClientRect();
        const inRange=rect.top < window.innerHeight && rect.bottom > 0;
        if(inRange){
          targetScroll=clamp(-rect.top,0,LIMIT);
          if(reduced.matches){displayedScroll=targetScroll;mx=0;my=0;}
          else {displayedScroll+=(targetScroll-displayedScroll)*.18;mx+=(tx-mx)*.09;my+=(ty-my)*.09;}
          render(displayedScroll);
          sceneActive=true;
        } else if(sceneActive){render(rect.top>0?0:LIMIT);sceneActive=false;}
        rafRunning=false;
        if(Math.abs(targetScroll-displayedScroll)>.2||Math.abs(tx-mx)>.002||Math.abs(ty-my)>.002)schedule();
      }
      on(window,'pointermove',e=>{if(reduced.matches)return;schedule();tx=clamp((e.clientX/window.innerWidth-.5)*2,-1,1);ty=clamp((e.clientY/window.innerHeight-.5)*2,-1,1);},{passive:true});
      on(window,'pointerleave',()=>{tx=0;ty=0;schedule();});
      on(window,'resize',()=>{measureCards();schedule();},{passive:true});
      on(window,'scroll',schedule,{passive:true});
      on(reduced,'change',()=>{measureCards();schedule();});
      function schedule(){if(!rafRunning){rafRunning=true;frame=requestAnimationFrame(tick);}}
      measureCards();
      const initial=stage.getBoundingClientRect(); displayedScroll=targetScroll=clamp(-initial.top,0,LIMIT);
      render(displayedScroll);
      schedule();
      return()=>{controller.abort();cancelAnimationFrame(frame);if(refs['clue-dialog'].open)refs['clue-dialog'].close();};

}
