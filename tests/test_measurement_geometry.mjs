import {test} from 'node:test';import assert from 'node:assert/strict';
import {nearestMeasurementPoint,regionBetween} from '../web/src/measurement-geometry.js';
test('el ajuste respeta el radio y elige el extremo más cercano',()=>{const points=[{point:[40,80],source:'vector'},{point:[42,80],source:'image'}];assert.deepEqual(nearestMeasurementPoint([40.4,80.2],points,1),points[0]);assert.equal(nearestMeasurementPoint([50,80],points,1),null);});
test('la ambigüedad entre extremos distintos no fuerza una elección',()=>{assert.equal(nearestMeasurementPoint([41,80],[{point:[40,80]},{point:[42,80]}],3),null);assert.equal(nearestMeasurementPoint([NaN,80],[],3),null);});
test('el radio en puntos puede adaptarse al zoom sin cambiar el vértice',()=>{const target={point:[100,120]};for(const zoom of [1,2,4])assert.deepEqual(nearestMeasurementPoint([100+2/zoom,120],[target],8/zoom),target);});
test('una región arrastrada hacia atrás conserva sus límites',()=>assert.deepEqual(regionBetween([200,250],[40,80]),[40,80,160,170]));
