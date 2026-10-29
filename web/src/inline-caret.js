// Reuse glyph geometry already loaded for selection; no additional PDF request.
export function caretIndex(text,box,characters,point){
 if(!Array.isArray(point)||point.length!==2||!point.every(Number.isFinite))return null;
 const [x,y,w,h]=box,groups=new Map();
 for(const c of characters){
  const xs=c.quad.map(p=>p[0]),ys=c.quad.map(p=>p[1]);
  if(Math.min(...xs)<x-.05||Math.max(...xs)>x+w+.05||Math.min(...ys)<y-.05||Math.max(...ys)>y+h+.05)continue;
  if(!groups.has(c.group))groups.set(c.group,[]);groups.get(c.group).push(c);
 }
 const expected=text.replace(/\s/g,''),matches=[...groups.values()].filter(g=>g.map(c=>c.text).join('')===expected);
 if(matches.length!==1)return null;
 let best=null,score=Infinity;
 for(const c of matches[0]){
  const center=c.quad.reduce((a,p)=>[a[0]+p[0]/4,a[1]+p[1]/4],[0,0]),distance=(center[0]-point[0])**2+(center[1]-point[1])**2;
  if(distance<score){score=distance;best=c;}
 }
 if(!best)return null;
 const a=best.quad[0],b=best.quad[1],dx=b[0]-a[0],dy=b[1]-a[1],length=dx*dx+dy*dy;
 if(length<1e-8)return null;
 const after=((point[0]-a[0])*dx+(point[1]-a[1])*dy)/length>.5,index=best.index+Number(after);
 return Array.from(text).slice(0,index).join('').length;
}
