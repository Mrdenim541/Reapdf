import test from 'node:test';
import assert from 'node:assert/strict';
import {caretIndex} from '../web/src/inline-caret.js';
const char=(text,index,x,group='one')=>({text,index,group,quad:[[x,0],[x+10,0],[x,20],[x+10,20]]});
test('mouse selects insertion boundary, keeping spaces and UTF16 indexes',()=>{
 const chars=[char('A',0,0),char('B',2,20)];assert.equal(caretIndex('A B',[0,0,30,20],chars,[3,10]),0);assert.equal(caretIndex('A B',[0,0,30,20],chars,[28,10]),3);
 const unicode=[char('😀',0,0),char('B',1,10)];assert.equal(caretIndex('😀B',[0,0,20,20],unicode,[8,10]),2);
});
test('ambiguous and unavailable glyph geometry falls back instead of guessing',()=>{
 assert.equal(caretIndex('AB',[0,0,20,20],[],[2,10]),null);assert.equal(caretIndex('AB',[0,0,20,20],[char('A',0,0),char('B',1,10),char('A',0,0,'two'),char('B',1,10,'two')],[2,10]),null);
});
test('oriented quads support four page rotations',()=>{
 for(const angle of [0,90,180,270]){
  const turn=([x,y])=>{if(angle===90)return [20-y,x];if(angle===180)return [20-x,20-y];if(angle===270)return [y,20-x];return [x,y];};
  const chars=[char('A',0,0),char('B',1,10)].map(c=>({...c,quad:c.quad.map(turn)}));assert.equal(caretIndex('AB',[0,0,20,20],chars,turn([18,10])),2);
 }
});
