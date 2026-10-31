"""Isolated finite line/cubic intersections using monotonic root intervals."""
import math


def line_cubic(line,controls):
    (ax,ay),(bx,by)=line;dx=bx-ax;dy=by-ay;length=math.hypot(dx,dy)
    if length<1e-8:return []
    values=[((p[0]-ax)*dy-(p[1]-ay)*dx)/length for p in controls]
    if max(abs(v) for v in values)<1e-8:return [] # Collinear overlap has no isolated snap.
    d=values[0];c=3*(values[1]-values[0]);b=3*(values[0]-2*values[1]+values[2]);a=-values[0]+3*values[1]-3*values[2]+values[3]
    def value(t):return ((a*t+b)*t+c)*t+d
    cuts=[0.,1.];qa=3*a;qb=2*b;qc=c
    if abs(qa)<1e-12:
        if abs(qb)>1e-12:cuts.append(-qc/qb)
    else:
        disc=qb*qb-4*qa*qc
        if disc>=0:
            root=math.sqrt(disc);q=-.5*(qb+math.copysign(root,qb))
            cuts.extend([q/qa,qc/q] if q else [-qb/(2*qa)])
    cuts=sorted(set(t for t in cuts if 0<=t<=1));roots=[t for t in cuts if abs(value(t))<1e-8]
    for left,right in zip(cuts,cuts[1:]):
        lo=value(left);hi=value(right)
        if lo*hi>=0:continue
        for _ in range(64):
            middle=(left+right)/2;v=value(middle)
            if lo*v<=0:right=middle
            else:left=middle;lo=v
        roots.append((left+right)/2)
    result=[]
    for t in sorted(roots):
        u=1-t;weights=[u**3,3*u*u*t,3*u*t*t,t**3]
        point=[sum(w*p[k] for w,p in zip(weights,controls)) for k in range(2)]
        projection=((point[0]-ax)*dx+(point[1]-ay)*dy)/(length*length)
        residual=abs((point[0]-ax)*dy-(point[1]-ay)*dx)/length
        if 0<=projection<=1 and residual<1e-6 and not any(math.dist(point,p)<1e-5 for p in result):result.append(point)
    return result
