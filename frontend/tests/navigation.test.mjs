import {test} from 'node:test';
import assert from 'node:assert/strict';

const listeners = new Map();
const scrolls = [];
let current = new URL('http://localhost/login?next=%2Fcases%2FCASE-old');
globalThis.window = {
  get location(){return current;},
  history:{pushState(_state,_title,path){current=new URL(path,current);}},
  addEventListener(name, callback){listeners.set(name,callback);},
  scrollTo(options){scrolls.push(options);},
};
const {navigate,location,query,safeNext,loginPathFor} = await import('../src/navigation.ts');

test('logout and query-only navigation clear the previous account return path',()=>{
  assert.equal(query.value,'?next=%2Fcases%2FCASE-old');
  navigate('/login');
  assert.equal(location.value,'/login');
  assert.equal(query.value,'');
  navigate('/login?next=%2Fsettings');
  assert.equal(location.value,'/login');
  assert.equal(query.value,'?next=%2Fsettings');
  current=new URL('http://localhost/signup?next=%2Fhistory');
  listeners.get('popstate')();
  assert.equal(location.value,'/signup');
  assert.equal(query.value,'?next=%2Fhistory');
});

test('post-login return paths cannot leave the app or return to an auth loop',()=>{
  for(const path of ['https://evil.example','//evil.example','/\\evil.example','/login','/signup','/cases/../../admin','/%2f%2fevil','/admin?next=https://evil.example',null]) assert.equal(safeNext(path),'/cases');
  for(const path of ['/cases/CASE-123','/admin/logs','/history','/settings']) assert.equal(safeNext(path),path);
});

test('saved analysis survives sign-in while unexpected query parameters are rejected',()=>{
  const target='/cases/CASE-123?job=JOB-456';
  assert.equal(safeNext(target),target);
  assert.equal(new URL(loginPathFor('/cases/CASE-123','?job=JOB-456'),'http://localhost').searchParams.get('next'),target);
  for(const value of [
    '/cases/CASE-123?job=JOB-456&next=https://evil.example',
    '/cases/CASE-123?job=JOB-456&job=JOB-789',
    '/cases/CASE-123?job=https://evil.example',
    '/cases/CASE-123?job=JOB%26next%3Dadmin',
    '/cases/CASE-123?job=JOB-456#admin',
    '/cases/CASE-123?other=JOB-456',
    '/history?job=JOB-456',
  ])assert.equal(safeNext(value),'/cases');
  assert.equal(new URL(loginPathFor('/cases/CASE-123','?job=JOB-456&next=admin'),'http://localhost').searchParams.get('next'),'/cases');
});

test('selecting analyses preserves reading position while opening another case resets it',()=>{
  navigate('/cases/CASE-A');
  scrolls.length=0;
  navigate('/cases/CASE-A?job=JOB-first');
  navigate('/cases/CASE-A?job=JOB-second');
  assert.equal(query.value,'?job=JOB-second');
  assert.equal(scrolls.length,0,'Same-case analysis selection must preserve the reading position');
  navigate('/cases/CASE-B?job=JOB-other');
  assert.equal(location.value,'/cases/CASE-B');
  assert.deepEqual(scrolls,[{top:0,behavior:'instant'}]);
});
