export function nearestMeasurementPoint(point,targets,radius){
 if(!Array.isArray(point)||point.length!==2||!point.every(Number.isFinite)||!Number.isFinite(radius)||radius<=0)return null;
 let best=null,distance=radius*radius,tied=false;
 for(const target of targets){const p=target.point;if(!Array.isArray(p)||p.length!==2||!p.every(Number.isFinite))continue;const d=(p[0]-point[0])**2+(p[1]-point[1])**2;if(d<distance-1e-8){best=target;distance=d;tied=false;}else if(best&&Math.abs(d-distance)<1e-8&&(p[0]!==best.point[0]||p[1]!==best.point[1]))tied=true;}
 return tied?null:best;
}
export function regionBetween(a,b){return [Math.min(a[0],b[0]),Math.min(a[1],b[1]),Math.abs(a[0]-b[0]),Math.abs(a[1]-b[1])].map(v=>Math.round(v*1000)/1000);}
