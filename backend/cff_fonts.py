"""Bounded CFF1 font maps; original programs are never rewritten."""
from io import BytesIO
import re
from fontTools.cffLib import CFFFontSet
from fontTools.ttLib import TTFont
from fontTools.misc.psCharStrings import T2OutlineExtractor
from fontTools.pens.boundsPen import ControlBoundsPen
from .engine import DocumentError


class Outline(T2OutlineExtractor):
    def execute(self,charstring):
        if len(self.callingStack)>=16:raise DocumentError('Los subprogramas CFF superan el límite de profundidad.')
        original=charstring.getToken
        def bounded(index):
            self.budget.remaining-=1
            if self.budget.remaining<0:raise DocumentError('Los contornos CFF superan el presupuesto de análisis.')
            return original(index)
        charstring.getToken=bounded
        try:return super().execute(charstring)
        finally:charstring.getToken=original


class CFFFace:
    def __init__(self,data,subtype):
        self.remaining=200000;self.cache={};self.cid_to_gid={};self.names=set()
        try:
            if subtype=='OpenType':
                if data[:4]!=b'OTTO':raise ValueError('OpenType sin cabecera OTTO')
                font=TTFont(BytesIO(data),lazy=True)
                if 'CFF ' not in font or 'CFF2' in font or 'fvar' in font or font['head'].unitsPerEm!=1000:raise ValueError('OpenType CFF1 de 1000 unidades requerido')
                cff=font['CFF '].cff
                for record in font['name'].names:
                    if record.nameID in [1,4,6]:self.names.add(record.toUnicode())
            elif subtype in ['Type1C','CIDFontType0C']:
                cff=CFFFontSet();cff.decompile(BytesIO(data),None)
            else:raise ValueError('Subtipo CFF no admitido')
            if cff.major!=1 or len(cff.fontNames)!=1:raise ValueError('CFF1 de una sola fuente requerido')
            self.top=cff[cff.fontNames[0]];self.order=list(self.top.charset);self.count=len(self.order)
            if not 1<self.count<=65536 or len(set(self.order))!=self.count:raise ValueError('Charset CFF no válido')
            self.names.update(str(getattr(self.top,k,'')) for k in ['FullName','FamilyName','FontName'])
            standard=[.001,0,0,.001,0,0]
            if list(getattr(self.top,'FontMatrix',standard))!=standard:raise ValueError('Matriz CFF no compatible')
            if len(getattr(self.top,'FDArray',[]))>256 or len(getattr(cff,'GlobalSubrs',[]))>65536:raise ValueError('Subprogramas o diccionarios CFF excesivos')
            for fd in getattr(self.top,'FDArray',[]):
                if hasattr(fd,'FontMatrix') and list(fd.FontMatrix)!=standard:raise ValueError('Matriz CID CFF no compatible')
            self.cid=hasattr(self.top,'ROS')
            if subtype=='CIDFontType0C' and not self.cid or subtype=='Type1C' and self.cid:raise ValueError('El subtipo y charset CFF no coinciden')
            if self.cid:
                for gid,name in enumerate(self.order):
                    if gid==0 and name=='.notdef':self.cid_to_gid[0]=0;continue
                    if not re.fullmatch(r'cid\d{1,5}',name):raise ValueError('Charset CID CFF no verificable')
                    cid=int(name[3:])
                    if cid>65535 or cid in self.cid_to_gid:raise ValueError('CID CFF repetido o fuera de rango')
                    self.cid_to_gid[cid]=gid
            else:self.cid_to_gid={i:i for i in range(self.count)}
        except DocumentError:raise
        except Exception as exc:raise DocumentError('El programa CFF1 no tiene una estructura verificable compatible.') from exc

    def has_outline(self,gid):
        if gid in self.cache:return self.cache[gid]
        if not 0<gid<self.count:return False
        try:
            charstring=self.top.CharStrings[self.order[gid]];private=charstring.private;pen=ControlBoundsPen(None)
            extractor=Outline(pen,getattr(private,'Subrs',[]),charstring.globalSubrs,private.nominalWidthX,private.defaultWidthX,private)
            extractor.budget=self;extractor.execute(charstring);result=pen.bounds is not None
        except DocumentError:raise
        except Exception as exc:raise DocumentError('Un contorno CFF no se puede verificar.') from exc
        self.cache[gid]=result;return result
