"""Edit one image invocation without changing other uses of its PDF object."""
import hashlib
import pymupdf as fitz
from .engine import open_pdf,export_pdf,DocumentError,finite
from .document_tools import editable
from .images import prepare_image
from .pdf_content import placements,set_content
from .form_text import SAFE,array,write


def _page_matrix(page):
    rotation=page.rotation
    try:
        if rotation:page.set_rotation(0)
        return page.transformation_matrix
    finally:
        if rotation:page.set_rotation(rotation)


def _resources(doc,owner):
    seen=set()
    while True:
        kind,value=doc.xref_get_key(owner,'Resources')
        if kind!='null':return owner
        kind,value=doc.xref_get_key(owner,'Parent')
        if kind!='xref':return owner
        owner=int(value.split()[0])
        if owner in seen or len(seen)>32:raise DocumentError('Recursos heredados no válidos.')
        seen.add(owner)


def _invocations(doc,page):
    result=[];budget={'bytes':0,'nodes':0};page_matrix=_page_matrix(page)
    def walk(owner,data,parent,path,ancestors,clips):
        budget['bytes']+=len(data);budget['nodes']+=1
        if budget['bytes']>32*1024*1024 or budget['nodes']>200 or len(path)>8:raise DocumentError('La página supera los límites de edición de imágenes.')
        resource_owner=_resources(doc,owner)
        if doc.xref_get_key(resource_owner,'Resources/Properties')[0]!='null':return
        for inv in placements(data)['images']:
            name=inv['resource']
            if not SAFE.fullmatch(name):continue
            kind,value=doc.xref_get_key(resource_owner,'Resources/XObject/'+name)
            if kind!='xref':continue
            target=int(value.split()[0]);subtype=doc.xref_get_key(target,'Subtype')
            combined=inv['matrix']*parent
            if subtype==('name','/Image'):
                stamp=repr(([(s['start'],s['end']) for s in path],inv['start'],inv['end'],target)).encode()+data
                result.append({'xref':target,'_native':[inv['start'],inv['end'],'image'],'_native_path':path,'_matrix':combined,'_clips':clips,'occurrence':hashlib.sha256(stamp).hexdigest(),'_value':data[inv['start']:inv['end']]})
                if len(result)>2000:raise DocumentError('Hasta 2000 apariciones de imágenes por página.')
            elif subtype==('name','/Form'):
                if target in ancestors:continue
                if any(doc.xref_get_key(target,k)[0]!='null' for k in ['OC','Ref','StructParent','StructParents']):continue
                if doc.xref_get_key(target,'Resources')[0] not in ['dict','xref']:continue
                matrix=fitz.Matrix(*array(doc,target,'Matrix',6,[1,0,0,1,0,0]))*combined
                if abs(matrix.a*matrix.d-matrix.b*matrix.c)<1e-8:continue
                box=fitz.Rect(array(doc,target,'BBox',4))
                if box.is_empty:continue
                polygon=[fitz.Point(p)*matrix*page_matrix*page.rotation_matrix for p in [box.tl,box.tr,box.br,box.bl]]
                from .styled_text import stream
                child=stream(doc,target,16*1024*1024)
                step={'owner':owner,'target':target,'start':inv['start'],'end':inv['end']}
                walk(target,child,matrix,path+[step],ancestors|{target},clips+[polygon])
    walk(page.xref,page.read_contents(),fitz.Matrix(1,1),[],set(),[])
    return result


def _same_box(a,b):return all(abs(x-y)<.02 for x,y in zip(a,b))


def _inside(box,polygon):
    for point in [box.tl,box.tr,box.br,box.bl]:
        crosses=[(b.x-a.x)*(point.y-a.y)-(b.y-a.y)*(point.x-a.x) for a,b in zip(polygon,polygon[1:]+polygon[:1])]
        if min(crosses)<-.02 and max(crosses)>.02:return False
    return True


def image_model(doc,number,*,private=False):
    if type(number) is not int or not 0<=number<len(doc):raise DocumentError('Página no válida.')
    page=doc[number];infos=page.get_image_info(xrefs=True);page_matrix=_page_matrix(page)
    if len(infos)>2000:raise DocumentError('Hasta 2000 apariciones de imágenes por página.')
    try:invocations=_invocations(doc,page);failure=''
    except DocumentError as exc:invocations=[];failure=str(exc)
    ocr=any('GlyphLessFont' in font[3] for font in page.get_fonts())
    tagged=doc.xref_get_key(doc.pdf_catalog(),'StructTreeRoot')[0]!='null'
    items=[];used=set()
    for index,info in enumerate(infos):
        if min(info['width'],info['height'])<=1:continue
        xref=info['xref'];box=fitz.Rect(info['bbox'])*page.rotation_matrix
        candidates=[(i,v) for i,v in enumerate(invocations) if i not in used and v['xref']==xref and _same_box(fitz.Rect(0,0,1,1)*v['_matrix']*page_matrix,info['bbox'])]
        invocation=None
        if candidates:
            i,invocation=candidates[0];used.add(i)
        reason=''
        if doc.get_sigflags()>0 or not doc.permissions & fitz.PDF_PERM_MODIFY:reason='Documento firmado o sin permiso de edición.'
        elif tagged:reason='La imagen pertenece a un PDF etiquetado; su estructura requiere una edición semántica coordinada.'
        elif not xref or invocation is None:reason=failure or 'No se pudo aislar esta aparición de imagen de forma segura.'
        elif doc.xref_get_key(xref,'OC')[0]!='null':reason='Imagen asociada a una capa no compatible.'
        elif ocr:reason='La página tiene una capa OCR; mover la imagen desalinearía el texto.'
        elif abs(invocation['_matrix'].a*invocation['_matrix'].d-invocation['_matrix'].b*invocation['_matrix'].c)<1e-8:reason='Transformación de imagen degenerada.'
        elif not page.rect.contains(box):reason='Imagen parcialmente fuera de la página.'
        elif any(not _inside(box,p) for p in invocation['_clips']):reason='La imagen está parcialmente recortada por un Form.'
        row={'xref':xref,'occurrence':invocation['occurrence'] if invocation else None,'width':info['width'],'height':info['height'],'rect':list(box),'digest':info['digest'].hex(),'editable':not reason,'reason':reason,'direct_content':not reason,'notice':'Solo cambia esta aparición. Se conservan orientación, compresión, recorte y transparencia; revisa la vista previa.' if not reason else ''}
        if private and invocation:row.update(invocation);row['_render_index']=index
        items.append(row)
    return {'images':items}


def _remaining_unchanged(before,after):
    if len(before)!=len(after):return False
    for original in before:
        found=next((i for i,item in enumerate(after) if original['digest']==item['digest'] and original['width']==item['width'] and original['height']==item['height'] and _same_box(original['bbox'],item['bbox']) and _same_box(original['transform'],item['transform'])),None)
        if found is None:return False
        after.pop(found)
    return True


def edit_image(base,operations,number,xref,action,box=None,data=None,occurrence=None):
    if type(xref) is not int or action not in ['move','replace','delete']:raise DocumentError('Imagen o acción no válida.')
    if occurrence is not None and (not isinstance(occurrence,str) or len(occurrence)!=64):raise DocumentError('Aparición de imagen no válida.')
    with open_pdf(base) as source:
        editable(source);rows=image_model(source,number,private=True)['images']
        selected=[r for r in rows if r['xref']==xref and (occurrence is None or r['occurrence']==occurrence)]
        if len(selected)>1:raise DocumentError('La imagen se comparte; selecciona la aparición concreta antes de editar.')
        if not selected:raise DocumentError('Imagen o aparición inexistente.')
        original=selected[0]
        if not original['editable']:raise DocumentError(original['reason'])
    with open_pdf(export_pdf(base,operations)) as doc:
        rows=image_model(doc,number,private=True)['images']
        candidates=[r for r in rows if r['digest']==original['digest'] and _same_box(r['rect'],original['rect'])]
        if len(candidates)>1 and not operations:
            # Identical overlapping invocations retain their paint order.
            candidates=[r for r in candidates if r['_render_index']==original['_render_index']]
        if len(candidates)!=1 or not candidates[0]['editable']:raise DocumentError('Los cambios previos ya no permiten identificar esta imagen de forma segura.')
        item=candidates[0];page=doc[number];rect=fitz.Rect(item['rect']);before=page.get_image_info(xrefs=True);text=page.get_text()
        if action=='move':
            if not isinstance(box,list) or len(box)!=4 or any(not finite(v) for v in box):raise DocumentError('Posición y tamaño de imagen no válidos.')
            rect=fitz.Rect(box[0],box[1],box[0]+box[2],box[1]+box[3])
            if min(rect.width,rect.height)<1 or not page.rect.contains(rect):raise DocumentError('La imagen debe quedar dentro de la página y medir al menos 1 × 1 pt.')
            if any(not _inside(rect,p) for p in item['_clips']):raise DocumentError('La nueva caja sale del recorte del Form; reduce o desplaza la imagen dentro de él.')
            old=fitz.Rect(item['rect']);transform=fitz.Matrix(1,0,0,1,-old.x0,-old.y0)*fitz.Matrix(rect.width/old.width,rect.height/old.height)*fitz.Matrix(1,0,0,1,rect.x0,rect.y0)
            global_matrix=item['_matrix']*_page_matrix(page)*page.rotation_matrix
            matrix=global_matrix*transform*~global_matrix
            value=('q '+' '.join(f'{v:.10f}' for v in matrix)+' cm ').encode()+item['_value']+b' Q'
        elif action=='delete':value=b''
        else:
            _,replacement=prepare_image(page,{'data':data,'points':[[rect.x0,rect.y0],[rect.x1,rect.y1]]})
            # Import only the image/mask. Restore the stream after MuPDF appends
            # its staging draw, then add the resource to the isolated owner.
            content=page.read_contents();replacement_xref=page.insert_image(page.rect,stream=replacement)
            set_content(doc,page,content)
            owner=item['_native_path'][-1]['target'] if item['_native_path'] else page.xref
            resource_owner=_resources(doc,owner);alias='ReapdfImage'
            while doc.xref_get_key(resource_owner,'Resources/XObject/'+alias)[0]!='null':alias+='x'
            item['_native_xobjects']={alias:replacement_xref};value=('/'+alias+' Do').encode()
        write(doc,page,[(item,value)])
        result=doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
    # Reopen the serialized result: PyMuPDF caches display lists and image info
    # on loaded pages, so inspecting the old page could validate stale data.
    with open_pdf(result) as verified:
        page=verified[number]
        # Verify the rendered invocation list, not just the edited PDF syntax.
        after=page.get_image_info(xrefs=True);others=[v for i,v in enumerate(before) if i!=item['_render_index']]
        if action!='delete':
            candidates=[(i,v) for i,v in enumerate(after) if _same_box(fitz.Rect(v['bbox'])*page.rotation_matrix,rect) and (action=='replace' or v['digest'].hex()==item['digest'])]
            if len(candidates)!=1 and not (not operations and len(candidates)>1):raise DocumentError('No se pudo verificar la imagen editada.')
            # Remove the selected paint position when appearances overlap.
            chosen=next((i for i,v in candidates if i==item['_render_index']),candidates[0][0]);after=[v for i,v in enumerate(after) if i!=chosen]
        if not _remaining_unchanged(others,list(after)) or page.get_text()!=text:raise DocumentError('La edición alteraría otras imágenes o texto; no se publicó el cambio.')
        return result
