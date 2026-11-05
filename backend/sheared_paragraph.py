"""Pack common-baseline styles with independent vertical shear, without flattening."""
import pymupdf as f
from .mixed_spacing import Layout
from .engine import DocumentError


def compatible(first,row):
    reference=f.Matrix(*first['_geometry']['matrix']);reference[4]=reference[5]=0
    current=f.Matrix(*row['_geometry']['matrix']);current[4]=current[5]=0
    relative=current*~reference
    return max(abs(relative.a-1),abs(relative.b),abs(relative.d-1))<=1e-4


def distinct(rows):
    return any(max(abs(a-b) for a,b in zip(r['_geometry']['matrix'][:4],rows[0]['_geometry']['matrix'][:4]))>1e-4 for r in rows)


def overhang(first,row):
    reference=f.Matrix(*first['_geometry']['matrix']);reference[4]=reference[5]=0
    matrix=f.Matrix(*row['_geometry']['matrix']);matrix[4]=matrix[5]=0;relative=matrix*~reference
    values=[relative.c*row['_geometry'][k] for k in ['ascent','descent']]
    return min(0,*values),max(0,*values)


def join_gap(first,left,right):
    state=left['_spacing']['state'];last=left['text'][-1:]
    gap=(state['char']+(state['word'] if last==' ' and left['_font'].encode(last,left['size'])[0]==b' ' else 0))*state['scale']/100
    return overhang(first,left)[1]-overhang(first,right)[0]+max(0,gap)


class ShearedLayout(Layout):
    def __init__(self,rows,runs):
        super().__init__(rows,runs)
        self.overhang={row['id']:overhang(rows[0],row) for row in rows}

    def pack(self,start,end):
        cursor=start;edge=0.;positions={};last_gap=0.
        while cursor<end:
            row=self.styles[cursor];stop=cursor+1
            while stop<end and self.styles[stop] is row:stop+=1
            left,right=self.overhang[row['id']];origin=edge-left;positions[cursor-start]=origin
            last_gap=max(0,self.gaps[stop-1]);edge=origin+self.extent(cursor,stop)+right+last_gap;cursor=stop
        return max(0,edge-last_gap),positions

    def line(self,text,start,width):
        end=text.find('\n',start)
        if end<0:end=len(text)
        if end==start:return '',start+1,True
        if self.pack(start,end)[0]<=width:return text[start:end],end+int(end<len(text)),True
        lo,hi=start,end
        while lo<hi:
            mid=(lo+hi+1)//2
            if self.pack(start,mid)[0]<=width:lo=mid
            else:hi=mid-1
        if lo==start:raise DocumentError('El marco no permite un carácter con su inclinación original. Amplía el ancho.')
        space=text.rfind(' ',start,lo+1);stop=space if space>start else lo;after=stop
        while after<end and text[after]==' ':after+=1
        return text[start:stop].rstrip(' '),after,False
