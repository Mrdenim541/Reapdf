"""Conservative rectangular merge suggestions from visible separator evidence."""
import re
import pymupdf as f


def candidates(pix,box):
    width,height=pix.width,pix.height;mask=pix.samples.translate(bytes(1 if n<110 else 0 for n in range(256)))
    def positions(vertical):
        size=width if vertical else height;extent=box.height if vertical else box.width
        minimum=max(12,round(18*(height if vertical else width)/extent));pattern=re.compile(b'\x01{'+str(minimum).encode()+b',}');hits=[]
        for i in range(size):
            line=mask[i::width] if vertical else mask[i*width:(i+1)*width]
            if pattern.search(line):hits.append(i)
        groups=[]
        for n in hits:
            if groups and n-groups[-1][-1]<=2:groups[-1].append(n)
            else:groups.append([n])
        origin=box.x0 if vertical else box.y0;length=box.width if vertical else box.height
        found=[origin+(sum(g)/len(g)+.5)*length/size for g in groups]
        return [origin,*[v for v in found if origin+3<v<origin+length-3],origin+length]
    columns,rows=positions(True),positions(False)
    if len(columns)>31 or len(rows)>101:return None
    return columns,rows


def suggestions(pix,box,columns,rows,words=()):
    width,height=pix.width,pix.height;raw=pix.samples;nr,nc=len(rows)-1,len(columns)-1;parents=list(range(nr*nc));uncertain=0
    def edge(vertical,coordinate,start,end):
        # Ignore crossings at the endpoints, and accept narrow antialiased scans.
        center=round((coordinate-(box.x0 if vertical else box.y0))*(width if vertical else height)/(box.width if vertical else box.height))
        a=(start-(box.y0 if vertical else box.x0))*(height if vertical else width)/(box.height if vertical else box.width)
        b=(end-(box.y0 if vertical else box.x0))*(height if vertical else width)/(box.height if vertical else box.width)
        inset=max(2,(b-a)*.12);begin=max(0,int(a+inset));finish=min(height if vertical else width,int(b-inset));extent=width if vertical else height
        band=range(max(0,center-2),min(extent,center+3))
        if finish-begin<4 or not band:return None
        ignored=[]
        for word in words:
            x0,y0,x1,y1=word['bbox']
            if (x0-.8<=coordinate<=x1+.8 if vertical else y0-.8<=coordinate<=y1+.8):
                low,high=(y0,y1) if vertical else (x0,x1);offset=box.y0 if vertical else box.x0;factor=(height if vertical else width)/(box.height if vertical else box.width)
                ignored.append(((low-offset)*factor-1,(high-offset)*factor+1))
        samples=[t for t in range(begin,finish) if not any(a<=t<=b for a,b in ignored)]
        if len(samples)<4:return None
        hits=sum(any(raw[t*width+s if vertical else s*width+t]<140 for s in band) for t in samples);ratio=hits/len(samples)
        return True if ratio>=.8 else False if ratio<=.1 else None
    vertical=[[edge(True,x,rows[r],rows[r+1]) for x in columns] for r in range(nr)]
    horizontal=[[edge(False,y,columns[c],columns[c+1]) for c in range(nc)] for y in rows]
    if any(v is not True for v in [*[row[0] for row in vertical],*[row[-1] for row in vertical],*horizontal[0],*horizontal[-1]]):return [],['No se sugieren combinaciones: el borde exterior no está completo.']
    def find(a):
        while parents[a]!=a:parents[a]=parents[parents[a]];a=parents[a]
        return a
    def join(a,b):parents[find(b)]=find(a)
    for r in range(nr):
        for c in range(nc):
            if c+1<nc:
                state=vertical[r][c+1]
                if state is False:join(r*nc+c,r*nc+c+1)
                elif state is None:uncertain+=1
            if r+1<nr:
                state=horizontal[r+1][c]
                if state is False:join(r*nc+c,(r+1)*nc+c)
                elif state is None:uncertain+=1
    groups={}
    for r in range(nr):
        for c in range(nc):groups.setdefault(find(r*nc+c),[]).append((r,c))
    spans=[];irregular=0
    for group in groups.values():
        if len(group)<2:continue
        r0=min(r for r,c in group);r1=max(r for r,c in group);c0=min(c for r,c in group);c1=max(c for r,c in group)
        if len(group)!=(r1-r0+1)*(c1-c0+1) or any(vertical[r][c] is not False for r in range(r0,r1+1) for c in range(c0+1,c1+1)) or any(horizontal[r][c] is not False for r in range(r0+1,r1+1) for c in range(c0,c1+1)):
            irregular+=1;continue
        spans.append({'row':r0,'column':c0,'rowspan':r1-r0+1,'colspan':c1-c0+1})
    warnings=[]
    if uncertain:warnings.append(f'{uncertain} segmentos de borde ambiguos: no se combinan a través de ellos.')
    if irregular:warnings.append(f'{irregular} grupos no rectangulares o contradictorios conservan sus celdas separadas.')
    return sorted(spans,key=lambda s:(s['row'],s['column'])),warnings


def apply(words,cells,columns,rows,spans):
    from .table_regions import assign
    result=[row[:] for row in cells]
    for span in spans:
        r,c,h,w=[span[k] for k in ['row','column','rowspan','colspan']];x0,x1=columns[c],columns[c+w];y0,y1=rows[r],rows[r+h]
        selected=[word for word in words if x0<=(word['bbox'][0]+word['bbox'][2])/2<x1 and y0<=(word['bbox'][1]+word['bbox'][3])/2<y1]
        text=assign(selected,[x0,x1],[y0,y1])[0][0][0]
        if len(text)>4000:raise ValueError('Una combinación reconocida supera 4000 caracteres.')
        for ri in range(r,r+h):
            for ci in range(c,c+w):result[ri][ci]=''
        result[r][c]=text
    return result


def crossings(words,columns,rows,spans):
    from bisect import bisect_right
    owners={}
    for s in spans:
        for r in range(s['row'],s['row']+s['rowspan']):
            for c in range(s['column'],s['column']+s['colspan']):owners[r,c]=s
    total=0
    for word in words:
        x0,y0,x1,y1=word['bbox'];r=bisect_right(rows,(y0+y1)/2)-1;c=bisect_right(columns,(x0+x1)/2)-1
        if not 0<=r<len(rows)-1 or not 0<=c<len(columns)-1:continue
        s=owners.get((r,c),{'row':r,'column':c,'rowspan':1,'colspan':1});r=s['row'];c=s['column']
        total+=int(x0<columns[c]-.8 or x1>columns[c+s['colspan']]+.8 or y0<rows[r]-.8 or y1>rows[r+s['rowspan']]+.8)
    return total
