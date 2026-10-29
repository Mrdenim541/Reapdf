import test from 'node:test';
import assert from 'node:assert/strict';
import {imageDimensions} from '../web/src/image-data.js';

test('Lee PNG antes de decodificar, incluyendo dimensiones excesivas',()=>{
 const bytes=new Uint8Array(33);bytes.set([137,80,78,71,13,10,26,10]);const v=new DataView(bytes.buffer);
 v.setUint32(8,13);v.setUint32(12,0x49484452);v.setUint32(16,100000);v.setUint32(20,100000);
 assert.deepEqual(imageDimensions(bytes),{width:100000,height:100000,mime:'image/png'});
});
test('Lee JPEG progresivo después de metadatos sin decodificar',()=>{
 const b=Uint8Array.from([255,216,255,224,0,4,0,0,255,194,0,8,8,0,40,0,80,3]);
 assert.deepEqual(imageDimensions(b),{width:80,height:40,mime:'image/jpeg'});
});
for(const bytes of [[],[255,216,255],[255,216,255,224,0,0],[255,216,255,194,0,8],[137,80,78,71,13,10,26,10],[71,73,70,56,57,97]]) {
 test(`Rechaza cabecera truncada o no admitida ${bytes.join(',')}`,()=>assert.throws(()=>imageDimensions(Uint8Array.from(bytes))));
}
