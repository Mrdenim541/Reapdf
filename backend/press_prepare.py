"""Native print preparation: page boxes and explicit local ICC, never PDF/X conversion."""
import base64,hashlib,json,math
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError
from .document_tools import editable
from .press_icc import inspect as inspect_icc,MAX_ICC
from .press_preflight import PROFILES


def digest(doc,limit,ignored):
    n=f.mupdf;pdf=f._as_pdf_document(doc);out={};budget=0
    from .text_typography import syntax
    for x in range(1,limit):
        if x in ignored and ignored[x] is None:continue
        obj=n.pdf_load_object(pdf,x)
        if n.pdf_to_name(n.pdf_dict_gets(obj,'Type')) in ['XRef','ObjStm']:continue
        if n.pdf_is_dict(obj):
            keys=sorted(n.pdf_to_name(n.pdf_dict_get_key(obj,i)) for i in range(n.pdf_dict_len(obj)))
            omit=ignored.get(x,set())|({'Length'} if doc.xref_is_stream(x) else set())
            text=' '.join(key+':'+syntax(n.pdf_dict_gets(obj,key)) for key in keys if key not in omit)
        else:text=syntax(obj)
        data=text.encode();raw=doc.xref_stream_raw(x) if doc.xref_is_stream(x) else b'';raw=raw or b'';budget+=len(data)+len(raw)
        if budget>128*1024*1024:raise DocumentError('La comprobación de objetos supera 128 MiB; divide el documento.')
        out[x]=hashlib.sha256(data+b'\x00'+raw).hexdigest()
    return out


def prepare(base,operations,payload,review=False):
    if not isinstance(payload,dict) or type(review) is not bool:raise DocumentError('Configuración de impresión no válida.')
    profile=payload.get('profile','x4-2010');boxes=payload.get('set_boxes',True)
    if profile not in PROFILES or type(boxes) is not bool:raise DocumentError('Selecciona un perfil de impresión válido.')
    margin=payload.get('trim_margin_mm',3);bleed=payload.get('bleed_mm',3);pages=payload.get('pages')
    if boxes and (any(type(v) not in [int,float] or not math.isfinite(v) for v in [margin,bleed]) or not 0<=bleed<=20 or not bleed<=margin<=50):raise DocumentError('El corte debe dejar entre 0 y 50 mm desde MediaBox; el sangrado, entre 0 y 20 mm y no más que ese margen.')
    encoded=payload.get('icc','');icc=None;icc_info=None;condition=payload.get('condition','')
    if not isinstance(encoded,str) or len(encoded)>4*((MAX_ICC+2)//3):raise DocumentError('El perfil ICC supera 2 MiB.')
    if encoded:
        try:icc=base64.b64decode(encoded,validate=True)
        except (ValueError,TypeError):raise DocumentError('Archivo ICC no válido.') from None
        icc_info=inspect_icc(icc)
        if not isinstance(condition,str) or not condition.strip() or len(condition)>200 or any(ord(c)<32 for c in condition):raise DocumentError('Escribe un identificador de condición de salida de 1 a 200 caracteres.')
    if not boxes and not icc:raise DocumentError('Elige cajas de impresión o un perfil ICC para preparar la copia.')
    with open_pdf(base) as source:editable(source)
    data=export_pdf(base,operations)
    with open_pdf(data) as doc:
        editable(doc)
        if len(doc)>100 or doc.xref_length()>50000:raise DocumentError('Hasta 100 páginas y 50000 objetos por preparación.')
        if boxes and (not isinstance(pages,list) or not 1<=len(pages)<=100 or any(type(v) is not int or not 0<=v<len(doc) for v in pages) or len(set(pages))!=len(pages)):raise DocumentError('Selecciona páginas existentes, sin repetir.')
        selected=sorted(pages) if boxes else []
        configuration={'profile':profile,'set_boxes':boxes,'pages':selected,'trim_margin_mm':float(margin) if boxes else None,'bleed_mm':float(bleed) if boxes else None,'icc_sha256':icc_info['sha256'] if icc_info else None,'condition':condition.strip() if icc else ''}
        try:token=hashlib.sha256(hashlib.sha256(base).digest()+json.dumps({'operations':operations,'configuration':configuration},sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        except (TypeError,ValueError):raise DocumentError('Las operaciones no permiten revisar esta copia.') from None
        if not review and (payload.get('acknowledge') is not True or payload.get('review_token')!=token):raise DocumentError('Revisa de nuevo las cajas y el perfil, y confirma los efectos antes de aplicar.')
        n=f.mupdf;pdf=f._as_pdf_document(doc);catalog=doc.pdf_catalog();info=n.pdf_to_num(n.pdf_dict_gets(n.pdf_trailer(pdf),'Info'));md=n.pdf_to_num(n.pdf_dict_gets(n.pdf_load_object(pdf,catalog),'Metadata'));limit=doc.xref_length()
        ignored={page.xref:{'TrimBox','BleedBox','ArtBox'} for page in doc if page.number in selected}
        # Original compression/index containers can become free objects on save.
        # Their member objects are still compared individually with stable xrefs.
        for x in range(1,limit):
            if n.pdf_to_name(n.pdf_dict_gets(n.pdf_load_object(pdf,x),'Type')) in ['XRef','ObjStm']:ignored[x]=None
        if icc:ignored.setdefault(catalog,set()).add('OutputIntents')
        if info:ignored[info]={'GTS_PDFXVersion','GTS_PDFXConformance'}
        # The XML object itself is compared to its intended new bytes below.
        before=digest(doc,limit,ignored)
        from .press_metadata import withdraw
        removed=withdraw(doc)
        if md:before.pop(md,None)
        changed=[]
        for number in selected:
            page=doc[number];media=page.mediabox;edge=float(margin)*72/25.4;extra=float(bleed)*72/25.4;trim=media+(edge,edge,-edge,-edge);bleedbox=trim+(-extra,-extra,extra,extra)
            if trim.width<1 or trim.height<1:raise DocumentError(f'Página {number+1}: el margen no deja un corte válido.')
            old={key:doc.xref_get_key(page.xref,key)[1] for key in ['TrimBox','BleedBox','ArtBox']}
            for key,box in [('TrimBox',trim),('BleedBox',bleedbox)]:doc.xref_set_key(page.xref,key,'['+' '.join(f'{v:.8f}' for v in box)+']')
            doc.xref_set_key(page.xref,'ArtBox','null');changed.append({'page':number,'before':old,'trim_pdf':list(trim),'bleed_pdf':list(bleedbox)})
        if icc:
            x=doc.get_new_xref();doc.update_object(x,f'<</N {icc_info["channels"]}>>');doc.update_stream(x,icc,compress=True)
            intent=doc.get_new_xref();doc.update_object(intent,f'<</Type/OutputIntent /S/GTS_PDFX /OutputConditionIdentifier {f.get_pdf_str(condition.strip())} /Info {f.get_pdf_str(icc_info["description"] or condition.strip())} /DestOutputProfile {x} 0 R>>');doc.xref_set_key(catalog,'OutputIntents',f'[{intent} 0 R]')
        expected_metadata=doc.xref_stream_raw(md) if md else None
        output=doc.tobytes(garbage=0,deflate=False,encryption=f.PDF_ENCRYPT_KEEP)
    with open_pdf(output) as check:
        after=digest(check,limit,ignored)
        if md:after.pop(md,None)
        if before!=after or md and check.xref_stream_raw(md)!=expected_metadata:raise DocumentError('La comprobación detectó un cambio ajeno a cajas, perfil o declaraciones; no se publica la copia.')
        for item in changed:
            for key,expected in [('TrimBox',item['trim_pdf']),('BleedBox',item['bleed_pdf'])]:
                value=n.pdf_dict_gets(n.pdf_load_object(f._as_pdf_document(check),check[item['page']].xref),key)
                if n.pdf_array_len(value)!=4 or any(abs(n.pdf_to_real(n.pdf_array_get(value,i))-expected[i])>.001 for i in range(4)):raise DocumentError('Las cajas guardadas no coinciden con las revisadas.')
        if icc:
            from .styled_text import stream
            obj=n.pdf_array_get(n.pdf_dict_gets(n.pdf_load_object(f._as_pdf_document(check),check.pdf_catalog()),'OutputIntents'),0);x=n.pdf_to_num(n.pdf_dict_gets(obj,'DestOutputProfile'))
            if hashlib.sha256(stream(check,x,MAX_ICC)).hexdigest()!=icc_info['sha256']:raise DocumentError('El perfil guardado no coincide con el elegido.')
        from .press_metadata import claims
        if claims(check):raise DocumentError('La copia conserva una declaración de estándar que no se ha revalidado; no se publica.')
        preview_page=selected[0] if selected else 0;view=check[preview_page];scale=min(1,800/max(view.rect.width,view.rect.height));preview_out=base64.b64encode(view.get_pixmap(matrix=f.Matrix(scale,scale),alpha=False).tobytes('png')).decode() if review else None
        overlay={'size':[view.rect.width,view.rect.height]}
        for name,key in [('trim','TrimBox'),('bleed','BleedBox')]:
            obj=n.pdf_dict_gets(n.pdf_load_object(f._as_pdf_document(check),view.xref),key)
            if n.pdf_is_array(obj) and n.pdf_array_len(obj)==4:overlay[name]=list(f.Rect([n.pdf_to_real(n.pdf_array_get(obj,i)) for i in range(4)])*view.transformation_matrix*view.rotation_matrix)
    from .preflight import inspect
    diagnostics=inspect(output,[],payload.get('min_dpi',150),profile)
    report={'schema':'reapdf-print-preparation-1','source_sha256':hashlib.sha256(base).hexdigest(),'output_sha256':hashlib.sha256(output).hexdigest(),'configuration':configuration,'review_token':token,'changed_pages':changed,'output_profile':icc_info,'withdrawn_claims':removed,'protected_objects_verified':len(before),'native_content_preserved':True,'colors_converted':False,'bleed_content_generated':False,'standard_conformity_claimed':False,'preflight':diagnostics}
    if review:
        with open_pdf(data) as source:
            scale=min(1,800/max(source[preview_page].rect.width,source[preview_page].rect.height));preview_in=base64.b64encode(source[preview_page].get_pixmap(matrix=f.Matrix(scale,scale),alpha=False).tobytes('png')).decode()
        report['preview']={'page':preview_page,'overlay':overlay,'source':'data:image/png;base64,'+preview_in,'output':'data:image/png;base64,'+preview_out}
        return report
    return output,report
