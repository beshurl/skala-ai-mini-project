import test from 'node:test';
import assert from 'node:assert/strict';
import {quoteParts} from '../src/quotes.ts';

test('source offsets preserve astral characters',()=>{
  const text='🔎 원문: 𐐀 A의 기록입니다.';
  const quote='𐐀 A의 기록';
  const result=quoteParts(text,{evidence_id:'E1',quote,start:6,end:13});
  assert.equal(result.before+result.quote+result.after,text);
  assert.equal(result.quote,quote);
});

test('stale or invalid source offsets never create a highlighted quote',()=>{
  const citation={evidence_id:'E1',quote:'원문',start:0,end:2};
  assert.equal(quoteParts('정정',citation),null);
  assert.equal(quoteParts('원문',{...citation,start:-1}),null);
  assert.equal(quoteParts('원문',{...citation,end:999}),null);
});
