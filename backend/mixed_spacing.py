"""Mixed original-font line fitting with Tc/Tw and retained adjacent TJ pairs."""
from .engine import DocumentError
from .text_spacing import retained_kern


class Layout:
    def __init__(self,rows,runs):
        self.styles=[];self.widths=[];self.gaps=[];self.kern=[];self.prefix=[0.]
        for row,run in zip(rows,runs):
            text=run['text'];kern=retained_kern(row,text)
            for i,char in enumerate(text):
                state=row['_spacing']['state'];scale=state['scale']/100
                encoded,width=(b'',0) if char=='\n' else row['_font'].encode(char,row['size'])
                adjustment=kern[i] if i<len(kern) and text[i+1]!='\n' else 0.
                gap=0 if char=='\n' else (state['char']+(state['word'] if encoded==b' ' else 0)-adjustment*row['size']/1000)*scale
                width*=scale;self.styles.append(row);self.widths.append(width);self.gaps.append(gap);self.kern.append(adjustment);self.prefix.append(self.prefix[-1]+width+gap)
        text=''.join(r['text'] for r in runs)
        for i in range(len(text)-1):
            if '\n' not in text[i:i+2] and (self.widths[i]+self.gaps[i]<=0 or self.widths[i+1]+self.gaps[i]<=0):raise DocumentError('El espaciado produciría avances invertidos o superpuestos. Se conserva el borrador.')

    def extent(self,start,end):return self.prefix[end]-self.prefix[start]-self.gaps[end-1] if end>start else 0.

    def line(self,text,start,width):
        end=text.find('\n',start)
        if end<0:end=len(text)
        if end==start:return '',start+1,True
        if self.extent(start,end)<=width:return text[start:end],end+int(end<len(text)),True
        lo,hi=start,end
        while lo<hi:
            mid=(lo+hi+1)//2
            if self.extent(start,mid)<=width:lo=mid
            else:hi=mid-1
        if lo==start:raise DocumentError('Una región es demasiado estrecha para el tamaño y espaciado originales.')
        space=text.rfind(' ',start,lo+1);stop=space if space>start else lo;after=stop
        while after<end and text[after]==' ':after+=1
        return text[start:stop].rstrip(' '),after,False


def operand(font,text,kern):
    if not any(kern):return b'<'+font.encode(text,1)[0].hex().encode()+b'> Tj'
    parts=[]
    for i,char in enumerate(text):
        parts.append(b'<'+font.encode(char,1)[0].hex().encode()+b'>')
        if i<len(text)-1 and kern[i]:parts.append(format(kern[i],'.8f').encode())
    return b'['+b' '.join(parts)+b'] TJ'
