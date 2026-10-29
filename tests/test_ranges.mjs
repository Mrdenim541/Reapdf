import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parsePageRange } from '../web/src/ranges.js';

test('conserva el orden de una selección mixta',()=>assert.deepEqual(parsePageRange(' 3, 1-2, 5 ',5),[2,0,1,4]));
test('acepta una sola página y espacios en el rango',()=>{
 assert.deepEqual(parsePageRange('1',1),[0]);assert.deepEqual(parsePageRange('1 - 3',3),[0,1,2]);
});
for(const value of ['', '0', '2-1', '1-4', '1,,2', '1-2,2', '3,3', 'NaN', '1.5', '1e2','1-',null])
 test(`rechaza selección no válida: ${value}`,()=>assert.throws(()=>parsePageRange(value,3)));
test('rechaza una cantidad de páginas no válida',()=>assert.throws(()=>parsePageRange('1',0)));
