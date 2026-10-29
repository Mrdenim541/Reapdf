"""Mixed paragraphs reusing validated original resources, sizes and colors."""
import re,unicodedata
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError
from .document_tools import editable
from .paragraphs import prepare_text_page
from .styled_text import styled_model,clone_resources
from .text_flow import next_line


def source_runs(doc,number,box):
    from .original_reflow import compatible_page
    compatible_page(doc,doc[number]);rect,rows=styled_model(doc,number,box)
    if any(r.get('transformed') for r in rows):raise DocumentError('El reflujo no cambia la matriz del texto. Edita su línea con la fuente original.')
    if not rows or any(not r['editable'] for r in rows):raise DocumentError('Algún fragmento no permite conservar su fuente original.')
    if any(r.get('_spacing',{}).get('state',{}).get('scale',100)!=100 for r in rows):raise DocumentError('El reflujo de fragmentos escalados todavía no es compatible.')
    return rect,rows


def public_runs(rows):
    result=[]
    for i,row in enumerate(rows):
        # Explicit paragraph mode joins original visual line breaks. Users can
        # retain/add a hard break in the text of a selected style fragment.
        separator=' ' if i+1<len(rows) and abs(rows[i+1]['origin'][1]-row['origin'][1])>.3 else ''
        result.append({'id':row['id'],'text':row['text']+separator,'font':row['font'],'size':row['size'],'color':row['color']})
    return result


def reflow(base,ops,number,box,text,runs,preview=False,source_box=None):
    if not isinstance(text,str) or not text.strip() or len(text)>4000 or any((ord(c)<32 and c!='\n') or ord(c)==127 or unicodedata.bidirectional(c) in {'R','AL','AN'} for c in text):raise DocumentError('Usa hasta 4000 caracteres cubiertos por las fuentes originales, sin controles ni escritura RTL.')
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,ops)) as doc:
        page,rotation=prepare_text_page(doc,number);rect,rows=source_runs(doc,number,box);by_id={r['id']:r for r in rows}
        if source_box is not None:
            source_rect,original=source_runs(doc,number,source_box)
            if not rect.contains(source_rect) or set(by_id)!={r['id'] for r in original}:raise DocumentError('El área corta el bloque o cruza otro texto.')
        if not isinstance(runs,list) or len(runs)!=len(rows):raise DocumentError('Revisa todos los fragmentos originales del párrafo.')
        if any(not isinstance(r,dict) or set(r)!={'id','text'} or not isinstance(r['id'],str) or not isinstance(r['text'],str) for r in runs):raise DocumentError('Cada fragmento necesita su identificador y texto.')
        if [r['id'] for r in runs]!=[r['id'] for r in rows] or ''.join(r['text'] for r in runs)!=text:raise DocumentError('Los fragmentos, su orden y el texto completo no coinciden.')
        if any(((f.Rect(d['rect'])+(-.5,-.5,.5,.5))&rect).get_area()>.1 for d in page.get_drawings()) or any((f.Rect(l['from'])&rect).get_area()>.1 for l in page.get_links()):raise DocumentError('El área cruza dibujos, bordes o enlaces.')
        styles=[];prefix=[0.]
        for run in runs:
            row=by_id[run['id']]
            for char in run['text']:
                prefix.append(prefix[-1]+(0 if char=='\n' else row['_font'].encode(char,row['size'])[1]));styles.append(row)
        cursor=0;top=rect.y0+2;draws=[];line_count=0
        while cursor<len(text):
            before=cursor;line,after,_=next_line(text,cursor,rect.width-4,prefix);group=styles[before:before+max(1,len(line))]
            ascent=max(r['origin'][1]-r['bbox'][1] for r in group);descent=max(r['bbox'][3]-r['origin'][1] for r in group);size=max(r['size'] for r in group)
            if top+ascent+descent>rect.y1-2+.01:raise DocumentError('El párrafo con varios estilos no cabe completo. Amplía el área.')
            baseline=top+ascent;offset=0;x=rect.x0+2
            while offset<len(line):
                row=styles[before+offset];end=offset+1
                while end<len(line) and styles[before+end] is row:end+=1
                fragment=line[offset:end]
                if fragment:draws.append((row,fragment,f.Point(x,baseline)))
                x+=prefix[before+end]-prefix[before+offset];offset=end
            line_count+=1;top+=max(size*1.35,ascent+descent);cursor=after
        report={'mode':'mixed-original','lines':line_count,'fragments':len(runs),'fonts':sorted({r['font'] for r in rows}),'font':' · '.join(sorted({r['font'] for r in rows})),'box':list(rect)}
        if preview:return report
        clone_resources(doc,page)
        for row in rows:page.add_redact_annot(f.Rect(row['bbox']),fill=False,cross_out=False)
        page.apply_redactions(images=0,graphics=0,text=0);page.wrap_contents();resources=clone_resources(doc,page);aliases={};snippets=[]
        for row,fragment,point in draws:
            font=row['_font'];key=font.xref
            if key not in aliases:
                alias='ReapdfMixedOriginal'+str(len(aliases)+1)
                while doc.xref_get_key(resources,alias)[0]!='null':alias+='x'
                doc.xref_set_key(resources,alias,f'{key} 0 R');aliases[key]=alias
            point=point*~page.transformation_matrix;color=[((row['color']>>v)&255)/255 for v in [16,8,0]];encoded=font.encode(fragment,row['size'])[0]
            snippets.append(f"q BT 0 Tc 0 Tw 100 Tz 0 Tr 0 Ts /{aliases[key]} {row['size']:.8f} Tf {' '.join(str(v) for v in color)} rg 1 0 0 1 {point.x:.8f} {point.y:.8f} Tm <{encoded.hex()}> Tj ET Q")
        xref=doc.get_new_xref();doc.update_object(xref,'<<>>');doc.update_stream(xref,'\n'.join(snippets).encode());doc.xref_set_key(page.xref,'Contents','['+' '.join(f'{x} 0 R' for x in page.get_contents()+[xref])+']');page.set_rotation(rotation);data=doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
    with open_pdf(data) as check:
        check[number].set_rotation(0);clean=lambda v:re.sub(r'\s+','',v)
        if clean(check[number].get_text(clip=rect,sort=True))!=clean(text):raise DocumentError('La comprobación del texto mixto detectó diferencias. No se publicó el cambio.')
    return data,report
