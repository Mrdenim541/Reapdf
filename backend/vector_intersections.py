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


# Curves use their original control polygons, never the display polyline.
# A point is reported only after both parameter intervals have been localized
# within 0.000002 pt and the original curves agree within 0.000001 pt.
CUBIC_SNAP_TOLERANCE=.000002


def _point(c,t):
    u=1-t;w=(u*u*u,3*u*u*t,3*u*t*t,t*t*t)
    return tuple(sum(a*p[k] for a,p in zip(w,c)) for k in (0,1))


def _derivative(c,t):
    u=1-t
    return tuple(3*(u*u*(c[1][k]-c[0][k])+2*u*t*(c[2][k]-c[1][k])+t*t*(c[3][k]-c[2][k])) for k in (0,1))


def _split(c):
    def mid(a,b):return tuple((a[k]+b[k])*.5 for k in (0,1))
    a,b,c,d=c;ab=mid(a,b);bc=mid(b,c);cd=mid(c,d);abc=mid(ab,bc);bcd=mid(bc,cd);m=mid(abc,bcd)
    return (a,ab,abc,m),(m,bcd,cd,d)


def _box(c):return (min(p[0] for p in c),min(p[1] for p in c),max(p[0] for p in c),max(p[1] for p in c))


def cubic_cubic(first,second,budget=None):
    """Return bounded isolated intersections and explicit incompleteness.

    A shared budget covers all pairs on a page. Exhaustion discards this pair's
    candidates instead of returning a misleading partial cluster of snaps.
    Coincident/collinear curves have no unique intersection to snap to.
    """
    if budget is None:budget=[0]
    a=tuple(tuple(p) for p in first);b=tuple(tuple(p) for p in second)
    if len(a)!=4 or len(b)!=4 or any(len(p)!=2 or any(not math.isfinite(v) or abs(v)>1e7 for v in p) for p in a+b):return {'points':[],'limited':True,'reason':'invalid'}
    if a==b or a==tuple(reversed(b)):return {'points':[],'limited':True,'reason':'coincident'}
    # This includes cubic representations of the same straight line. Even a
    # different parameterization must not generate a cloud of false crossings.
    endpoints=max(((p,q) for p in a+b for q in a+b),key=lambda pair:math.dist(*pair));p,q=endpoints;length=math.dist(p,q)
    if length<1e-8:return {'points':[],'limited':True,'reason':'degenerate'}
    if all(abs((r[0]-p[0])*(q[1]-p[1])-(r[1]-p[1])*(q[0]-p[0]))/length<1e-9 for r in a+b):return {'points':[],'limited':True,'reason':'collinear'}
    points=[]
    for p in (a[0],a[-1]):
        if any(math.dist(p,q)<1e-10 for q in (b[0],b[-1])) and not any(math.dist(p,q)<1e-5 for q in points):points.append(list(p))
    stack=[(a,b,0.,1.,0.,1.,0)];nodes=0
    while stack:
        ca,cb,ta,tb,ua,ub,depth=stack.pop();budget[0]+=1;nodes+=1
        if nodes>12000 or budget[0]>100000:return {'points':[],'limited':True,'reason':'budget'}
        x=_box(ca);y=_box(cb)
        if x[2]<y[0]-1e-10 or y[2]<x[0]-1e-10 or x[3]<y[1]-1e-10 or y[3]<x[1]-1e-10:continue
        sa=max(x[2]-x[0],x[3]-x[1]);sb=max(y[2]-y[0],y[3]-y[1])
        if max(sa,sb)<=CUBIC_SNAP_TOLERANCE:
            t=(ta+tb)*.5;u=(ua+ub)*.5
            # Newton also consolidates adjacent candidate boxes at tangencies.
            for _ in range(40):
                pa=_point(a,t);pb=_point(b,u);da=_derivative(a,t);db=_derivative(b,u);dx=pa[0]-pb[0];dy=pa[1]-pb[1];det=da[1]*db[0]-da[0]*db[1]
                if abs(det)<1e-16:break
                nt=t+(dx*db[1]-dy*db[0])/det;nu=u+(dx*da[1]-dy*da[0])/det
                if not 0<=nt<=1 or not 0<=nu<=1:break
                t,u=nt,nu
            pa=_point(a,t);pb=_point(b,u)
            if math.dist(pa,pb)<=1e-6:
                point=[(pa[k]+pb[k])*.5 for k in (0,1)]
                if not any(math.dist(point,old)<1e-5 for old in points):points.append(point)
            continue
        if depth>=80:return {'points':[],'limited':True,'reason':'depth'}
        if sa>=sb:
            left,right=_split(ca);tm=(ta+tb)*.5;stack.extend([(right,cb,tm,tb,ua,ub,depth+1),(left,cb,ta,tm,ua,ub,depth+1)])
        else:
            left,right=_split(cb);um=(ua+ub)*.5;stack.extend([(ca,right,ta,tb,um,ub,depth+1),(ca,left,ta,tb,ua,um,depth+1)])
    return {'points':points,'limited':False,'reason':''}
