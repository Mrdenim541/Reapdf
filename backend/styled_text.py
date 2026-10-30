"""Fixed-position edits using the original PDF font, including bounded TTF subsets."""
import re
import struct
import zlib
from collections import defaultdict
import pymupdf as fitz
from .engine import open_pdf,export_pdf,DocumentError
from .document_tools import editable
from .paragraphs import region_model,prepare_text_page
from .text_style import FONT_OPTIONS

BASE_FONTS={name:key for key,name in FONT_OPTIONS}


def stream(doc,xref,limit):
    raw=doc.xref_stream_raw(xref)
    if raw is None or len(raw)>limit or doc.xref_get_key(xref,'DecodeParms')[0]!='null':raise DocumentError('El recurso usa una compresión o tamaño no compatible.')
    kind,value=doc.xref_get_key(xref,'Filter')
    if kind=='null':return raw
    if not ((kind=='name' and value=='/FlateDecode') or (kind=='array' and re.sub(r'\s','',value)=='[/FlateDecode]')):raise DocumentError('El recurso usa una compresión no compatible.')
    try:
        decoder=zlib.decompressobj();data=decoder.decompress(raw,limit+1)
        if len(data)>limit or decoder.unconsumed_tail or decoder.unused_data or not decoder.eof:raise ValueError()
        return data
    except (ValueError,zlib.error) as exc:raise DocumentError('El recurso supera el límite o su compresión no es válida.') from exc


def unicode_cmap(data,code_bytes=2):
    if code_bytes not in [1,2]:raise DocumentError('Tamaño de código de fuente no compatible.')
    if b'usecmap' in data:raise DocumentError('La fuente depende de otro mapa de caracteres no compatible.')
    text=re.sub(rb'%[^\r\n]*',b'',data).decode('ascii',errors='strict');mapping={}
    spaces=re.findall(r'begincodespacerange(.*?)endcodespacerange',text,re.S)
    if not spaces or any(len(re.sub(r'\s','',v))!=code_bytes*2 for area in spaces for v in re.findall(r'<([^>]*)>',area)):raise DocumentError('El mapa de la fuente no usa el tamaño de código esperado.')
    def put(cid,encoded):
        if not 0<=cid<256**code_bytes:raise DocumentError('Código de fuente fuera de rango.')
        try:char=encoded.decode('utf-16-be')
        except UnicodeError:return
        if len(char)!=1 or ord(char)<32:return
        if cid in mapping and mapping[cid]!=char:raise DocumentError('El mapa de caracteres contiene códigos contradictorios.')
        mapping[cid]=char
    for block in re.finditer(r'(\d+)\s+begin(bfchar|bfrange)\b(.*?)end\2',text,re.S):
        count=int(block[1]);area=block[3];tokens=re.findall(r'<[0-9A-Fa-f\s]+>|\[|\]',area)
        if count>65536 or re.sub(r'<[0-9A-Fa-f\s]+>|\[|\]|\s','',area):raise DocumentError('Mapa de caracteres no compatible.')
        pos=0
        def hex_bytes():
            nonlocal pos
            if pos>=len(tokens) or not tokens[pos].startswith('<'):raise DocumentError('Mapa de caracteres incompleto.')
            digits=re.sub(r'\s','',tokens[pos][1:-1]);value=bytes.fromhex(digits+('0' if len(digits)%2 else ''));pos+=1;return value
        for _ in range(count):
            start=hex_bytes()
            if len(start)!=code_bytes:raise DocumentError('Código de fuente no compatible.')
            first=int.from_bytes(start,'big')
            if block[2]=='bfchar':put(first,hex_bytes());continue
            end=hex_bytes()
            if len(end)!=code_bytes:raise DocumentError('Rango de fuente no compatible.')
            last=int.from_bytes(end,'big')
            if last<first:raise DocumentError('Rango de fuente invertido.')
            if pos<len(tokens) and tokens[pos]=='[':
                pos+=1
                for cid in range(first,last+1):put(cid,hex_bytes())
                if pos>=len(tokens) or tokens[pos]!=']':raise DocumentError('Rango de fuente incompleto.')
                pos+=1
            else:
                initial=hex_bytes()
                if not initial or len(initial)>16:raise DocumentError('Unicode de fuente no compatible.')
                value=int.from_bytes(initial,'big')
                for offset,cid in enumerate(range(first,last+1)):
                    try:encoded=(value+offset).to_bytes(len(initial),'big')
                    except OverflowError as exc:raise DocumentError('Rango Unicode fuera de límites.') from exc
                    put(cid,encoded)
        if pos!=len(tokens):raise DocumentError('El mapa de fuente contiene entradas adicionales.')
    if not mapping:raise DocumentError('La fuente no tiene un mapa Unicode compatible.')
    return mapping


class TrueType:
    def __init__(self,data):
        if len(data)<12 or data[:4] not in [b'\x00\x01\x00\x00',b'true']:raise DocumentError('Solo se conservan programas TrueType con contornos compatibles.')
        count=struct.unpack_from('>H',data,4)[0];tables={}
        if count>200 or 12+16*count>len(data):raise DocumentError('Directorio TrueType no válido.')
        for i in range(count):
            tag,_,start,length=struct.unpack_from('>4sIII',data,12+16*i)
            if start+length>len(data):raise DocumentError('Tabla de fuente fuera de límites.')
            tables[tag]=data[start:start+length]
        if b'fvar' in tables:raise DocumentError('La fuente TrueType variable necesita una instancia estática verificada; no se elige un eje de forma implícita.')
        self.names=set()
        try:
            names=tables.get(b'name',b'');records=struct.unpack_from('>H',names,2)[0];offset=struct.unpack_from('>H',names,4)[0]
            if records>2000:raise ValueError()
            for i in range(records):
                platform,_,_,identifier,length,start=struct.unpack_from('>6H',names,6+12*i)
                if identifier in [4,6] and offset+start+length<=len(names):
                    raw=names[offset+start:offset+start+length]
                    self.names.add(raw.decode('utf-16-be' if platform in [0,3] else 'mac_roman'))
        except (ValueError,UnicodeError,struct.error):pass
        try:
            head=tables[b'head'];self.glyf=tables[b'glyf'];loca=tables[b'loca'];self.count=struct.unpack_from('>H',tables[b'maxp'],4)[0]
            mode=struct.unpack_from('>h',head,50)[0]
            if mode not in [0,1]:raise ValueError()
            size=2 if mode==0 else 4
            if len(loca)<(self.count+1)*size:raise ValueError()
            self.offsets=[struct.unpack_from('>H' if size==2 else '>I',loca,i*size)[0]*(2 if size==2 else 1) for i in range(self.count+1)]
            if self.offsets!=sorted(self.offsets) or self.offsets[-1]>len(self.glyf):raise ValueError()
        except (KeyError,ValueError,struct.error) as exc:raise DocumentError('Los contornos TrueType no son compatibles.') from exc
        self.cache={}
        self.byte_cmap=None
        cmap=tables.get(b'cmap',b'')
        if len(cmap)>=12 and struct.unpack_from('>H',cmap,2)[0]==1:
            platform,encoding,offset=struct.unpack_from('>HHI',cmap,4)
            if platform==1 and encoding==0 and offset+262<=len(cmap) and struct.unpack_from('>HH',cmap,offset)==(0,262):
                self.byte_cmap=list(cmap[offset+6:offset+262])
    def has_outline(self,gid,path=()):
        if gid in self.cache:return self.cache[gid]
        if not 0<gid<self.count or gid in path or len(path)>16:return False
        start,end=self.offsets[gid:gid+2]
        if end-start<10:return False
        contours=struct.unpack_from('>h',self.glyf,start)[0]
        if contours>0:self.cache[gid]=True;return True
        if contours==0:return False
        pos=start+10;valid=True
        for _ in range(100):
            if pos+4>end:return False
            flags,child=struct.unpack_from('>HH',self.glyf,pos);pos+=4
            valid=valid and self.has_outline(child,(*path,gid));pos+=4 if flags&1 else 2
            pos+=2 if flags&8 else 4 if flags&64 else 8 if flags&128 else 0
            if pos>end:return False
            if not flags&32:self.cache[gid]=valid;return valid
        return False


def normal_name(value):return re.sub(r'\s','',re.sub(r'^[A-Z]{6}\+','',value.replace('#20',' ')))


def native_font(doc,xref):return fitz.mupdf.pdf_load_object(fitz._as_pdf_document(doc),xref)


class OriginalFont:
    def __init__(self,doc,item):
        self.xref,self.ext,self.type,self.name,self.resource,*_=item;self.base=None;self.options=defaultdict(list);self.aliases={normal_name(self.name)};self.program_bytes=0;self.code_bytes=2;self.trace_cid=False
        self.restricted=bool(re.match(r'^[A-Z]{6}\+',self.name))
        if self.type=='Type3':
            from .type3_fonts import load
            load(self,doc);return
        if self.type=='Type1' and self.name in BASE_FONTS:
            if doc.xref_get_key(self.xref,'FontDescriptor/FontFile3')[0]=='xref':self.load_simple(doc,cff=True);return
            if any(doc.xref_get_key(self.xref,'FontDescriptor/'+key)[0]!='null' for key in ['FontFile','FontFile2','FontFile3']):raise DocumentError('Las fuentes Type1 incrustadas requieren otro tratamiento; no se sustituyen por una fuente base.')
            if doc.xref_get_key(self.xref,'Widths')[0]!='null':raise DocumentError('La fuente base tiene anchuras personalizadas.')
            encoding=doc.xref_get_key(self.xref,'Encoding')
            if encoding not in [('name','/WinAnsiEncoding'),('null','null')]:raise DocumentError('La fuente base tiene una codificación no compatible.')
            self.encoding='cp1252' if encoding[0]=='name' else 'ascii';self.base=fitz.Font(BASE_FONTS[self.name]);return
        if self.type=='Type1':
            self.load_simple(doc,cff=True);return
        if self.type=='TrueType':
            if doc.xref_get_key(self.xref,'Encoding')[0]=='null':self.load_builtin(doc)
            else:self.load_simple(doc)
            return
        if self.type!='Type0' or doc.xref_get_key(self.xref,'Encoding')!=('name','/Identity-H'):raise DocumentError('Se requiere una fuente base, TrueType o CFF1 compatible con Identity-H/WinAnsi.')
        n=fitz.mupdf;obj=native_font(doc,self.xref);desc=n.pdf_dict_gets(obj,'DescendantFonts')
        if n.pdf_array_len(desc)!=1:raise DocumentError('La fuente compuesta no tiene un descendiente único.')
        descendant=n.pdf_array_get(desc,0)
        kind=n.pdf_to_name(n.pdf_dict_gets(descendant,'Subtype'));cff=kind=='CIDFontType0'
        if kind not in ['CIDFontType2','CIDFontType0']:raise DocumentError('El tipo de contorno compuesto no es compatible.')
        program=n.pdf_dict_getp(descendant,'FontDescriptor/'+('FontFile3' if cff else 'FontFile2'));program_xref=n.pdf_to_num(program)
        if not program_xref:raise DocumentError('Falta el programa TrueType incrustado.')
        program_data=stream(doc,program_xref,16*1024*1024);self.program_bytes=len(program_data);face=self.cff_face(doc,program_xref,program_data) if cff else TrueType(program_data);self.aliases.update(normal_name(n) for n in face.names);self.trace_cid=bool(cff and face.cid)
        cmap_xref=n.pdf_to_num(n.pdf_dict_gets(obj,'ToUnicode'))
        if not cmap_xref:raise DocumentError('Falta el mapa Unicode de la fuente.')
        mapping=unicode_cmap(stream(doc,cmap_xref,2*1024*1024))
        width_obj=n.pdf_dict_gets(descendant,'W');widths={};i=0
        if n.pdf_array_len(width_obj)>100000:raise DocumentError('La tabla de anchuras supera el límite.')
        while i<n.pdf_array_len(width_obj):
            first=n.pdf_to_int(n.pdf_array_get(width_obj,i));i+=1;value=n.pdf_array_get(width_obj,i);i+=1
            if n.pdf_is_array(value):
                count=n.pdf_array_len(value)
                if not 0<=first<=first+count-1<=65535:raise DocumentError('Anchuras de fuente fuera de rango.')
                for offset in range(count):widths[first+offset]=n.pdf_to_real(n.pdf_array_get(value,offset))
            else:
                last=n.pdf_to_int(value);width=n.pdf_to_real(n.pdf_array_get(width_obj,i));i+=1
                if not 0<=first<=last<=65535:raise DocumentError('Rango de anchuras no compatible.')
                for cid in range(first,last+1):widths[cid]=width
        default_obj=n.pdf_dict_gets(descendant,'DW');default=1000 if n.pdf_is_null(default_obj) else n.pdf_to_real(default_obj)
        gid_obj=n.pdf_dict_gets(descendant,'CIDToGIDMap');gid_data=None
        if cff and not n.pdf_is_null(gid_obj):raise DocumentError('CIDToGIDMap no es válido para este modo CFF.')
        if n.pdf_is_stream(gid_obj):gid_data=stream(doc,n.pdf_to_num(gid_obj),131072)
        elif not n.pdf_is_null(gid_obj) and n.pdf_to_name(gid_obj)!='Identity':raise DocumentError('La fuente usa un mapa de glifos no compatible.')
        for cid,char in mapping.items():
            width=widths.get(cid,default)
            if not 0<width<=10000:continue
            if cff:gid=face.cid_to_gid.get(cid,0)
            elif gid_data is None:gid=cid
            elif cid*2+2<=len(gid_data):gid=int.from_bytes(gid_data[cid*2:cid*2+2],'big')
            else:continue
            if 0<gid<face.count and (char in [' ','\u00a0'] or face.has_outline(gid)):
                self.options[char].append((cid,width/1000,gid))
    def load_builtin(self,doc):
        kind,flags=doc.xref_get_key(self.xref,'FontDescriptor/Flags')
        if kind!='int' or not int(flags)&4:raise DocumentError('La codificación integrada requiere una clasificación simbólica explícita y un mapa verificado.')
        kind,value=doc.xref_get_key(self.xref,'FontDescriptor/FontFile2')
        if kind!='xref':raise DocumentError('Falta el programa TrueType incrustado.')
        data=stream(doc,int(value.split()[0]),16*1024*1024);self.program_bytes=len(data);face=TrueType(data)
        if face.byte_cmap is None:raise DocumentError('La fuente integrada requiere un único cmap Macintosh de un byte; no se adivina su codificación.')
        kind,value=doc.xref_get_key(self.xref,'ToUnicode')
        if kind!='xref':raise DocumentError('Falta ToUnicode para la fuente integrada.')
        mapping=unicode_cmap(stream(doc,int(value.split()[0]),2*1024*1024),1)
        n=fitz.mupdf;obj=native_font(doc,self.xref);first=n.pdf_dict_gets(obj,'FirstChar');last=n.pdf_dict_gets(obj,'LastChar');widths=n.pdf_dict_gets(obj,'Widths')
        if not n.pdf_is_int(first) or not n.pdf_is_int(last):raise DocumentError('Rango de anchuras no válido.')
        a,b=n.pdf_to_int(first),n.pdf_to_int(last)
        if not 0<=a<=b<=255 or n.pdf_array_len(widths)!=b-a+1:raise DocumentError('Tabla de anchuras integrada no válida.')
        self.code_bytes=1;self.aliases.update(normal_name(name) for name in face.names)
        for cid,char in mapping.items():
            if not a<=cid<=b:continue
            glyph=face.byte_cmap[cid];width=n.pdf_to_real(n.pdf_array_get(widths,cid-a))
            if 0<width<=10000 and 0<glyph<face.count and (char in [' ','\u00a0'] or face.has_outline(glyph)):
                self.options[char].append((cid,width/1000,glyph))

    def cff_face(self,doc,xref,data):
        from .cff_fonts import CFFFace
        kind,value=doc.xref_get_key(xref,'Subtype')
        if kind!='name':raise DocumentError('Falta el subtipo del programa CFF.')
        return CFFFace(data,value.lstrip('/'))

    def load_simple(self,doc,cff=False):
        if doc.xref_get_key(self.xref,'Encoding')!=('name','/WinAnsiEncoding'):raise DocumentError('La fuente simple requiere WinAnsi explícita, sin diferencias.')
        kind,flags=doc.xref_get_key(self.xref,'FontDescriptor/Flags')
        if kind!='int' or int(flags)&4 or not int(flags)&32:raise DocumentError('Las TrueType simbólicas o sin clasificación no se editan como WinAnsi.')
        kind,value=doc.xref_get_key(self.xref,'FontDescriptor/'+('FontFile3' if cff else 'FontFile2'))
        if kind!='xref':raise DocumentError('Falta el programa de fuente simple incrustado.')
        data=stream(doc,int(value.split()[0]),16*1024*1024);self.program_bytes=len(data);face=self.cff_face(doc,int(value.split()[0]),data) if cff else TrueType(data)
        if cff and face.cid:raise DocumentError('La fuente simple no puede usar charset CID.')
        self.aliases.update(normal_name(name) for name in face.names)
        try:font=fitz.Font(fontbuffer=data)
        except Exception as exc:raise DocumentError('No se pudo leer el mapa de glifos TrueType simple.') from exc
        n=fitz.mupdf;obj=native_font(doc,self.xref)
        first_obj=n.pdf_dict_gets(obj,'FirstChar');last_obj=n.pdf_dict_gets(obj,'LastChar');widths=n.pdf_dict_gets(obj,'Widths')
        if not n.pdf_is_int(first_obj) or not n.pdf_is_int(last_obj):raise DocumentError('Falta el rango de anchuras de la TrueType simple.')
        first,last=n.pdf_to_int(first_obj),n.pdf_to_int(last_obj)
        if not 0<=first<=last<=255 or n.pdf_array_len(widths)!=last-first+1:raise DocumentError('La tabla WinAnsi de anchuras no es válida.')
        cmap_obj=n.pdf_dict_gets(obj,'ToUnicode');mapping=None
        if not n.pdf_is_null(cmap_obj):
            if not n.pdf_is_stream(cmap_obj):raise DocumentError('El mapa Unicode simple no es compatible.')
            mapping=unicode_cmap(stream(doc,n.pdf_to_num(cmap_obj),2*1024*1024),1)
            for cid,char in mapping.items():
                try:expected=bytes([cid]).decode('cp1252')
                except UnicodeError:expected=None
                if char!=expected:raise DocumentError('El mapa Unicode contradice WinAnsi; se requiere otro tratamiento.')
        self.code_bytes=1
        for cid in range(first,last+1):
            try:char=bytes([cid]).decode('cp1252')
            except UnicodeError:continue
            if ord(char)<32 or ord(char)==127 or mapping is not None and cid not in mapping:continue
            width_obj=n.pdf_array_get(widths,cid-first)
            if not n.pdf_is_number(width_obj):continue
            width=n.pdf_to_real(width_obj);gid=font.has_glyph(ord(char),fallback=0)
            if 0<width<=10000 and 0<gid<face.count and (char in [' ','\u00a0'] or face.has_outline(gid)):
                self.options[char].append((cid,width/1000,gid))

    def encode(self,text,size):
        if self.base:
            try:data=text.encode(self.encoding)
            except UnicodeEncodeError as exc:raise DocumentError('La fuente original no admite uno de los caracteres. Cambia el texto o usa el reemplazo con DejaVu Sans.') from exc
            if any(not self.base.has_glyph(ord(c),fallback=0) for c in text):raise DocumentError('Un carácter no está disponible en la fuente original.')
            return data,self.base.text_length(text,fontsize=size)
        result=bytearray();width=0
        for char in text:
            entries=self.options.get(char,[])
            if not entries:raise DocumentError(f'La fuente original no contiene el carácter «{char}». Cambia el texto o usa DejaVu Sans.')
            if len({(round(w,6),gid) for _,w,gid in entries})!=1:raise DocumentError(f'El carácter «{char}» tiene varias formas ambiguas en esta fuente.')
            cid,advance,_=entries[0];result.extend(cid.to_bytes(self.code_bytes,'big'));width+=advance*size
        return bytes(result),width


def styled_model(doc,number,box,font_cache=None):
    rect,_=region_model(doc,number,box,minimum=.1,affine=True);page=doc[number]
    cache={} if font_cache is None else font_cache
    if '_route_native' not in cache:
        content=page.read_contents();kerned=False
        if b'TJ' in content:
            from .pdf_content import operations as content_operations
            try:kerned=any(op=='TJ' and len(args)==1 and args[0].kind=='array' and any(t.kind=='number' and t.value!=0 for t in args[0].value) for op,args,_ in content_operations(content))
            except DocumentError:pass
        from .pdf_content import placements,operations as content_operations
        multiple=False;transformed=False;segmented=False
        try:objects=placements(content)['texts'];segmented=len(objects)>sum(op=='BT' for op,_,_ in content_operations(content));multiple=any(o['shows'][0].kind=='operator-array' for o in objects);transformed=any(tuple(o['matrix'])!=(1.,0.,0.,1.,0.,0.) for o in objects) or any(op=='Tm' and [t.value for t in args[:4]]!=[1,0,0,1] for op,args,_ in content_operations(content))
        except DocumentError:transformed=bool(re.search(rb'(?<![A-Za-z])(?:cm|Tm)(?![A-Za-z])',content))
        cache['_route_native']=bool(transformed or segmented or multiple or kerned or page.get_xobjects() or any(i[1] in ['cff','otf','cid'] or i[2]=='Type3' for i in page.get_fonts()) or re.search(rb'(?<![A-Za-z])(?:BDC|BMC|W\*?|Tc|Tw|Tz|gs)(?![A-Za-z])',content))
    if cache['_route_native']:
        from .native_text import native_model
        return native_model(doc,number,rect,cache)
    region_model(doc,number,box,minimum=.1)
    if page.get_xobjects() or doc.get_ocgs() or doc.xref_get_key(page.xref,'Resources')[0]=='null':raise DocumentError('Este modo requiere texto directo sin capas ni objetos de formulario internos.')
    if any(doc.xref_get_key(page.xref,key)[0]!='null' for key in ['Resources/ExtGState','Resources/Pattern','Resources/Shading']):raise DocumentError('Las transparencias, patrones o sombreados necesitan una edición adicional antes de conservar estilos.')
    if re.search(rb'(?<![A-Za-z])(?:BDC|BMC|W\*?)(?![A-Za-z])',page.read_contents()):raise DocumentError('El contenido marcado o recortado todavía no es compatible con este modo.')
    traces=page.get_texttrace()
    if sum(len(t['chars']) for t in traces)>100000:raise DocumentError('La página supera el límite de texto para analizar estilos.')
    if any(t['type']!=0 or t['opacity']!=1 or t['layer'] for t in traces):raise DocumentError('Este modo no admite texto oculto, contorneado, transparente o asociado a capas.')
    fonts=page.get_fonts(full=True)
    if len(fonts)>20:raise DocumentError('Este modo admite hasta 20 recursos de fuente por página.')
    cache={} if font_cache is None else font_cache;rows=[];program_bytes=sum(v.program_bytes for v in cache.values() if isinstance(v,OriginalFont))
    for item in fonts:
        if item[-1] or item[0] in cache:continue
        try:
            font=OriginalFont(doc,item);program_bytes+=font.program_bytes
            if program_bytes>64*1024*1024:raise DocumentError('Los programas de fuente superan 64 MB.')
            cache[item[0]]=font
        except (DocumentError,ValueError,struct.error,UnicodeError) as exc:cache[item[0]]=str(exc)
    for bi,block in enumerate(page.get_text('rawdict',flags=fitz.TEXTFLAGS_TEXT,sort=True)['blocks']):
        for li,line in enumerate(block.get('lines',[])):
            for si,span in enumerate(line['spans']):
                bounds=fitz.Rect(span['bbox'])
                if (bounds&rect).get_area()<=.1:continue
                text=''.join(c['c'] for c in span['chars']);reason='';font=None
                candidates={i[0]:i for i in fonts if not i[-1] and (normal_name(i[3])==normal_name(span['font']) or isinstance(cache.get(i[0]),OriginalFont) and normal_name(span['font']) in cache[i[0]].aliases)}
                if len(candidates)!=1:reason='No se pudo identificar una fuente original única para este fragmento.'
                else:
                    item=next(iter(candidates.values()));xref=item[0]
                    if xref not in cache:
                        try:cache[xref]=OriginalFont(doc,item)
                        except (DocumentError,ValueError,struct.error,UnicodeError) as exc:cache[xref]=str(exc)
                    font=cache[xref]
                    if isinstance(font,str):reason=font;font=None
                if not reason:
                    try:
                        _,expected=font.encode(text,span['size'])
                        if abs(expected-bounds.width)>.3:reason='El fragmento usa espaciado o escala horizontal que todavía no se conserva.'
                        advance=0
                        for char in span['chars']:
                            if abs(char['origin'][0]-span['origin'][0]-advance)>.3:reason='El fragmento tiene ajustes de espaciado que todavía no se conservan.';break
                            _,step=font.encode(char['c'],span['size']);advance+=step
                    except DocumentError as exc:reason=str(exc)
                rows.append({'id':f'{bi}:{li}:{si}','text':text,'font':span['font'],'size':span['size'],'color':span['color'],'origin':list(span['origin']),'bbox':list(bounds),'editable':not reason,'reason':reason,'subset':bool(font and font.restricted),'_font':font})
    if len(rows)>100:raise DocumentError('Hasta 100 fragmentos por región; divide el bloque.')
    return rect,rows


def inspect_styled(base,operations,number,box):
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,operations)) as doc:
        prepare_text_page(doc,number)
        _,rows=styled_model(doc,number,box)
        return {'runs':[{k:v for k,v in r.items() if not k.startswith('_')} for r in rows]}


def replace_styled(base,operations,number,box,changes,expand=False):
    if type(expand) is not bool:raise DocumentError('La ampliación de ancho debe ser verdadera o falsa.')
    if not isinstance(changes,list) or not 1<=len(changes)<=100:raise DocumentError('Indica de 1 a 100 fragmentos editados.')
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,operations)) as doc:
        page,rotation=prepare_text_page(doc,number)
        rect,rows=styled_model(doc,number,box)
        prepared=prepare_changes(doc,number,rect,rows,changes,expand)
        write_changes(doc,number,prepared)
        doc[number].set_rotation(rotation)
        data=doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
    from .affine_text import verify
    verify(data,{number:prepared});return data


def prepare_changes(doc,number,rect,rows,changes,expand=False):
    model={r['id']:r for r in rows};seen=set();prepared=[];total=0
    from .type3_text import merge_lines
    neighbor_blocks=merge_lines(doc,doc[number],doc[number].get_text('dict',flags=fitz.TEXTFLAGS_TEXT)['blocks'])
    for change in changes:
        if not isinstance(change,dict) or set(change)!={'id','text'} or not isinstance(change.get('id'),str) or change['id'] not in model or change['id'] in seen:raise DocumentError('Fragmento inexistente, repetido o con propiedades no compatibles.')
        seen.add(change['id']);row=model[change['id']];text=change['text']
        if not isinstance(text,str) or len(text)>4000 or any(ord(c)<32 or ord(c)==127 for c in text):raise DocumentError('Cada fragmento admite una línea, sin controles, dentro del límite de 4000 caracteres.')
        total+=len(text)
        if text==row['text']:continue
        if not row['editable']:raise DocumentError(row['reason'])
        if '_native' in row:
            from .text_spacing import replacement
            encoded,width=replacement(row,text)
        else:encoded,width=row['_font'].encode(text,row['size'])
        if '_geometry' in row:
            from .affine_text import polygon,contains,rectangle,overlap
            g=row['_geometry'];target=polygon(g,width)
            if not expand and width>g['width']+.1:raise DocumentError('El texto no cabe en el ancho disponible. Acórtalo o amplía su región; este modo no redistribuye las líneas.')
            if width and (not contains(rectangle(rect),target) or not contains(rectangle(doc[number].rect),target)):raise DocumentError('El texto sale de la página o de la región disponible.')
            if width and any(not contains(clip,target) for clip in row.get('_clips',[])):raise DocumentError('El texto nuevo sale del recorte del objeto Form.')
            if any(overlap(target,obstacle)>.1 for obstacle in row.get('_obstacles',[])):raise DocumentError('El texto nuevo cruza una imagen, campo o anotación.')
            original=polygon(g)
            for block in neighbor_blocks:
                for line in block.get('lines',[]):
                    for span in line['spans']:
                        if span['origin']==tuple(row['origin']) and span['font']==row['font'] and span['text']==row['text']:continue
                        neighbor=rectangle(fitz.Rect(span['bbox']))
                        if overlap(neighbor,target)>.1 or overlap(neighbor,original)>.1:raise DocumentError('El texto se cruza con otro fragmento.')
        else:
            available=rect.x1-row['origin'][0] if expand else fitz.Rect(row['bbox']).width
            if width>available+.1:raise DocumentError('El texto no cabe en el ancho disponible. Acórtalo o amplía el área y activa su ancho disponible; este modo no redistribuye las líneas.')
            if not page_contains(doc[number],row,width):raise DocumentError('El texto sale de la página o se cruza con otro fragmento.')
        prepared.append(({**row,'_replacement_text':text,'_replacement_width':width},encoded))
    if total>4000:raise DocumentError('Hasta 4000 caracteres entre los fragmentos editados.')
    if not prepared:raise DocumentError('No hay cambios de texto para aplicar.')
    return prepared


def write_changes(doc,number,prepared):
    page=doc[number]
    if all('_native' in row for row,_ in prepared):
        from .form_text import write
        write(doc,page,prepared);return
    clone_resources(doc,page)
    for row,_ in prepared:page.add_redact_annot(fitz.Rect(row['bbox']),fill=False,cross_out=False)
    page.apply_redactions(images=0,graphics=0,text=0)
    page.wrap_contents()
    font_dict=clone_resources(doc,page)
    snippets=[]
    for index,(row,encoded) in enumerate(prepared):
        alias=f'ReapdfOriginal{index+1}'
        while doc.xref_get_key(font_dict,alias)[0]!='null':alias+='x'
        doc.xref_set_key(font_dict,alias,f"{row['_font'].xref} 0 R")
        if not encoded:continue
        origin=fitz.Point(row['origin'])*~page.transformation_matrix;color=[((row['color']>>shift)&255)/255 for shift in [16,8,0]]
        snippets.append(f"q BT /{alias} {row['size']:.8f} Tf {' '.join(f'{v:.8f}' for v in color)} rg 1 0 0 1 {origin.x:.8f} {origin.y:.8f} Tm <{encoded.hex()}> Tj ET Q")
    if snippets:
        content=doc.get_new_xref();doc.update_object(content,'<<>>');doc.update_stream(content,'\n'.join(snippets).encode('ascii'))
        page.set_contents(content) if not page.get_contents() else doc.xref_set_key(page.xref,'Contents','['+' '.join(f'{x} 0 R' for x in page.get_contents()+[content])+']')


def replace_styled_regions(base,operations,regions):
    """Validate every region first, then redact once per page and serialize once.

    Each region carries stable row IDs from the same exported snapshot. No
    intermediate PDF is published if a later region fails validation.
    """
    if not isinstance(regions,list) or not 1<=len(regions)<=100:raise DocumentError('Selecciona de 1 a 100 regiones.')
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,operations)) as doc:
        prepared=defaultdict(list);rotations={};caches=defaultdict(dict);seen=set();characters=0
        for region in regions:
            number=region['page'];changes=region['changes']
            if not isinstance(changes,list) or not 1<=len(changes)<=100:raise DocumentError('Indica de 1 a 100 fragmentos editados.')
            if number not in rotations:_,rotations[number]=prepare_text_page(doc,number)
            rect,rows=styled_model(doc,number,region['box'],caches[number])
            try:items=prepare_changes(doc,number,rect,rows,changes)
            except DocumentError as exc:raise DocumentError(f'Página {number+1}: {exc} No se aplicó ningún cambio.') from exc
            for row,_ in items:
                key=(number,row['id'])
                if key in seen:raise DocumentError('Un fragmento aparece en más de una región.')
                seen.add(key);characters+=len(row['text'])
            if len(seen)>100 or characters>20000:raise DocumentError('Hasta 100 fragmentos y 20000 caracteres originales por operación.')
            prepared[number].extend(items)
        for number,items in prepared.items():
            write_changes(doc,number,items);doc[number].set_rotation(rotations[number])
        data=doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
    from .affine_text import verify
    verify(data,prepared);return data


def page_contains(page,row,width):
    target=fitz.Rect(row['bbox']);target.x1=row['origin'][0]+width
    if width and not page.rect.contains(target):return False
    from .type3_text import merge_lines
    for block in merge_lines(page.parent,page,page.get_text('dict',flags=fitz.TEXTFLAGS_TEXT)['blocks']):
        for line in block.get('lines',[]):
            for span in line['spans']:
                if span['origin']==tuple(row['origin']) and span['font']==row['font'] and span['text']==row['text']:continue
                if (fitz.Rect(span['bbox'])&target).get_area()>.1 or (fitz.Rect(span['bbox'])&fitz.Rect(row['bbox'])).get_area()>.1:return False
    return True


def clone_resources(doc,page):
    # Detach both dictionaries before native redaction cleans resources. A font
    # dictionary may be shared even when the top resource dictionaries differ.
    kind,raw=doc.xref_get_key(page.xref,'Resources');resource=doc.get_new_xref()
    doc.update_object(resource,doc.xref_object(int(raw.split()[0])) if kind=='xref' else raw if kind=='dict' else '<<>>')
    doc.xref_set_key(page.xref,'Resources',f'{resource} 0 R')
    kind,raw=doc.xref_get_key(resource,'Font');font_dict=doc.get_new_xref()
    doc.update_object(font_dict,doc.xref_object(int(raw.split()[0])) if kind=='xref' else raw if kind=='dict' else '<<>>')
    doc.xref_set_key(resource,'Font',f'{font_dict} 0 R')
    return font_dict
