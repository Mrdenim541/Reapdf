"""Recorte reversible por versiones y división sin alterar la fuente."""
from .engine import pdf_garbage
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
import pymupdf as fitz
from .engine import open_pdf, export_pdf, DocumentError, finite, MAX_PAGES
from .pages import organize_pdf
from .merge import _check_source, _check_bookmarks, _incoming_links

MAX_SPLIT_BYTES = 100 * 1024 * 1024


def split_token(data,operations,review,preserve_tags):
    import hashlib,json
    try:payload=json.dumps({"input":hashlib.sha256(data).hexdigest(),"operations":operations,"parts":[{k:part[k] for k in ["name","pages","count"]} for part in review["parts"]],"rotations":review["rotations"],"preserve_tags":preserve_tags,"max_bytes":review.get("max_bytes")},sort_keys=True,ensure_ascii=True,allow_nan=False)
    except (TypeError,ValueError):raise DocumentError("No se puede verificar el plan de división.") from None
    return hashlib.sha256(payload.encode()).hexdigest()


def _selection(pages, count):
    if not isinstance(pages, list) or not pages or len(pages) > count or any(type(p) is not int or not 0 <= p < count for p in pages) or len(set(pages)) != len(pages):
        raise DocumentError('Selecciona páginas válidas, sin repeticiones.')


def crop_pdf(data, operations, pages, margins=None, *, reset=False):
    with open_pdf(data) as source:
        if source.get_sigflags() > 0:
            raise DocumentError('No se recortan PDF firmados en este prototipo.')
        if not source.permissions & fitz.PDF_PERM_MODIFY:
            raise DocumentError('El documento no permite modificar los límites de página.')
        _selection(pages, len(source))
        if type(reset) is not bool:
            raise DocumentError('Modo de recorte no válido.')
        if not reset:
            if not isinstance(margins, list) or len(margins) != 4 or any(not finite(v) or v < 0 for v in margins):
                raise DocumentError('Indica márgenes superior, derecho, inferior e izquierdo válidos en puntos.')
            top, right, bottom, left = margins
            for number in pages:
                rect = source[number].rect
                if rect.width-left-right < 10 or rect.height-top-bottom < 10:
                    raise DocumentError('El recorte debe conservar al menos 10 × 10 puntos en cada página.')
    edited = export_pdf(data, operations)
    with open_pdf(edited) as output:
        for number in pages:
            page = output[number]
            if reset:
                # CropBox usa el eje Y superior de MuPDF, incluso si MediaBox no empieza en cero.
                media = page.mediabox
                page.set_cropbox(fitz.Rect(media.x0, 0, media.x1, media.height))
            else:
                visible = fitz.Rect(left, top, page.rect.width-right, page.rect.height-bottom)
                native = visible * page.derotation_matrix
                old = page.cropbox
                page.set_cropbox(fitz.Rect(native.x0+old.x0, native.y0+old.y0,
                                           native.x1+old.x0, native.y1+old.y0))
        return output.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=pdf_garbage(output), deflate=True)


def prepare_split(data,operations,*,size=None,groups=None,names=None,bookmark_level=None,preserve_tags=True,max_bytes=None):
    from .split_plan import plan
    if max_bytes is not None:
        from .split_size import size_limit
        size_limit(max_bytes,MAX_SPLIT_BYTES)
        if size is not None or bookmark_level is not None:raise DocumentError('Elige tamaño máximo sin mezclar bloques o marcadores.')
    if type(preserve_tags) is not bool:raise DocumentError('Elige si quieres conservar las etiquetas de accesibilidad.')
    with open_pdf(data) as source:
        if source.get_sigflags()>0:raise DocumentError('Crea una copia de trabajo antes de dividir un PDF firmado; sus firmas no serían válidas en las partes.')
        if not source.permissions&fitz.PDF_PERM_COPY:raise DocumentError('El documento no permite dividir o copiar páginas.')
        _check_source(source);_check_bookmarks(source);_incoming_links(source)
    edited=export_pdf(data,operations)
    if not preserve_tags:
        with open_pdf(edited) as source:tagged=source.xref_get_key(source.pdf_catalog(),'StructTreeRoot')[0]!='null'
        if tagged:
            from .untagged_copy import create
            edited,_=create(edited,[],True)
    with open_pdf(edited) as doc:
        # Pending changes must pass the same partition guards as the original.
        _check_source(doc);_check_bookmarks(doc);_incoming_links(doc)
        from .structure_partition import partition
        structure=partition(doc,[p.xref for p in doc])
        rotations=[p.rotation for p in doc];measurements={}
        def measure(pages):
            key=tuple(pages)
            if key not in measurements:
                if len(measurements)>=1024:raise DocumentError('La división por tamaño supera el límite de 1024 mediciones. Usa grupos de páginas o un límite mayor.')
                output=organize_pdf(edited,[],[{'page':p,'rotation':rotations[p]} for p in pages],extract=True,partition_tags=True)
                measurements[key]=len(output)
            return measurements[key]
        if max_bytes is not None and groups is None:
            from .split_size import groups_by_bytes
            groups=groups_by_bytes(len(doc),structure['atomic_page_groups'],max_bytes,measure)
        result=plan(doc,size=size,groups=groups,names=names,bookmark_level=bookmark_level)
        for part in result['parts']:
            chosen=set(part['pages'])
            if any(chosen.intersection(group) and not set(group)<=chosen for group in structure['atomic_page_groups']):raise DocumentError('Un texto alternativo o una caja de maquetación abarca páginas de distintas partes. Ajusta los grupos o elige partes sin etiquetas.')
        if max_bytes is not None:
            result['max_bytes']=max_bytes
            for part in result['parts']:
                part['bytes']=measure(part['pages'])
                if part['bytes']>max_bytes:raise DocumentError('Una parte supera el tamaño máximo. Recalcula los grupos o aumenta el límite.')
            if sum(part['bytes'] for part in result['parts'])>MAX_SPLIT_BYTES:raise DocumentError('La división supera 100 MB de PDF de salida. Reduce el documento antes de dividirlo.')
        result['structure_nodes']=structure['nodes']
        result['rotations']=[p.rotation for p in doc]
        result['accessibility_tags_retained']=preserve_tags
    result["review_token"]=split_token(data,operations,result,preserve_tags)
    return edited,result


def inspect_split(data,operations,**options):
    _,result=prepare_split(data,operations,**options)
    result.pop('rotations');return result


def split_pdf(data, operations, *, size=None, groups=None,names=None,bookmark_level=None,manifest=False,preserve_tags=True,review_token=None,max_bytes=None):
    import json,hashlib
    if type(manifest) is not bool:raise DocumentError('La opción de relación de archivos debe ser verdadera o falsa.')
    edited,review=prepare_split(data,operations,size=size,groups=groups,names=names,bookmark_level=bookmark_level,preserve_tags=preserve_tags,max_bytes=max_bytes)
    if review_token is not None and (not isinstance(review_token,str) or review_token!=review['review_token']):raise DocumentError('La configuración o el documento cambió desde la comprobación. Revisa de nuevo antes de descargar.')
    from .split_integrity import scales,fingerprint,verify
    with open_pdf(edited) as source:
        page_scales=scales(source);labels=bool(source.get_page_labels());expected=[fingerprint(p,page_scales[p.number],labels) for p in source]
    buffer=BytesIO();total=0;records=[]
    with ZipFile(buffer,'w',ZIP_DEFLATED) as archive:
        for part in review['parts']:
            group=part['pages'];plan=[{'page':p,'rotation':review['rotations'][p]} for p in group]
            result=organize_pdf(edited,[],plan,extract=True,partition_tags=True);total+=len(result)
            if max_bytes is not None and len(result)>max_bytes:raise DocumentError('Una parte supera el tamaño máximo tras guardarse. No se entrega un ZIP parcial.')
            if total>MAX_SPLIT_BYTES:raise DocumentError('La división supera 100 MB de PDF de salida. Reduce el documento antes de dividirlo.')
            integrity=verify(result,expected,group,page_scales,labels)
            archive.writestr(part['name'],result)
            records.append({'name':part['name'],'source_pages':[p+1 for p in group],'pages':len(group),'bytes':len(result),'sha256':hashlib.sha256(result).hexdigest(),**integrity})
        if manifest:archive.writestr('reapdf-division.json',json.dumps({'format':'reapdf-split-receipt','version':1,'source_sha256':hashlib.sha256(edited).hexdigest(),'original_source_sha256':hashlib.sha256(data).hexdigest(),'accessibility_tags_retained':preserve_tags,'review_token':review['review_token'],'native_content_verified':True,'source_pages':review['pages'],'max_bytes_per_pdf':max_bytes,'parts':records},ensure_ascii=False,indent=2).encode('utf-8'))
    return buffer.getvalue()
