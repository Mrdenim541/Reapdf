"""Atomic flow through explicit regions using verified source font programs."""
import math,re,unicodedata
import pymupdf as f
from .engine import DocumentError,open_pdf,export_pdf,finite
from .document_tools import editable
from .original_mixed_reflow import source_runs,public_runs
from .original_reflow import compatible_page
from .styled_text import clone_resources
from .mixed_flow import layout_mixed
from .text_flow import next_line,regions_model


class OriginalMetrics:
    def __init__(self,row):
        self.original=row['_font'];self.ascender=(row['origin'][1]-row['bbox'][1])/row['size'];self.descender=(row['origin'][1]-row['bbox'][3])/row['size']
    def char_lengths(self,text,fontsize):return [0 if c=='\n' else self.original.encode(c,fontsize)[1] for c in text]


def collect(doc,rows):
    result=[]
    for index,region in enumerate(rows):
        compatible_page(doc,doc[region['page']])
        if not region['replace']:continue
        rect=region['rect'];_,sources=source_runs(doc,region['page'],[rect.x0,rect.y0,rect.width,rect.height]);public=public_runs(sources)
        if result:result[-1]['text']+='\n\n'
        for row,value in zip(sources,public):
            if not 6<=row['size']<=72:raise DocumentError('El flujo original admite fuentes de 6 a 72 pt.')
            result.append({**value,'id':str(index)+':'+row['id'],'font_name':row['font'],'font':OriginalMetrics(row),'color':[((row['color']>>v)&255)/255 for v in [16,8,0]]})
    if not 1<=len(result)<=200:raise DocumentError('El flujo original admite de 1 a 200 fragmentos.')
    return result


def inspect_original(doc,rows):
    try:
        runs=collect(doc,rows)
        return {'original_supported':True,'original_reason':'','original_runs':[{k:r[k] for k in ['id','text','font_name','size','color']} for r in runs]}
    except DocumentError as exc:return {'original_supported':False,'original_reason':str(exc),'original_runs':[]}


def write_draws(doc,draws):
    # All font objects belong to this document and remain referenced after
    # redaction. Do not subset them or replace their programs.
    snippets={};aliases={};resources={}
    for draw in draws:
        number=draw['page'];font=draw['font'].original;key=(number,font.xref)
        if number not in resources:resources[number]=clone_resources(doc,doc[number])
        if key not in aliases:
            alias='ReapdfFlowOriginal'+str(len(aliases)+1)
            while doc.xref_get_key(resources[number],alias)[0]!='null':alias+='x'
            doc.xref_set_key(resources[number],alias,f'{font.xref} 0 R');aliases[key]=alias
        point=f.Point(draw['origin'])*~doc[number].transformation_matrix;encoded=font.encode(draw['text'],draw['size'])[0]
        snippets.setdefault(number,[]).append(f"q BT 0 Tc 0 Tw 100 Tz 0 Tr 0 Ts /{aliases[key]} {draw['size']:.8f} Tf {' '.join(str(v) for v in draw['color'])} rg 1 0 0 1 {point.x:.8f} {point.y:.8f} Tm <{encoded.hex()}> Tj ET Q")
    for number,parts in snippets.items():
        page=doc[number];xref=doc.get_new_xref();doc.update_object(xref,'<<>>');doc.update_stream(xref,'\n'.join(parts).encode());doc.xref_set_key(page.xref,'Contents','['+' '.join(f'{x} 0 R' for x in page.get_contents()+[xref])+']')


def flow(base,operations,regions,text,runs,align,line_height,auto_fit,min_size):
    if not isinstance(text,str) or not text.strip() or len(text)>12000 or any((ord(c)<32 and c!='\n') or ord(c)==127 or unicodedata.bidirectional(c) in {'R','AL','AN'} for c in text):raise DocumentError('Usa hasta 12000 caracteres, sin controles ni escritura RTL.')
    if type(align) is not int or align not in range(4) or not finite(line_height) or not 1<=line_height<=2.5 or type(auto_fit) is not bool or not finite(min_size) or not 6<=min_size<=72:raise DocumentError('Formato de flujo original no válido.')
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,operations)) as doc:
        rows,rotations=regions_model(doc,regions);source=collect(doc,rows)
        if not isinstance(runs,list) or len(runs)!=len(source) or any(not isinstance(r,dict) or set(r)!={'id','text'} or not isinstance(r['id'],str) or not isinstance(r['text'],str) for r in runs):raise DocumentError('Revisa los identificadores y textos de todos los fragmentos originales.')
        if [r['id'] for r in runs]!=[r['id'] for r in source] or ''.join(r['text'] for r in runs)!=text:raise DocumentError('El orden, los fragmentos originales y el texto completo no coinciden.')
        parsed=[{**row,'text':run['text']} for row,run in zip(source,runs)]
        smallest=min(r['size'] for r in parsed);largest=max(r['size'] for r in parsed)
        if auto_fit and min_size>smallest:raise DocumentError('El mínimo supera el menor tamaño original.')
        minimum=min_size/smallest;scales=[1.]
        if auto_fit:scales += [round(1-i*.025,6) for i in range(1,math.floor((1-minimum)/.025)+1)]+[minimum]
        for scale in dict.fromkeys(scales):
            try:draws,details,consumed=layout_mixed(doc,rows,text,parsed,scale,align,line_height,next_line)
            except DocumentError:
                if auto_fit:continue
                raise
            if consumed==len(text):break
        else:raise DocumentError('El texto no cabe completo en las regiones. Amplía el espacio o activa el ajuste proporcional.')
        for number in rotations:
            page=doc[number];replaced=[r for r in rows if r['page']==number and r['replace']]
            if replaced:
                clone_resources(doc,page)
                for row in replaced:page.add_redact_annot(row['rect'],fill=False,cross_out=False)
                page.apply_redactions(images=0,graphics=0,text=0);page.wrap_contents()
        write_draws(doc,draws)
        for number,rotation in rotations.items():doc[number].set_rotation(rotation)
        data=doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
    with open_pdf(data) as check:
        for number in rotations:check[number].set_rotation(0)
        actual=''
        for row in rows:
            page=check[row['page']];actual+=page.get_text(clip=row['rect'],sort=False)
            for block in page.get_text('dict',clip=row['rect'])['blocks']:
                for line in block.get('lines',[]):
                    for span in line['spans']:
                        if not (row['rect']+(-.02,-.02,.02,.02)).contains(f.Rect(span['bbox'])):raise DocumentError('El texto excede una región. No se entrega un flujo recortado.')
        clean=lambda v:re.sub(r'\s+','',v)
        if clean(actual)!=clean(text):raise DocumentError('La comprobación del texto original detectó diferencias. No se aplicó el cambio.')
    mixed={'scale':scale,'adjusted':scale!=1,'min_size':smallest*scale,'max_size':largest*scale,'fragments':len(runs)}
    return data,{'mode':'original','mixed':mixed,'text_verified':True,'size':None,'requested_size':None,'adjusted':scale!=1,'characters':len(text),'regions':details,'pages':sorted(rotations),'complete':True}
