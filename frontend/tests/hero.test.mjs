import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setMaxListeners} from 'node:events';
import {mountHero} from '../src/landing/hero.js';

// Isolated DOM stand-ins test lifecycle and reduced-motion logic; browser QA is recorded separately.
function environment(reduced){
 class Node extends EventTarget {
  constructor(){super();this.style={};this.attrs={};this.dataset={};this.open=false;this.tagName='DIV';this.top=0;}
  setAttribute(k,v){this.attrs[k]=v;} getAttribute(k){return this.attrs[k]??null;}
  getBoundingClientRect(){return {top:this.top,bottom:this.top+4720,width:300};}
  close(){this.open=false;this.dispatchEvent(new Event('close'));} showModal(){this.open=true;}
 }
 const map=new Map();const get=id=>{if(!map.has(id))map.set(id,new Node());return map.get(id);};
 const cards=Array.from({length:15},()=>new Node());
 get('cards-track').querySelectorAll=()=>cards;
 const jumps=[1000,1800,2640,3800].map(p=>{const n=new Node();n.dataset.jump=String(p);return n;});
 const root={querySelector:s=>get(s.replace(/^[#.]/,'')),querySelectorAll:()=>jumps};
 const window=new Node(),media=new Node(),document=new Node();
 window.innerWidth=390;window.innerHeight=844;window.scrollY=0;window.matchMedia=()=>media;media.matches=reduced;document.activeElement={tagName:'BODY'};
 const frames=new Map();let id=0;
 const previous=Object.fromEntries(['window','document','requestAnimationFrame','cancelAnimationFrame'].map(k=>[k,globalThis[k]]));
 Object.assign(globalThis,{window,document,requestAnimationFrame:fn=>{frames.set(++id,fn);return id;},cancelAnimationFrame:key=>frames.delete(key)});
 return {map,get,cards,window,frames,root,flush(){for(let i=0;i<100&&frames.size;i++){const list=[...frames.values()];frames.clear();list.forEach(fn=>fn());}},restore(){for(const [key,value]of Object.entries(previous)){if(value===undefined)delete globalThis[key];else globalThis[key]=value;}}};
}
test('reduced motion retains scene content without translate/rotate motion; cleanup cancels listeners and frames',()=>{
 setMaxListeners(40);
 const e=environment(true);try{
  const cleanup=mountHero(e.root);e.get('story-scroll').top=-1800;e.window.dispatchEvent(new Event('scroll'));e.flush();
  assert.equal(e.get('story-two').inert,false);assert.equal(e.get('title-entry').inert,true);
  assert.equal(e.get('room').style.transform,'none');assert.equal(e.get('door-left').style.transform,'none');
  assert.equal(e.get('gallery-shell').inert,true);
  assert.equal(e.frames.size,0,'idle reduced-motion scene has no continuous rAF');
  cleanup();e.window.dispatchEvent(new Event('scroll'));assert.equal(e.frames.size,0);
 }finally{e.restore();setMaxListeners(10);}
});
test('normal motion preserves door transforms and gallery has only visible cards in tab order',()=>{
 setMaxListeners(40);
 const e=environment(false);try{
  const cleanup=mountHero(e.root);e.get('story-scroll').top=-1800;e.window.dispatchEvent(new Event('scroll'));e.flush();
  assert.match(e.get('door-left').style.transform,/rotateY/);
  assert.equal(e.cards.filter(c=>c.tabIndex===0).length,1);
  cleanup();assert.equal(e.frames.size,0);
 }finally{e.restore();setMaxListeners(10);}
});
