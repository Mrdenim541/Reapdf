import test from 'node:test';import assert from 'node:assert/strict';import {editMixedText} from '../web/src/mixed-text-edit.js';
const runs=()=>[{id:'a',font:'Bold',text:'HELLO '},{id:'b',font:'Italic',text:'TEXT'}];
test('insert at style boundary keeps suffix style, ids and metadata',()=>{const original=runs(),out=editMixedText(original,'HELLO HELLO TEXT');assert.deepEqual(out.map(r=>r.text),['HELLO HELLO ','TEXT']);assert.equal(out[1].font,'Italic');assert.deepEqual(original,runs());});
test('typing inside the last run keeps its style',()=>assert.deepEqual(editMixedText(runs(),'HELLO TEST').map(r=>r.text),['HELLO ','TEST']));
test('deleting across runs retains surviving styles',()=>assert.deepEqual(editMixedText(runs(),'HEXT').map(r=>r.text),['HE','XT']));
test('delete all then type retains a usable first style',()=>{const empty=editMixedText(runs(),'');assert.deepEqual(editMixedText(empty,'New').map(r=>r.text),['New','']);});
test('whole replacement and start insertion have defined first style',()=>{assert.deepEqual(editMixedText(runs(),'new').map(r=>r.text),['new','']);assert.deepEqual(editMixedText(runs(),'XHELLO TEXT').map(r=>r.text),['XHELLO ','TEXT']);});
test('code points are preserved across emoji edits and line breaks',()=>{const r=[{id:'a',text:'A😀'},{id:'b',text:'βZ'}];assert.deepEqual(editMixedText(r,'A😁βZ').map(r=>r.text),['A😁','βZ']);assert.deepEqual(editMixedText(r,'A😀\nβZ').map(r=>r.text),['A😀\n','βZ']);});
test('unchanged text and empty first run do not shift style',()=>{const r=[{id:'empty',text:''},...runs()];assert.deepEqual(editMixedText(r,'HELLO TEXT'),r);});
