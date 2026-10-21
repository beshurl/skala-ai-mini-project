import {test} from 'node:test';
import assert from 'node:assert/strict';

const listeners = new Map();
let current = new URL('http://localhost/login?next=%2Fcases%2FCASE-old');
globalThis.window = {
  get location(){return current;},
  history:{pushState(_state,_title,path){current=new URL(path,current);}},
  addEventListener(name, callback){listeners.set(name,callback);},
  scrollTo(){},
};
const {navigate,location,query,safeNext} = await import('../src/navigation.ts');

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
