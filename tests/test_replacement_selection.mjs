import {test} from 'node:test';
import assert from 'node:assert/strict';
import {replacementSelection, selectCompatibleBatch} from '../web/src/replacement-selection.js';

const match=(i, page=0)=>({id:`m${i}`,editable:true,page,start:0,end:2,parts:[{id:`r${i}`,start:0,end:2}]});
test('compatible selection respects both occurrence and run limits',()=>{
  const matches=Array.from({length:150},(_,i)=>match(i));
  const chosen=selectCompatibleBatch(matches);
  assert.equal(chosen.length,100);
  assert.deepEqual(replacementSelection(matches,chosen),{count:100,runs:100,valid:true});
  assert.equal(replacementSelection(matches,matches.map(m=>m.id)).valid,false);
});
test('split matches count all touched styles, excluding unrelated context',()=>{
  const matches=Array.from({length:51},(_,i)=>({...match(i),parts:[{id:`a${i}`,start:0,end:1},{id:`b${i}`,start:1,end:2},{id:`c${i}`,start:2,end:3}]}));
  assert.equal(selectCompatibleBatch(matches).length,50);
  assert.equal(replacementSelection(matches,matches.map(m=>m.id)).runs,102);
});
test('repeated hits in a run count it once and page IDs remain distinct',()=>{
  const a=match(0),b={...match(1),parts:a.parts},c={...match(2,1),parts:a.parts};
  assert.equal(replacementSelection([a,b,c],['m0','m1','m2']).runs,2);
});
test('readonly matches are excluded and later small matches can fit',()=>{
  const matches=Array.from({length:99},(_,i)=>match(i));
  matches.push({...match(99),editable:false});
  matches.push({...match(100),parts:[{id:'x',start:0,end:1},{id:'y',start:1,end:2}]});
  matches.push(match(101));
  assert.equal(selectCompatibleBatch(matches).at(-1),'m101');
});
