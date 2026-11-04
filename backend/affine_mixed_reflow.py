"""Reflow parallel original mixed-style text through native operand patches."""
import copy,unicodedata
from collections import Counter
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError,finite
from .document_tools import editable
from .native_text import native_model
from .affine_text import polygon,rectangle,contains,overlap,verify
from .text_flow import next_line


def compatible(rows):
    if not rows or any(not r['editable'] or r['original_only'] for r in rows):raise DocumentError('El párrafo mixto necesita grupos visibles sin composición especial.')
    first=rows[0];frame=f.Matrix(*first['_geometry']['matrix']);inverse=~frame
    for r in rows:
        if r['_native_path']!=first['_native_path'] or r['_text_object']!=first['_text_object'] or max(abs(a-b) for a,b in zip(r['_geometry']['matrix'][:4],first['_geometry']['matrix'][:4]))>1e-4:raise DocumentError('Los estilos deben compartir objeto y transformación paralela.')
        state=r['_spacing']['state']
        if state['char']!=0 or state['word']!=0:raise DocumentError('El párrafo usa espaciado especial que aún no puede redistribuirse conservando sus estilos.')
    ordered=sorted(rows,key=lambda r:(-round((f.Point(r['origin'])*inverse).y,2),(f.Point(r['origin'])*inverse).x))
    return ordered


def inspect_rows(rows):
    rows=compatible(rows);first=rows[0];inverse=~f.Matrix(*first['_geometry']['matrix']);positions=[f.Point(r['origin'])*inverse for r in rows]
    if abs(positions[0].x)>.5:raise DocumentError('El párrafo no empieza en el marco seleccionado.')
    for i,(a,b) in enumerate(zip(positions,positions[1:])):
        if abs(a.y-b.y)<.3:
            if abs(b.x-a.x-rows[i]['_geometry']['width'])>.5:raise DocumentError('Los estilos no forman una línea continua.')
        elif abs(b.x)>.5 or not .5*max(rows[i]['size'],rows[i+1]['size'])<=a.y-b.y<=3*max(rows[i]['size'],rows[i+1]['size']):raise DocumentError('Los estilos no forman líneas continuas.')
    rect=f.Rect(rows[0]['bbox'])
    for r in rows[1:]:rect|=f.Rect(r['bbox'])
    runs=[]
    for i,r in enumerate(rows):
        separator=' ' if i+1<len(rows) and abs(positions[i+1].y-positions[i].y)>.3 else ''
        runs.append({'id':r['id'],'text':r['text']+separator,'font':r['font'],'size':r['size'],'color':r['color']})
    top=max(p.y+r['_geometry']['ascent'] for p,r in zip(positions,rows));bottom=min(p.y+r['_geometry']['descent'] for p,r in zip(positions,rows))
    return {'affine':True,'mixed':True,'ids':[r['id'] for r in rows],'runs':runs,'text':''.join(r['text'] for r in runs),'font':' · '.join(sorted({r['font'] for r in rows})),'box':[rect.x0,rect.y0,rect.width,rect.height],'original_available':True,'reason':'','local_width':max(10,max(p.x+r['_geometry']['width'] for p,r in zip(positions,rows))+.5),'local_height':max(10,top-bottom+.5)}


def stable_key(row):
    return (row['text'],row['font'],round(row['size'],3),row['color'],row['alpha'],tuple(round(v,2) for v in row['origin']),tuple(round(v,2) for v in row['bbox']))


def reflow(base,ops,number,box,identifier,text,width,height,preview,identifiers,runs):
    if not isinstance(text,str) or not text.strip() or len(text)>4000 or any((ord(c)<32 and c!='\n') or ord(c)==127 or unicodedata.bidirectional(c) in {'R','AL','AN'} for c in text):raise DocumentError('Usa hasta 4000 caracteres compatibles y sin controles o escritura RTL.')
    if type(number) is not int or not finite(width) or not finite(height) or not 10<=width<=2000 or not 10<=height<=2000:raise DocumentError('Página, ancho o alto del párrafo no válidos.')
    if not isinstance(identifiers,list) or not 1<=len(identifiers)<=100 or any(not isinstance(i,str) for i in identifiers) or len(set(identifiers))!=len(identifiers) or identifiers[0]!=identifier:raise DocumentError('Selecciona todos los grupos del párrafo en orden.')
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,ops)) as doc:
        if not 0<=number<len(doc):raise DocumentError('Página no válida.')
        if doc.xref_get_key(doc.pdf_catalog(),'StructTreeRoot')[0]!='null':raise DocumentError('El reflujo mixto afín de texto etiquetado requiere revisión estructural.')
        if not isinstance(box,list) or len(box)!=4 or any(not finite(v) for v in box) or box[2]<=0 or box[3]<=0:raise DocumentError('Región no válida.')
        page=doc[number];rotation=page.rotation;page.set_rotation(0);region=f.Rect(box[0],box[1],box[0]+box[2],box[1]+box[3]);_,all_rows=native_model(doc,number,page.rect)
        chosen={r['id']:r for r in all_rows if r['id'] in identifiers}
        if len(chosen)!=len(identifiers):raise DocumentError('La selección de grupos está obsoleta.')
        rows=compatible([chosen[i] for i in identifiers]);first=rows[0]
        if [r['id'] for r in rows]!=identifiers or any(not (region+(-.1,-.1,.1,.1)).contains(f.Rect(r['bbox'])) for r in rows):raise DocumentError('La región corta el párrafo o cambia su orden.')
        full=[r for r in all_rows if r['_text_object']==first['_text_object'] and r['_native_path']==first['_native_path']]
        if {r['id'] for r in full}!=set(identifiers):raise DocumentError('Selecciona el objeto de texto completo para conservar su estado.')
        if not isinstance(runs,list) or len(runs)!=len(rows) or any(not isinstance(r,dict) or set(r)!={'id','text'} or not isinstance(r['text'],str) for r in runs) or [r['id'] for r in runs]!=identifiers or ''.join(r['text'] for r in runs)!=text:raise DocumentError('Los estilos, identificadores y texto completo no coinciden.')
        styles=[];prefix=[0.]
        for run,row in zip(runs,rows):
            for char in run['text']:
                styles.append(row);prefix.append(prefix[-1]+(0 if char=='\n' else row['_font'].encode(char,row['size'])[1]*row['_spacing']['state']['scale']/100))
        obstacles=[clip for r in rows for clip in r['_obstacles']]+[rectangle(l['from']) for l in page.get_links()]+[rectangle(f.Rect(d['rect'])+(-.5,-.5,.5,.5)) for d in page.get_drawings()]
        untouched=[r for r in all_rows if r['id'] not in identifiers];obstacles +=[r['quad'] or rectangle(f.Rect(r['bbox'])) for r in untouched]
        original_untouched=Counter(stable_key(r) for r in untouched)
        frame=f.Matrix(*first['_geometry']['matrix']);inverse=~frame;top=max((f.Point(r['origin'])*inverse).y+r['_geometry']['ascent'] for r in rows);commands={r['id']:[] for r in rows};prepared=[];cursor=0;used=0.;lines=0
        while cursor<len(text):
            line,after,_=next_line(text,cursor,width,prefix);group=styles[cursor:cursor+max(1,len(line))];ascent=max(r['_geometry']['ascent'] for r in group);descent=min(r['_geometry']['descent'] for r in group);size=max(r['size'] for r in group)
            if used+ascent-descent>height+.01:raise DocumentError('El párrafo mixto no cabe completo. Amplía el alto; se conserva el borrador.')
            baseline=top-used-ascent;offset=0;x=0.
            while offset<len(line):
                row=styles[cursor+offset];end=offset+1
                while end<len(line) and styles[cursor+end] is row:end+=1
                fragment=line[offset:end];extent=prefix[cursor+end]-prefix[cursor+offset];g=copy.copy(row['_geometry']);origin=f.Point(x,baseline)*frame;g['matrix']=[*g['matrix'][:4],origin.x,origin.y];cell=polygon(g,extent)
                if not contains(rectangle(page.rect),cell) or any(not contains(c,cell) for c in row['_clips']):raise DocumentError('El párrafo sale de la página o del recorte original.')
                if any(overlap(cell,o)>.1 for o in obstacles):raise DocumentError('El párrafo cruza otro texto, imagen, borde, enlace o anotación.')
                local=origin*~f.Matrix(*row['_geometry']['matrix']);tm=f.Matrix(*row['_line_matrix']);position=f.Point(local.x/(g['factor']*g['horizontal']),local.y/g['factor'])*tm;tm[4]=position.x;tm[5]=position.y
                encoded=row['_font'].encode(fragment,row['size'])[0];command=(' '.join(f'{v:.8f}' for v in tm)+' Tm <'+encoded.hex()+'> Tj').encode();commands[row['id']].append(command)
                prepared.append(({**row,'origin':list(origin),'_geometry':g,'_replacement_text':fragment,'_replacement_width':extent},b''));x+=extent;offset=end
            cursor=after;used+=max(size*1.35,ascent-descent);lines+=1
        report={'lines':lines,'font':' · '.join(sorted({r['font'] for r in rows})),'width':width,'height':height,'preserves_affine':True,'mixed':True,'source_groups':len(rows)}
        if preview:return report
        patches=[]
        for row in rows:
            chunks=commands[row['id']];restore=(' '+' '.join(f'{v:.8f}' for v in row['_line_matrix'])+' Tm ').encode();kind=row['_native'][2];tail=restore+(b'[] TJ' if kind=='operator-array' else b'<>' if kind=='string' else b'[]');patches.append((row,b' ET BT '.join(chunks)+tail))
        from .form_text import write
        write(doc,page,patches);page.set_rotation(rotation);data=doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
    verify(data,{number:prepared})
    with open_pdf(data) as check:
        check[number].set_rotation(0);_,remaining=native_model(check,number,check[number].rect)
        if original_untouched-Counter(stable_key(r) for r in remaining):raise DocumentError('La comprobación detectó cambios en otro texto. No se publicó el párrafo.')
    return data,report
