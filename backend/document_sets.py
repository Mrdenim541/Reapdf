"""Portable, hash-bound document sets with explicit, reviewable PDF anchors."""
from collections import defaultdict
from hashlib import sha256
from io import BytesIO
import json
import re
from zipfile import ZipFile,ZIP_DEFLATED,BadZipFile
import pymupdf as f
from .engine import DocumentError,open_pdf,finite

MAX_SET=60*1024*1024
CODE=re.compile(r'(?<![A-Z0-9./-])[A-Z0-9]+(?:[-./][A-Z0-9]+){1,7}(?![A-Z0-9./-])')
ID=re.compile(r'[0-9a-f]{32}\Z')


def digest(data):return sha256(data).hexdigest()

def text(value,limit):
    if not isinstance(value,str) or not 1<=len(value.strip())<=limit or any(ord(c)<32 for c in value):raise DocumentError('Nombre, función o identificador no válido.')
    return value.strip()


def documents(items):
    if not isinstance(items,list) or not 1<=len(items)<=10:raise DocumentError('El conjunto admite de 1 a 10 documentos.')
    total=0;pages=0;seen=set()
    for item in items:
        if not isinstance(item,dict) or set(item)!={'id','name','role','sha256','data'}:raise DocumentError('Documento del conjunto incompleto.')
        if not isinstance(item['id'],str) or not ID.fullmatch(item['id']) or item['id'] in seen:raise DocumentError('Identidad de documento no válida o repetida.')
        seen.add(item['id']);text(item['name'],200);text(item['role'],60)
        if not isinstance(item['data'],bytes) or digest(item['data'])!=item['sha256']:raise DocumentError('El archivo cambió; vuelve a incorporarlo al conjunto.')
        total+=len(item['data'])
        if len(item['data'])>30*1024*1024 or total>MAX_SET:raise DocumentError('Hasta 30 MB por PDF y 60 MB en el conjunto.')
        with open_pdf(item['data']) as doc:
            if not doc.permissions&f.PDF_PERM_COPY:raise DocumentError('Un documento no permite extraer identificadores ni guardarlo en el conjunto.')
            pages+=len(doc)
            if pages>1000:raise DocumentError('Hasta 1000 páginas en todo el conjunto.')
    return items


def normalized(value):
    result=''
    for char in value:
        char='-' if char in '‐‑‒–—−' else char.upper()
        result+=char if len(char)==1 else ' '
    return result


def index(item,codes=None):
    result=defaultdict(list);characters=0;count=0
    regex=None
    if codes:
        if not isinstance(codes,list) or len(codes)>200:raise DocumentError('Hasta 200 identificadores explícitos.')
        values=[normalized(text(c,80)) for c in codes]
        if any(not re.fullmatch(r'[A-Z0-9][A-Z0-9./-]{0,79}',c) for c in values):raise DocumentError('Usa identificadores alfanuméricos, guiones, puntos o barras.')
        regex=re.compile(r'(?<![A-Z0-9./-])(?:'+'|'.join(re.escape(c) for c in sorted(set(values),key=len,reverse=True))+r')(?![A-Z0-9./-])')
    with open_pdf(item['data']) as doc:
        for number,page in enumerate(doc):
            for block in page.get_text('rawdict',sort=True,flags=f.TEXTFLAGS_TEXT)['blocks']:
                for line in block.get('lines',[]):
                    chars=[];previous=None
                    for span in line['spans']:
                        if previous is not None and (span['bbox'][0]-previous['bbox'][2]>.5 or abs(span['origin'][1]-previous['origin'][1])>.3):chars.append({'c':' ','bbox':span['bbox']})
                        for char in span['chars']:
                            chars.extend({**char,'c':c} for c in char['c'])
                        previous=span
                    value=normalized(''.join(c['c'] for c in chars));characters+=len(chars)
                    if characters>2_000_000:raise DocumentError('Un documento supera dos millones de caracteres; divide el conjunto.')
                    for hit in (regex or CODE).finditer(value):
                        code=hit[0]
                        if len(code)>80 or not regex and re.fullmatch(r'\d{1,4}/\d{1,2}/\d{1,4}',code):continue
                        rect=f.Rect(chars[hit.start()]['bbox'])
                        for char in chars[hit.start()+1:hit.end()]:rect|=f.Rect(char['bbox'])
                        rect=rect*page.rotation_matrix
                        coordinates=[round(v,4) for v in rect]
                        identity=digest(json.dumps([item['sha256'],number,coordinates,code]).encode())[:24]
                        result[code].append({'id':identity,'document':item['id'],'page':number,'rect':coordinates,'code':code})
                        count+=1
                        if count>20000:raise DocumentError('Demasiadas apariciones de identificadores; limita los códigos o divide el conjunto.')
    return dict(result)


def analyze(items,source,target,codes=None):
    documents(items);by_id={i['id']:i for i in items}
    if not isinstance(source,str) or not isinstance(target,str) or source not in by_id or target not in by_id or source==target:raise DocumentError('Selecciona dos documentos distintos como origen y destino.')
    a=index(by_id[source],codes);b=index(by_id[target],codes);rows=[]
    for code in sorted(set(a)&set(b)):
        rows.append({'code':code,'source':a[code],'target':b[code],'ambiguous':len(a[code])!=1 or len(b[code])!=1})
        if len(rows)>500:raise DocumentError('Más de 500 identificadores comunes; escribe los códigos que necesitas.')
    hashes=defaultdict(list)
    for item in items:hashes[item['sha256']].append(item['id'])
    return {'candidates':rows,'duplicates':[ids for ids in hashes.values() if len(ids)>1],'unmatched_source':len(set(a)-set(b)),'unmatched_target':len(set(b)-set(a)),'scope':'Identificadores de una línea digital; para escaneados prepara antes el OCR.'}


def manual_anchor(item,code,number,rect):
    code=normalized(text(code,80))
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9./-]{0,79}',code):raise DocumentError('Usa un identificador alfanumérico con guiones, puntos o barras.')
    if type(number) is not int or not isinstance(rect,list) or len(rect)!=4 or any(not finite(v) for v in rect):raise DocumentError('Página o región manual no válida.')
    with open_pdf(item['data']) as doc:
        if not 0<=number<len(doc):raise DocumentError('Página de referencia fuera del documento.')
        box=f.Rect(rect)
        if min(box.width,box.height)<2 or not doc[number].rect.contains(box):raise DocumentError('Marca una región de al menos 2 × 2 pt dentro de la página.')
    coordinates=[round(v,4) for v in rect]
    identity=digest(json.dumps(['manual',item['sha256'],number,coordinates,code]).encode())[:24]
    return {'id':identity,'document':item['id'],'page':number,'rect':coordinates,'code':code,'kind':'manual'}


def validate_relations(items,relations):
    if not isinstance(relations,list) or len(relations)>500:raise DocumentError('Hasta 500 vínculos por conjunto.')
    documents(items);by_id={i['id']:i for i in items};codes=[];seen=set()
    for r in relations:
        if not isinstance(r,dict) or set(r)!={'id','code','source','target'} or not isinstance(r['id'],str) or not ID.fullmatch(r['id']) or r['id'] in seen:raise DocumentError('Vínculo no válido o repetido.')
        seen.add(r['id']);codes.append(text(r['code'],80))
        for side in ['source','target']:
            anchor=r[side]
            if not isinstance(anchor,dict) or set(anchor) not in [{'id','document','page','rect','code'},{'id','document','page','rect','code','kind'}] or ('kind' in anchor and anchor['kind']!='manual') or not isinstance(anchor['document'],str) or anchor['document'] not in by_id:raise DocumentError('Destino de vínculo no válido.')
        if r['source']['document']==r['target']['document']:raise DocumentError('El vínculo debe relacionar documentos distintos.')
    if len(set(codes))>200:raise DocumentError('Hasta 200 identificadores distintos en los vínculos.')
    automatic_codes=sorted({r['code'] for r in relations if any(r[s].get('kind')!='manual' for s in ['source','target'])})
    indices={item['id']:index(item,automatic_codes) for item in items} if automatic_codes else {}
    pairs=set()
    for r in relations:
        if normalized(r['code'])!=r['code']:raise DocumentError('Identificador de vínculo no normalizado.')
        for side in ['source','target']:
            anchor=r[side]
            matches=[manual_anchor(by_id[anchor['document']],r['code'],anchor['page'],anchor['rect'])] if anchor.get('kind')=='manual' else indices[anchor['document']].get(r['code'],[])
            if anchor not in matches:raise DocumentError('Una referencia ya no coincide con su PDF. Revisa de nuevo los destinos.')
        pair=(r['source']['document'],r['source']['id'],r['target']['document'],r['target']['id'])
        if pair in pairs:raise DocumentError('El mismo vínculo ya está incluido.')
        pairs.add(pair)
    return relations


def build(items,relations,name):
    documents(items);validate_relations(items,relations);name=text(name,100)
    version=2 if any(r[s].get('kind')=='manual' for r in relations for s in ['source','target']) else 1
    manifest={'format':'reapdf-document-set','version':version,'name':name,'documents':[{k:v for k,v in i.items() if k!='data'} for i in items],'relations':relations}
    stream=BytesIO()
    with ZipFile(stream,'w',ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,allow_nan=False))
        for item in items:archive.writestr('documents/'+item['id']+'.pdf',item['data'])
    return stream.getvalue()


def read(data):
    if not isinstance(data,bytes) or not data or len(data)>70*1024*1024:raise DocumentError('Conjunto vacío o mayor de 70 MB.')
    try:
        with ZipFile(BytesIO(data)) as archive:
            entries=archive.infolist()
            if not 2<=len(entries)<=11 or len({i.filename for i in entries})!=len(entries):raise DocumentError('Archivos del conjunto no válidos o repetidos.')
            info=archive.getinfo('manifest.json')
            if info.file_size>1024*1024:raise DocumentError('Manifiesto demasiado grande.')
            manifest=json.loads(archive.read(info))
            if not isinstance(manifest,dict) or set(manifest)!={'format','version','name','documents','relations'} or manifest['format']!='reapdf-document-set' or type(manifest['version']) is not int or manifest['version'] not in [1,2]:raise DocumentError('Formato de conjunto no compatible.')
            text(manifest['name'],100);docs=manifest['documents']
            if not isinstance(docs,list) or not 1<=len(docs)<=10:raise DocumentError('Lista de documentos no válida.')
            expected={'manifest.json'};items=[];total=0
            for item in docs:
                if not isinstance(item,dict) or set(item)!={'id','name','role','sha256'} or not isinstance(item['id'],str) or not ID.fullmatch(item['id']):raise DocumentError('Descriptor PDF no válido.')
                name='documents/'+item['id']+'.pdf';expected.add(name);info=archive.getinfo(name);total+=info.file_size
                if info.flag_bits&1 or info.file_size>30*1024*1024 or total>MAX_SET:raise DocumentError('Tamaño o cifrado del conjunto no permitido.')
                with archive.open(info) as handle:content=handle.read(30*1024*1024+1)
                if len(content)>30*1024*1024:raise DocumentError('PDF demasiado grande.')
                items.append({**item,'data':content})
            if {i.filename for i in entries}!=expected:raise DocumentError('El conjunto contiene archivos ajenos al formato.')
            documents(items);validate_relations(items,manifest['relations'])
            if manifest['version']==1 and any(r[s].get('kind')=='manual' for r in manifest['relations'] for s in ['source','target']):raise DocumentError('Las referencias manuales requieren el formato de conjunto 2.')
            return items,manifest['relations'],manifest['name']
    except DocumentError:raise
    except (BadZipFile,KeyError,TypeError,ValueError,RuntimeError,OSError,EOFError) as exc:raise DocumentError('No se pudo verificar el conjunto. No se reemplazó el conjunto abierto.') from exc


def compile_pdf(items,relations,name):
    """Compile copies of pages and add reviewed native GoTo links/bookmarks.

    Originals remain in the portable set. Signed files, forms and OCGs require
    an explicit compatible working copy rather than silent loss of semantics.
    """
    documents(items);validate_relations(items,relations);name=text(name,100)
    if not relations:raise DocumentError('Crea al menos un vínculo antes de compilar el PDF.')
    offsets={};toc=[];total=0;by_id={i['id']:i for i in items}
    with f.open() as out:
        for item in items:
            offsets[item['id']]=total
            with open_pdf(item['data']) as source:
                if source.get_sigflags()>0 or source.get_ocgs() or any(list(p.widgets() or []) for p in source):raise DocumentError('La compilación protege firmas, formularios y capas. Prepara copias compatibles; el conjunto original conserva todos sus archivos.')
                if not source.permissions&(f.PDF_PERM_ASSEMBLE|f.PDF_PERM_MODIFY):raise DocumentError('Un documento no permite reorganizar sus páginas.')
                if total+len(source)>500:raise DocumentError('Hasta 500 páginas en el PDF compilado.')
                out.insert_pdf(source,links=True,annots=True,widgets=False)
                toc.append([1,item['role']+' · '+item['name'],total+1])
                for relation in relations:
                    if relation['source']['document']==item['id']:
                        # Destinations are resolved after every document offset
                        # is known; retain a stable placeholder here.
                        toc.append([2,relation['code']+' → '+by_id[relation['target']['document']]['role'],relation])
                for index,page in enumerate(source):
                    for key in ['ReapdfCalibration','ReapdfMeasurementScales']:
                        kind,value=source.xref_get_key(page.xref,key)
                        if kind=='string':
                            from .form_structure import pdf_string
                            out.xref_set_key(out[total+index].xref,key,pdf_string(value))
                total+=len(source)
        occupied={p.number:[f.Rect(l['from']) for l in p.get_links()] for p in out};targets={}
        for relation in relations:
            a,b=relation['source'],relation['target'];number=offsets[a['document']]+a['page'];target=offsets[b['document']]+b['page'];rect=f.Rect(a['rect'])
            key=(a['document'],a['id']);destination=(b['document'],b['id'])
            if key in targets and targets[key]!=destination:raise DocumentError('Una aparición tiene varios destinos. Resuelve el vínculo antes de compilar enlaces superpuestos.')
            targets[key]=destination
            if any((rect&other).get_area()>.1 for other in occupied[number]):raise DocumentError('Un vínculo se superpone con otro enlace existente. Revisa las apariciones elegidas.')
            occupied[number].append(rect);page=out[number];rotation=page.rotation;box=rect*page.derotation_matrix;to=f.Point(b['rect'][:2])*out[target].derotation_matrix
            page.set_rotation(0)
            try:page.insert_link({'kind':f.LINK_GOTO,'from':box,'page':target,'to':to})
            finally:page.set_rotation(rotation)
        for entry in toc:
            if isinstance(entry[2],dict):r=entry[2]['target'];entry[2]=offsets[r['document']]+r['page']+1
        out.set_toc(toc);out.set_metadata({'title':name,'creator':'Reapdf','subject':'Compilación de páginas con vínculos revisados. Los originales se conservan en el conjunto Reapdf.'})
        data=out.tobytes(garbage=4,deflate=True)
    if len(data)>MAX_SET:raise DocumentError('El PDF compilado supera 60 MB.')
    with open_pdf(data) as check:
        if len(check)!=total or sum(1 for p in check for link in p.get_links() if link['kind']==f.LINK_GOTO)<len(relations):raise DocumentError('No se pudo comprobar el PDF vinculado.')
    return data,{'documents':len(items),'pages':total,'links':len(relations),'scope':'Copias de páginas, marcadores y enlaces nativos; conserva los originales con Guardar conjunto. No transfiere el árbol de accesibilidad ni adjuntos del documento fuente.'}


def revision(items,relations,old_id,replacement,choices=None):
    """Review every affected link before replacing a set snapshot.

    A unique code can still have moved to a different page: suggestions never
    constitute approval. Missing anchors require an explicit removed relation.
    Inputs are validated again when applying, so stale/tampered plans fail.
    """
    validate_relations(items,relations)
    old=next((i for i in items if i['id']==old_id),None)
    if old is None:raise DocumentError('Elige el documento que se revisará.')
    documents([replacement])
    if replacement['id'] in {i['id'] for i in items}:raise DocumentError('La revisión necesita una nueva copia del documento.')
    replacement={**replacement,'role':old['role']}
    updated=[replacement if i['id']==old_id else i for i in items];documents(updated)
    affected=[r for r in relations if any(r[s]['document']==old_id for s in ['source','target'])]
    codes=sorted({r['code'] for r in affected});new_index=index(replacement,codes) if codes else {};rows=[]
    for r in affected:
        side='source' if r['source']['document']==old_id else 'target';anchor=r[side];candidates=[] if anchor.get('kind')=='manual' else new_index.get(r['code'],[])
        exact=[a for a in candidates if a['page']==anchor['page'] and all(abs(x-y)<.05 for x,y in zip(a['rect'],anchor['rect']))]
        suggested=exact[0]['id'] if len(exact)==1 else candidates[0]['id'] if len(candidates)==1 else ''
        status='manual_review' if anchor.get('kind')=='manual' else 'ambiguous' if len(candidates)>1 else 'same_location' if len(exact)==1 else 'moved' if candidates else 'missing'
        rows.append({'relation':r['id'],'code':r['code'],'side':side,'previous':anchor,'candidates':candidates,'suggested':suggested,'status':status})
    if choices is None:return {'old':{k:v for k,v in old.items() if k!='data'},'replacement':{k:v for k,v in replacement.items() if k!='data'},'affected':rows,'unaffected':len(relations)-len(rows),'review_required':True}
    if not isinstance(choices,dict) or set(choices)!={r['relation'] for r in rows}:raise DocumentError('Revisa el destino o la retirada de cada vínculo afectado.')
    selected={};removed=set()
    for row in rows:
        choice=choices[row['relation']]
        if isinstance(choice,dict) and row['previous'].get('kind')=='manual':
            candidate=manual_anchor(replacement,row['code'],choice.get('page'),choice.get('rect'))
            if set(choice)!={'page','rect'}:raise DocumentError('Revisa la región manual en el documento nuevo.')
            selected[row['relation']]=(row['side'],candidate);continue
        if choice is None:removed.add(row['relation']);continue
        match=next((a for a in row['candidates'] if a['id']==choice),None)
        if match is None:raise DocumentError('Un destino no pertenece a la revisión actual.')
        selected[row['relation']]=(row['side'],match)
    result=[]
    for r in relations:
        if r['id'] in removed:continue
        if r['id'] in selected:
            side,anchor=selected[r['id']];r={**r,side:anchor}
        result.append(r)
    validate_relations(updated,result)
    return updated,result,{'reviewed':len(rows),'removed':len(removed),'unaffected':len(relations)-len(rows)}
