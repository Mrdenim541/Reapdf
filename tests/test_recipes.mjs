import {test} from 'node:test';
import assert from 'node:assert/strict';
import {newRecipe,moveStep,defaultStep,presetRecipes,parseRecipeFile,loadRecipes,saveRecipe,recipeStorageKey} from '../web/src/recipes.js';
const memory=()=>{const data=new Map();return {getItem:k=>data.get(k)??null,setItem:(k,v)=>data.set(k,v)};};
test('moving recipe steps preserves options and bounds',()=>{const r=newRecipe('Prueba',['watermark','numbering','optimize']);r.steps[0].text='BORRADOR';const next=moveStep(r,0,1);assert.equal(next.steps[1].text,'BORRADOR');assert.equal(r.steps[0].text,'BORRADOR');assert.equal(moveStep(r,0,-1),r);assert.equal(moveStep(r,2,1),r);});
test('presets have valid terminal order and never contain credentials',()=>{for(const r of presetRecipes){assert.ok(r.steps.length);const encoded=JSON.stringify(r);assert.ok(!encoded.includes('password'));const end=r.steps.findIndex(s=>['text','protect'].includes(s.type));assert.ok(end===-1||end===r.steps.length-1);}assert.deepEqual(defaultStep('protect'),{type:'protect',allow_copy:true,allow_print:true});});
test('local recipe library replaces by name, limits count and tolerates bad storage',()=>{const storage=memory();let values=[];for(let i=0;i<25;i++)values=saveRecipe(storage,newRecipe('Receta '+i),values);assert.equal(values.length,20);values=saveRecipe(storage,newRecipe('Receta 24',['text']),values);assert.equal(values.length,20);assert.equal(loadRecipes(storage)[0].steps[0].type,'text');storage.setItem(recipeStorageKey,'not json');assert.deepEqual(loadRecipes(storage),[]);storage.setItem(recipeStorageKey,'{}');assert.deepEqual(loadRecipes(storage),[]);});
test('recipe file parsing rejects invalid formats and excessive UTF-8 bytes',()=>{const r=newRecipe();assert.deepEqual(parseRecipeFile(JSON.stringify(r)),r);for(const value of ['{}','[]','bad',JSON.stringify({...r,version:2}),'é'.repeat(33000)])assert.throws(()=>parseRecipeFile(value));});

test('Word en recetas tiene opciones explícitas y mantiene formato declarativo sin secretos',()=>{
 const step=defaultStep('docx');assert.equal(step.type,'docx');assert.equal(step.keep_lines,true);
 for(const option of ['keep_lines','include_images','include_tables','include_links'])assert.equal(typeof step[option],'boolean');
 assert.ok(!JSON.stringify(step).includes('password'));
});
