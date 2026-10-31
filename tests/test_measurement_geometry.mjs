import {test} from 'node:test';import assert from 'node:assert/strict';
import {nearestMeasurementPoint,regionBetween} from '../web/src/measurement-geometry.js';
test('el ajuste respeta el radio y elige el extremo más cercano',()=>{const points=[{point:[40,80],source:'vector'},{point:[42,80],source:'image'}];assert.deepEqual(nearestMeasurementPoint([40.4,80.2],points,1),points[0]);assert.equal(nearestMeasurementPoint([50,80],points,1),null);});
test('la ambigüedad entre extremos distintos no fuerza una elección',()=>{assert.equal(nearestMeasurementPoint([41,80],[{point:[40,80]},{point:[42,80]}],3),null);assert.equal(nearestMeasurementPoint([NaN,80],[],3),null);});
test('el radio en puntos puede adaptarse al zoom sin cambiar el vértice',()=>{const target={point:[100,120]};for(const zoom of [1,2,4])assert.deepEqual(nearestMeasurementPoint([100+2/zoom,120],[target],8/zoom),target);});
test('una región arrastrada hacia atrás conserva sus límites',()=>assert.deepEqual(regionBetween([200,250],[40,80]),[40,80,160,170]));
import {nearestMeasurementGeometry,closeMeasurementPath} from '../web/src/measurement-geometry.js';
test('proyecta sobre un trazado y conserva la prioridad de sus vértices',()=>{
 const paths=[{id:'curve',curved:true,points:[[0,0],[10,0],[20,10]]}];
 const hit=nearestMeasurementGeometry([5,1],[],paths,2);assert.deepEqual(hit.point,[5,0]);assert.equal(hit.source,'curve_approximation');
 const vertex={point:[5,2],source:'vector'};assert.equal(nearestMeasurementGeometry([5,1],[vertex],paths,2),vertex);
 assert.equal(nearestMeasurementGeometry([5,5],[],paths,2),null);
});
test('los trazados equidistantes no fuerzan un ajuste y cerrar no duplica extremos',()=>{
 assert.equal(nearestMeasurementGeometry([5,0],[],[{points:[[0,1],[10,1]]},{points:[[0,-1],[10,-1]]}],3),null);
 const original=[[0,0],[10,0],[10,10]],closed=closeMeasurementPath(original,true);assert.equal(closed.length,4);assert.deepEqual(closed[0],closed.at(-1));assert.equal(original.length,3);
 assert.deepEqual(closeMeasurementPath(closed,false),original);assert.deepEqual(closeMeasurementPath(closed,true),closed);
});
