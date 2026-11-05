"""Reflow common-baseline mixed styles, retaining each original affine transform."""
from .engine import pdf_garbage
import copy,math,unicodedata
from collections import Counter,defaultdict
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError,finite
from .document_tools import editable
from .native_text import native_model
from .affine_text import polygon,rectangle,contains,overlap,bounds
from .mixed_spacing import Layout,operand


def path_key(row):
    return tuple((s['owner'],s['target'],s['start'],s['end']) for s in row['_native_path'])


def object_key(row):return (path_key(row),row['_text_object'])


def complete_objects(rows,all_rows):
    objects={object_key(r) for r in rows}
    return {r['id'] for r in all_rows if object_key(r) in objects}=={r['id'] for r in rows}


def compatible(rows,sort=True,across_paths=False):
    if not rows or any(not r['editable'] or r['original_only'] for r in rows):raise DocumentError('El párrafo mixto necesita grupos visibles sin composición especial.')
    first=rows[0];frame=f.Matrix(*first['_geometry']['matrix']);inverse=~frame
    from .sheared_paragraph import compatible as compatible_shear
    for r in rows:
        if (not across_paths and r['_native_path']!=first['_native_path']) or not compatible_shear(first,r):raise DocumentError('Los estilos deben compartir dirección de lectura y orientación vertical; las rutas distintas necesitan selección explícita.')
    ordered=sorted(rows,key=lambda r:(-round((f.Point(r['origin'])*inverse).y,2),(f.Point(r['origin'])*inverse).x))
    return ordered if sort else rows


def inspect_rows(rows,continuous=True):
    rows=compatible(rows,sort=continuous,across_paths=not continuous);first=rows[0];inverse=~f.Matrix(*first['_geometry']['matrix']);positions=[f.Point(r['origin'])*inverse for r in rows]
    if abs(positions[0].x)>.5:raise DocumentError('El párrafo no empieza en el marco seleccionado.')
    from .sheared_paragraph import distinct,ShearedLayout,join_gap,overhang
    variable=distinct(rows)
    for i,(a,b) in enumerate(zip(positions,positions[1:])) if continuous else []:
        if abs(a.y-b.y)<.3:
            if min(abs(b.x-a.x-rows[i]['_geometry']['width']),abs(b.x-a.x-rows[i]['_geometry']['width']-(join_gap(first,rows[i],rows[i+1]) if variable else 0)))>.5:raise DocumentError('Los estilos no forman una línea continua.')
        elif min(abs(b.x),abs(b.x+overhang(first,rows[i+1])[0]) if variable else abs(b.x))>.5 or not .5*max(rows[i]['size'],rows[i+1]['size'])<=a.y-b.y<=3*max(rows[i]['size'],rows[i+1]['size']):raise DocumentError('Los estilos no forman líneas continuas.')
    rect=f.Rect(rows[0]['bbox'])
    for r in rows[1:]:rect|=f.Rect(r['bbox'])
    runs=[]
    for i,r in enumerate(rows):
        separator=' ' if i+1<len(rows) and abs(positions[i+1].y-positions[i].y)>.3 else ''
        if not continuous:
            separated=i+1<len(rows) and (abs(positions[i+1].y-positions[i].y)>.3 or abs(positions[i+1].x-positions[i].x-r['_geometry']['width'])>.5)
            separator=' ' if separated and not r['text'].endswith((' ','\n')) and not rows[i+1]['text'].startswith((' ','\n')) else ''
        runs.append({'id':r['id'],'text':r['text']+separator,'font':r['font'],'size':r['size'],'color':r['color']})
    packed_width=0.
    if variable:
        layout=ShearedLayout(rows,runs)
        start=0;line_start=0
        for i,run in enumerate(runs):
            start+=len(run['text'])
            if i==len(runs)-1 or abs(positions[i+1].y-positions[i].y)>.3:
                packed_width=max(packed_width,layout.pack(line_start,start)[0]);line_start=start
    top=max(p.y+r['_geometry']['ascent'] for p,r in zip(positions,rows));bottom=min(p.y+r['_geometry']['descent'] for p,r in zip(positions,rows))
    return {'affine':True,'mixed':True,'variable_shear':variable,'ids':[r['id'] for r in rows],'runs':runs,'text':''.join(r['text'] for r in runs),'font':' · '.join(sorted({r['font'] for r in rows})),'box':[rect.x0,rect.y0,rect.width,rect.height],'original_available':True,'reason':'','local_width':max(10,packed_width+.5,max(p.x+r['_geometry']['width'] for p,r in zip(positions,rows))+.5),'local_height':max(10,top-bottom+.5)}


def stable_key(row):
    return (row['text'],row['font'],round(row['size'],3),row['color'],row['alpha'],tuple(round(v,2) for v in row['origin']),tuple(round(v,2) for v in row['bbox']))


def verify_fragments(data,prepared,number):
    from .styled_text import normal_name
    from .native_text import matching_traces
    from .type3_text import merge_lines,trace as type3_trace
    with open_pdf(data) as doc:
        page=doc[number];page.set_rotation(0);traces=page.get_texttrace()
        blocks=merge_lines(doc,page,page.get_text('rawdict',flags=f.TEXTFLAGS_TEXT)['blocks']);index=defaultdict(list)
        for block in blocks:
            for line in block.get('lines',[]):
                for span in line['spans']:
                    font=normal_name(span['font'])
                    for i,char in enumerate(span['chars']):
                        x,y=char['origin']
                        if finite(x) and finite(y):index[(font,char['c'],math.floor(x*10),math.floor(y*10))].append((span,i))
        for row,_ in prepared:
            text=row['_replacement_text'];font=normal_name(row['font']);x,y=row['origin'];matches=[]
            for dx in [-1,0,1]:
                for dy in [-1,0,1]:
                    for span,i in index.get((font,text[0],math.floor(x*10)+dx,math.floor(y*10)+dy),[]):
                        chars=span['chars'][i:i+len(text)]
                        if len(chars)!=len(text) or ''.join(c['c'] for c in chars)!=text or math.dist(chars[0]['origin'],row['origin'])>.02:continue
                        rect=f.Rect(chars[0]['bbox'])
                        for char in chars[1:]:rect|=f.Rect(char['bbox'])
                        matches.append({**span,'origin':chars[0]['origin'],'chars':chars,'bbox':list(rect),'text':text})
            if len(matches)!=1:raise DocumentError('La comprobación del texto mixto detectó diferencias. No se publicó el párrafo.')
            span=matches[0];expected=bounds(polygon(row['_geometry'],row['_replacement_width']))
            if max(abs(a-b) for a,b in zip(expected,span['bbox']))>.3 or abs(span['size']-row['display_size'])>.02 or span['color']!=row['color'] or span.get('alpha',255)!=row['alpha']:raise DocumentError('La geometría o el estilo del texto mixto cambió al guardar.')
            appearances=matching_traces(traces,text,row['origin'])
            if row['_font'].type=='Type3':
                checked=type3_trace(row['_font'],span,traces);appearances=[checked] if checked else []
            if len(appearances)!=1 or appearances[0]['type']!=0 or abs(appearances[0]['opacity']-row['opacity'])>1e-6:raise DocumentError('La apariencia del texto mixto no se pudo verificar.')


def reflow(base,ops,number,box,identifier,text,width,height,preview,identifiers,runs,explicit_order=False,continuations=None,paginate=False):
    if type(paginate) is not bool:raise DocumentError('La paginación automática debe ser verdadera o falsa.')
    if paginate and continuations is not None:raise DocumentError('Elige continuación manual o páginas nuevas automáticas, no ambas.')
    if type(explicit_order) is not bool:raise DocumentError('El orden explícito debe ser verdadero o falso.')
    if not isinstance(text,str) or not text.strip() or len(text)>4000 or any((ord(c)<32 and c!='\n') or ord(c)==127 or unicodedata.bidirectional(c) in {'R','AL','AN'} for c in text):raise DocumentError('Usa hasta 4000 caracteres compatibles y sin controles o escritura RTL.')
    if type(number) is not int or not finite(width) or not finite(height) or not 10<=width<=2000 or not 10<=height<=2000:raise DocumentError('Página, ancho o alto del párrafo no válidos.')
    if not isinstance(identifiers,list) or not 1<=len(identifiers)<=100 or any(not isinstance(i,str) for i in identifiers) or len(set(identifiers))!=len(identifiers) or identifiers[0]!=identifier:raise DocumentError('Selecciona todos los grupos del párrafo en orden.')
    requested_width,requested_height=width,height
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,ops)) as doc:
        if not 0<=number<len(doc):raise DocumentError('Página no válida.')
        from .tagged_text_integrity import snapshot as semantic_snapshot
        semantic=semantic_snapshot(doc,number);tagged=None
        if not isinstance(box,list) or len(box)!=4 or any(not finite(v) for v in box) or box[2]<=0 or box[3]<=0:raise DocumentError('Región no válida.')
        page=doc[number];rotation=page.rotation;page.set_rotation(0);page_size=(page.rect.width,page.rect.height);original_pages=len(doc);region=f.Rect(box[0],box[1],box[0]+box[2],box[1]+box[3]);_,all_rows=native_model(doc,number,page.rect,context=True)
        if paginate and (doc.get_ocgs() or min(page_size)<=92):raise DocumentError('La paginación automática necesita páginas sin capas y espacio para márgenes de 36 pt.')
        chosen={r['id']:r for r in all_rows if r['id'] in identifiers}
        if len(chosen)!=len(identifiers):raise DocumentError('La selección de grupos está obsoleta.')
        if semantic is not None:
            from .tagged_paragraph import Paragraph
            tagged=Paragraph(doc,number,all_rows,chosen[identifier]);tagged.validate([chosen[i] for i in identifiers])
        rows=compatible([chosen[i] for i in identifiers],sort=not (explicit_order or tagged),across_paths=explicit_order);first=rows[0]
        if [r['id'] for r in rows]!=identifiers or any(not (region+(-.1,-.1,.1,.1)).contains(f.Rect(r['bbox'])) for r in rows):raise DocumentError('La región corta el párrafo o cambia su orden.')
        objects={object_key(r) for r in rows}
        if not complete_objects(rows,all_rows):raise DocumentError('Selecciona completos los objetos de texto para conservar su estado.')
        if not isinstance(runs,list) or len(runs)!=len(rows) or any(not isinstance(r,dict) or set(r)!={'id','text'} or not isinstance(r['text'],str) for r in runs) or [r['id'] for r in runs]!=identifiers or ''.join(r['text'] for r in runs)!=text:raise DocumentError('Los estilos, identificadores y texto completo no coinciden.')
        from .sheared_paragraph import distinct,ShearedLayout
        variable=distinct(rows);layout=ShearedLayout(rows,runs) if variable else Layout(rows,runs);styles=layout.styles
        obstacles=[clip for r in rows for clip in r['_obstacles']]+[rectangle(l['from']) for l in page.get_links()]+[rectangle(f.Rect(d['rect'])+(-.5,-.5,.5,.5)) for d in page.get_drawings()]
        untouched=[r for r in all_rows if r['id'] not in identifiers];obstacles +=[r['quad'] or rectangle(f.Rect(r['bbox'])) for r in untouched]
        original_untouched=Counter(stable_key(r) for r in untouched)
        from .native_continuation import regions as continuation_regions,append as append_continuations
        destinations,rotations=continuation_regions(doc,number,continuations,first['_geometry']['matrix']);rotations[number]=rotation
        untouched_by_page={number:original_untouched}
        for n in rotations:
            if n!=number:
                native=native_model(doc,n,doc[n].rect,context=True)[1] if doc[n].get_text().strip() else [];untouched_by_page[n]=Counter(stable_key(r) for r in native)
        frame=f.Matrix(*first['_geometry']['matrix']);inverse=~frame;top=max((f.Point(r['origin'])*inverse).y+r['_geometry']['ascent'] for r in rows);commands={r['id']:[] for r in rows};prepared=[];cursor=0;used=0.;lines=0;destination=-1;current=number;draws=[];details=[{'page':number,'lines':0,'characters':0}]
        while cursor<len(text):
            line,after,_=layout.line(text,cursor,width);group=styles[cursor:cursor+max(1,len(line))];ascent=max(r['_geometry']['ascent'] for r in group);descent=min(r['_geometry']['descent'] for r in group);size=max(r['size'] for r in group)
            if used+ascent-descent>height+.01:
                if destination<0 and (destinations or paginate) and not lines:raise DocumentError('El alto inicial no permite una línea. Amplía el área inicial; se conserva el borrador.')
                if destination+1>=len(destinations) and paginate:
                    if len(doc)-original_pages>=16:raise DocumentError('El párrafo supera el límite de 16 páginas nuevas; no se publica texto parcial.')
                    added=doc.new_page(width=page_size[0],height=page_size[1]);n=added.number
                    extra,_=continuation_regions(doc,number,[{'page':n,'box':[36,36,page_size[0]-72,page_size[1]-72]}],first['_geometry']['matrix'])
                    destinations.extend(extra);rotations[n]=rotation;untouched_by_page[n]=Counter()
                    # Adding pages invalidates previously acquired Page handles.
                    page=doc[number]
                if destination+1>=len(destinations):raise DocumentError('El párrafo mixto no cabe completo. Amplía el alto o añade otra continuación; se conserva el borrador.')
                destination+=1;target=destinations[destination];current=target['page'];frame=target['frame'];top=0.;used=0.;width=target['width'];height=target['height'];details.append({'page':current,'lines':0,'characters':0});continue
            baseline=top-used-ascent;offset=0;x=0.;packed=layout.pack(cursor,cursor+len(line))[1] if variable else {}
            while offset<len(line):
                row=styles[cursor+offset];end=offset+1
                while end<len(line) and styles[cursor+end] is row:end+=1
                if variable:x=packed[offset]
                fragment=line[offset:end];extent=layout.extent(cursor+offset,cursor+end);g=copy.copy(row['_geometry']);origin=f.Point(x,baseline)*frame;g['matrix']=[*g['matrix'][:4],origin.x,origin.y];cell=polygon(g,extent)
                if not contains(rectangle(doc[current].rect),cell) or (destination<0 and any(not contains(c,cell) for c in row['_clips'])) or (destination>=0 and not contains(rectangle(destinations[destination]['rect']),cell)):raise DocumentError('El párrafo sale de la página o del recorte original.')
                if destination<0 and any(overlap(cell,o)>.1 for o in obstacles):raise DocumentError('El párrafo cruza otro texto, imagen, borde, enlace o anotación.')
                if destination<0:
                    local=origin*~f.Matrix(*row['_geometry']['matrix']);tm=f.Matrix(*row['_line_matrix']);position=f.Point(local.x/(g['factor']*g['horizontal']),local.y/g['factor'])*tm;tm[4]=position.x;tm[5]=position.y
                    command=(' '.join(f'{v:.8f}' for v in tm)+' Tm ').encode()+operand(row['_font'],fragment,layout.kern[cursor+offset:cursor+end]);commands[row['id']].append(command)
                else:draws.append((current,{**row,'_replacement_kern':layout.kern[cursor+offset:cursor+end]},g,fragment))
                prepared.append((current,({**row,'origin':list(origin),'_geometry':g,'_replacement_text':fragment,'_replacement_width':extent},b'')));x+=layout.prefix[cursor+end]-layout.prefix[cursor+offset];offset=end
            details[-1]['characters']+=after-cursor;details[-1]['lines']+=1;cursor=after;used+=max(size*1.35,ascent-descent);lines+=1
        report={'lines':lines,'font':' · '.join(sorted({r['font'] for r in rows})),'width':requested_width,'height':requested_height,'preserves_affine':True,'variable_shear':variable,'preserves_run_transforms':True,'preserves_spacing':True,'mixed':True,'source_groups':len(rows),'source_objects':len(objects),'source_paths':len({path_key(r) for r in rows}),'regions':details,'pages':sorted(rotations),'complete':True,'automatic_pagination':paginate,'added_pages':len(doc)-original_pages}
        report['tagged_native']=tagged is not None
        if tagged:tagged.extend(draws)
        if preview:return report
        patches=[]
        for row in rows:
            chunks=commands[row['id']];restore=(' '+' '.join(f'{v:.8f}' for v in row['_line_matrix'])+' Tm ').encode();kind=row['_native'][2];tail=restore+(b'[] TJ' if kind=='operator-array' else b'<>' if kind=='string' else b'[]');patches.append((row,b' ET BT '.join(chunks)+tail))
        from .form_text import write
        # Record the intended graph before changing page contents, then verify
        # its identity after serialization. Continuations add markers only on
        # their destination pages; source markers must remain byte-identical.
        expected_semantic=semantic_snapshot(doc,number) if tagged else None
        write(doc,page,patches);append_continuations(doc,draws)
        destination_semantics={n:semantic_snapshot(doc,n) for n in rotations if n!=number} if tagged else {}
        for n,angle in rotations.items():doc[n].set_rotation(angle)
        data=doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=pdf_garbage(doc),deflate=True)
    for n in rotations:verify_fragments(data,[value for page,value in prepared if page==n],n)
    with open_pdf(data) as check:
        if tagged:
            from .tagged_text_integrity import verify as verify_semantic
            verify_semantic(check,number,expected_semantic)
            for n,expected in destination_semantics.items():verify_semantic(check,n,expected)
        for n in rotations:
            check[n].set_rotation(0)
            if not untouched_by_page[n] and not tagged:continue
            _,remaining=native_model(check,n,check[n].rect,context=True)
            if untouched_by_page[n]-Counter(stable_key(r) for r in remaining):raise DocumentError('La comprobación detectó cambios en otro texto. No se publicó el párrafo.')
            if tagged:
                changed=[r for r in remaining if stable_key(r) not in untouched_by_page[n]]
                if changed:
                    from .tagged_paragraph import Paragraph
                    association=Paragraph(check,n,remaining,changed[0])
                    if not {r['id'] for r in changed}<={r['id'] for r in association.rows}:raise DocumentError('El texto guardado perdió su asociación al párrafo etiquetado.')
    return data,report


def inspect_selection(base,ops,number,selection):
    if type(number) is not int or not isinstance(selection,list) or not 1<=len(selection)<=100:raise DocumentError('Selecciona de 1 a 100 textos en una página.')
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,ops)) as doc:
        if not 0<=number<len(doc):raise DocumentError('Página no válida.')
        page=doc[number];page.set_rotation(0)
        _,all_rows=native_model(doc,number,page.rect,context=True);chosen=[]
        for ref in selection:
            if not isinstance(ref,dict) or set(ref)!={'origin','text'} or not isinstance(ref['origin'],list) or len(ref['origin'])!=2 or any(not finite(v) for v in ref['origin']) or not isinstance(ref['text'],str):raise DocumentError('Referencia de selección no válida.')
            matches=[r for r in all_rows if r['origin']==ref['origin'] and r['text']==ref['text']]
            if len(matches)!=1 or matches[0]['id'] in {r['id'] for r in chosen}:raise DocumentError('Selección repetida, ambigua u obsoleta.')
            chosen.append(matches[0])
        rows=compatible(chosen,sort=False,across_paths=True)
        tagged=doc.xref_get_key(doc.pdf_catalog(),'StructTreeRoot')[0]!='null'
        if tagged:
            from .tagged_paragraph import Paragraph
            Paragraph(doc,number,all_rows,rows[0]).validate(rows)
        if not complete_objects(rows,all_rows):raise DocumentError('Selecciona también los otros fragmentos de esos objetos. No se añade texto sin tu selección.')
        result=inspect_rows(rows,continuous=False);result['explicit_selection']=True;result['source_paths']=len({path_key(r) for r in rows})
        if tagged:result.update(tagged_native=True,tagged_paragraph=True,complete_object_selection=True)
        return result
