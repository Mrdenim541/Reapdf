import test from 'node:test';
import assert from 'node:assert/strict';
import {branchEnd,previousSibling,moveBranch,indentBranch,validateBookmarks} from '../web/src/bookmark-data.js';
const tree=()=>[['A',1],['a',2],['aa',3],['b',2],['B',1],['c',2],['C',1]].map(([title,level])=>({title,level,page:0}));
const titles=items=>items.map(i=>i.title).join(',');
test('subtree bounds and previous siblings respect parents',()=>{
 const t=tree();assert.equal(branchEnd(t,0),4);assert.equal(branchEnd(t,1),3);assert.equal(previousSibling(t,3),1);assert.equal(previousSibling(t,5),-1);
});
test('move root with all descendants and keep selected root',()=>{
 const t=tree(),copy=structuredClone(t),down=moveBranch(t,0,1);
 assert.equal(titles(down.items),'B,c,A,a,aa,b,C');assert.equal(down.index,2);
 const up=moveBranch(down.items,down.index,-1);assert.deepEqual(up.items,t);assert.equal(up.index,0);assert.deepEqual(t,copy);
});
test('move children with whole branch without crossing root',()=>{
 const t=tree(),down=moveBranch(t,1,1);assert.equal(titles(down.items),'A,b,a,aa,B,c,C');assert.equal(down.index,2);
 assert.equal(moveBranch(t,3,1).items,t);assert.equal(moveBranch(t,1,-1).items,t);
});
test('indent adds complete branch under previous sibling',()=>{
 const t=tree(),m=indentBranch(t,4,1);assert.equal(titles(m.items),titles(t));assert.deepEqual(m.items.map(i=>i.level),[1,2,3,2,2,3,1]);assert.equal(m.index,4);assert.equal(validateBookmarks(m.items,1),'');
});
test('outdent moves branch after remaining children of parent',()=>{
 const t=tree(),m=indentBranch(t,1,-1);assert.equal(titles(m.items),'A,b,a,aa,B,c,C');assert.deepEqual(m.items.map(i=>i.level),[1,2,1,2,1,2,1]);assert.equal(m.index,2);assert.equal(validateBookmarks(m.items,1),'');
 assert.deepEqual(t,tree());
});
test('outdent nested branch preserves next uncle and roots',()=>{
 const t=tree(),m=indentBranch(t,2,-1);assert.equal(titles(m.items),titles(t));assert.deepEqual(m.items.map(i=>i.level),[1,2,2,2,1,2,1]);assert.equal(m.index,2);
});
test('first sibling cannot indent and roots cannot outdent',()=>{
 const t=tree();assert.equal(indentBranch(t,0,1).items,t);assert.equal(indentBranch(t,1,1).items,t);assert.equal(indentBranch(t,0,-1).items,t);
});
test('depth limit applies to deepest descendant',()=>{
 const t=Array.from({length:10},(_,i)=>({title:String(i),level:i+1,page:0}));t.splice(1,0,{title:'previous',level:2,page:0});
 assert.equal(indentBranch(t,2,1).items,t);
});
test('index validation includes hierarchy destinations limits and control characters',()=>{
 assert.equal(validateBookmarks([],1),'');assert.equal(validateBookmarks(tree(),1),'');
 for(const patch of [{level:2},{level:0},{level:11},{level:1.5},{title:''},{title:'x\n'},{title:'x'.repeat(301)},{page:1},{page:-1},{page:.5}])assert.ok(validateBookmarks([{title:'A',level:1,page:0,...patch}],1));
 assert.ok(validateBookmarks(Array(2001).fill({title:'A',level:1,page:0}),1));
});
