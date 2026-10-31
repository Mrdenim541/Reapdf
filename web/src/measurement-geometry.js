export function nearestMeasurementPoint(point,targets,radius){
 if(!Array.isArray(point)||point.length!==2||!point.every(Number.isFinite)||!Number.isFinite(radius)||radius<=0)return null;
 let best=null,distance=radius*radius,tied=false;
 for(const target of targets){const p=target.point;if(!Array.isArray(p)||p.length!==2||!p.every(Number.isFinite))continue;const d=(p[0]-point[0])**2+(p[1]-point[1])**2;if(d<distance-1e-8){best=target;distance=d;tied=false;}else if(best&&Math.abs(d-distance)<1e-8&&(p[0]!==best.point[0]||p[1]!==best.point[1]))tied=true;}
 return tied?null:best;
}
export function regionBetween(a,b){return [Math.min(a[0],b[0]),Math.min(a[1],b[1]),Math.abs(a[0]-b[0]),Math.abs(a[1]-b[1])].map(v=>Math.round(v*1000)/1000);}

// Projection onto the reviewed polyline is bounded by the server's reported
// approximation of the original curve. Prefer a nearby exact vertex first.
export function nearestMeasurementGeometry(point,targets,paths,radius){
 const vertex=nearestMeasurementPoint(point,targets,radius);if(vertex)return vertex;
 if(!Array.isArray(point)||!point.every(Number.isFinite)||!Number.isFinite(radius)||radius<=0)return null;
 let best=null,distance=radius*radius,tied=false;
 for(const path of paths){
  for(let i=1;i<path.points.length;i++){
   const a=path.points[i-1],b=path.points[i],dx=b[0]-a[0],dy=b[1]-a[1],length=dx*dx+dy*dy;if(!length)continue;
   const t=Math.max(0,Math.min(1,((point[0]-a[0])*dx+(point[1]-a[1])*dy)/length)),p=[a[0]+t*dx,a[1]+t*dy],d=(p[0]-point[0])**2+(p[1]-point[1])**2;
   if(d<distance-1e-8){best={point:p,source:path.curved?'curve_approximation':'path',path:path.id};distance=d;tied=false;}
   else if(best&&Math.abs(d-distance)<1e-8&&Math.hypot(p[0]-best.point[0],p[1]-best.point[1])>1e-5)tied=true;
  }
 }
 return tied?null:best;
}
export function closeMeasurementPath(points,closed){
 const result=points.map(p=>[...p]);if(result.length>1&&result[0][0]===result.at(-1)[0]&&result[0][1]===result.at(-1)[1])result.pop();
 if(closed&&result.length>=3&&result.length<200)result.push([...result[0]]);return result;
}
