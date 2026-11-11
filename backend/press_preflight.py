"""Named PDF/X preparation checks, explicitly short of ISO certification."""
import math,re
import pymupdf as f
from .engine import DocumentError
from .styled_text import stream
PROFILES={'x1a-2001':'PDF/X-1a:2001 · preparación','x4-2010':'PDF/X-4:2010 · preparación'}


def evaluate(doc,general,profile):
    if profile not in PROFILES:raise DocumentError('Perfil de impresión no válido.')
    n=f.mupdf;pdf=f._as_pdf_document(doc);root=n.pdf_load_object(pdf,doc.pdf_catalog());checks=[]
    def add(code,status,message,page=None,xref=None):
        if len(checks)>=3000:raise DocumentError('Más de 3000 hallazgos PDF/X; divide el documento.')
        checks.append({'code':code,'status':status,'message':message,'page':page,'xref':xref})
    def get(obj,key):return n.pdf_dict_gets(obj,key)
    intents=get(root,'OutputIntents');output=None
    if not n.pdf_is_array(intents) or not 1<=n.pdf_array_len(intents)<=16:add('output_intent','error','Falta una condición de salida PDF/X con perfil ICC incrustado.')
    else:
        selected=[n.pdf_array_get(intents,i) for i in range(n.pdf_array_len(intents)) if n.pdf_to_name(get(n.pdf_array_get(intents,i),'S'))=='GTS_PDFX']
        if len(selected)!=1:add('output_intent','error','Debe haber una condición de salida GTS_PDFX única y verificable.')
        else:
            intent=selected[0];ref=get(intent,'DestOutputProfile');xref=n.pdf_to_num(ref)
            try:
                if not xref or not n.pdf_is_stream(ref):raise DocumentError('El perfil de salida debe estar incrustado; no se revisan perfiles externos.')
                from .press_icc import inspect
                output=inspect(stream(doc,xref,2*1024*1024));channels=get(ref,'N')
                if not n.pdf_is_int(channels) or n.pdf_to_int(channels)!=output['channels']:raise DocumentError('N del stream no coincide con los canales ICC.')
                identifier=get(intent,'OutputConditionIdentifier')
                if not n.pdf_is_string(identifier) or not n.pdf_to_text_string(identifier).strip():raise DocumentError('Falta el identificador de la condición de salida.')
                if profile=='x1a-2001' and (output['space']!='CMYK' or output['major_version']!=2):raise DocumentError('Este perfil preparatorio PDF/X-1a espera una salida CMYK ICC v2.')
                add('output_intent','pass','Condición de salida e ICC estructuralmente comprobados.',xref=xref)
            except DocumentError as exc:add('output_intent','error',str(exc),xref=xref)
    if doc.metadata.get('encryption'):add('encryption','error','PDF/X no admite cifrado.')
    else:add('encryption','pass','Documento sin cifrado activo.')
    for font in general['fonts']:
        add('font_embedding','pass' if font['embedded'] else 'error',('Fuente declarada incrustada: ' if font['embedded'] else 'Incrusta la fuente: ')+font['name'],font['pages'][0])
        if font['type']=='Type3':add('type3_glyphs','review','Los programas y colores internos de Type3 requieren una comprobación adicional.',font['pages'][0])
    if general['layers']:add('layers','error' if profile=='x1a-2001' else 'review','Hay capas; comprueba estados de impresión y contenido condicional.')
    if doc.embfile_count() or not n.pdf_is_null(get(root,'Collection')):add('attachments','error','Los adjuntos/portfolios necesitan retirarse de una copia de impresión.')
    for key in ['OpenAction','AA']:
        if not n.pdf_is_null(get(root,key)):add('actions','error','El catálogo contiene acciones interactivas.')
    names=get(root,'Names')
    if not n.pdf_is_null(get(names,'JavaScript')):add('javascript','error','Hay acciones JavaScript en el documento.')
    for page,row in zip(doc,general['pages']):
        obj=n.pdf_load_object(pdf,page.xref)
        raw={key:get(obj,key) for key in ['TrimBox','ArtBox','BleedBox']}
        trim=not n.pdf_is_null(raw['TrimBox']);art=not n.pdf_is_null(raw['ArtBox'])
        if trim==art:add('page_boxes','error','Define exactamente una caja de corte TrimBox o de arte ArtBox explícita.',page.number)
        else:
            valid=True
            for key,value in raw.items():
                if n.pdf_is_null(value):continue
                if not n.pdf_is_array(value) or n.pdf_array_len(value)!=4:valid=False;continue
                vals=[n.pdf_array_get(value,i) for i in range(4)]
                if any(not n.pdf_is_number(v) for v in vals):valid=False;continue
                box=f.Rect([n.pdf_to_real(v) for v in vals])
                if not all(math.isfinite(v) for v in box) or box.is_empty or not page.mediabox.contains(box):valid=False
            chosen=page.trimbox if trim else page.artbox
            if not page.bleedbox.contains(chosen):valid=False
            add('page_boxes','pass' if valid else 'error','Cajas explícitas y anidamiento comprobados.' if valid else 'Revisa las cajas: deben ser válidas y quedar dentro de MediaBox y BleedBox.',page.number)
        colors=set(row['vector_colors']);rgb=bool(colors&{'RGB','ICCBased3'}) or any(im['channels']==3 for im in row['images'])
        if profile=='x1a-2001' and (rgb or colors&{'CalRGB','Lab'}):add('color_space','error','Se detecta RGB/Lab; asignar un ICC no convierte esos colores a CMYK.',page.number)
        elif profile=='x4-2010' and rgb and output and output['space']!='RGB':add('color_management','review','Hay RGB con salida no RGB; verifica perfiles de origen y espacios por defecto, también dentro de Forms.',page.number)
        if row['color_analysis']['limited'] or colors&{'Otro','ICCBased','Indexed','Pattern'}:add('color_coverage','review','El análisis de espacios de color es parcial; requiere un validador completo.',page.number)
        if row['color_analysis']['spot_colorants']:add('spot_functions','review','Se detectan tintas planas; faltan evaluar funciones de tinta y separaciones.',page.number)
        for item in general['issues']:
            if item['page']==page.number and item['code']=='image_resolution':add('image_resolution','warning',item['message'],page.number)
        if page.annot_xrefs():add('annotations','review','Revisa tipos, banderas y posición de anotaciones respecto al área de impresión.',page.number)
    # Follow catalog references and direct resource dictionaries; unrelated,
    # abandoned objects from previous revisions do not describe current output.
    def reachable():
        stack=[(n.pdf_new_indirect(pdf,doc.pdf_catalog(),0),0,0)];seen=set();count=0
        while stack:
            value,owner,depth=stack.pop();count+=1
            if count>1_000_000 or depth>128:raise DocumentError('El grafo de recursos supera el límite de revisión PDF/X.')
            identity=n.pdf_to_num(value)
            if identity:
                if identity in seen:continue
                seen.add(identity);owner=identity;value=n.pdf_resolve_indirect(value)
            if n.pdf_is_dict(value):
                yield owner,value
                stack.extend((n.pdf_dict_get_val(value,i),owner,depth+1) for i in range(n.pdf_dict_len(value)))
            elif n.pdf_is_array(value):stack.extend((n.pdf_array_get(value,i),owner,depth+1) for i in range(n.pdf_array_len(value)))
    for xref,obj in reachable():
        subtype=n.pdf_to_name(get(obj,'Subtype'));kind=n.pdf_to_name(get(obj,'Type'))
        if not n.pdf_is_null(get(obj,'AA')) or n.pdf_to_name(get(obj,'S'))=='JavaScript':add('actions','error','Hay acciones adicionales o JavaScript declarados.',xref=xref)
        if subtype in ['Widget','RichMedia','Movie','Sound','Screen','3D','FileAttachment']:add('interactive_content','error','Contenido interactivo que requiere preparar una copia aplanada.',xref=xref)
        if kind=='Filespec' and not n.pdf_is_null(get(obj,'F')):add('external_or_embedded_file','review','Hay una referencia a archivo; revisa su alcance.',xref=xref)
        if not n.pdf_is_null(get(obj,'Ref')) and subtype=='Form':add('external_form','error','Se detecta una referencia externa de Form.',xref=xref)
        transparency=False
        for key in ['CA','ca']:
            value=get(obj,key)
            if n.pdf_is_number(value) and n.pdf_to_real(value)<1:transparency=True
        mask=get(obj,'SMask');group=get(obj,'Group');blend=get(obj,'BM')
        if not n.pdf_is_null(mask) and n.pdf_to_name(mask)!='None':transparency=True
        if n.pdf_to_name(get(group,'S'))=='Transparency':transparency=True
        if n.pdf_is_name(blend) and n.pdf_to_name(blend) not in ['Normal','Compatible']:transparency=True
        if n.pdf_is_array(blend) and any(n.pdf_to_name(n.pdf_array_get(blend,i)) not in ['Normal','Compatible'] for i in range(min(n.pdf_array_len(blend),32))):transparency=True
        if transparency:add('transparency','error' if profile=='x1a-2001' else 'review','Se declaran recursos con transparencia; PDF/X-1a requiere aplanarla y PDF/X-4 requiere verificar mezcla/color.',xref=xref)
    from .press_metadata import claims
    try:
        declarations=claims(doc);pdfx=[v for v in declarations if v['key'] in ['GTS_PDFXVersion','GTS_PDFXConformance']]
        if not pdfx:add('standard_claim','review','No declara PDF/X. Esta preparación no asigna ni certifica la declaración del estándar.')
        else:add('standard_claim','review','Hay una declaración PDF/X previa; debe contrastarse con un validador completo.')
    except DocumentError as exc:declarations=[];add('metadata','review',str(exc))
    trapped=doc.xref_get_key(n.pdf_to_num(get(n.pdf_trailer(pdf),'Info')),'Trapped') if n.pdf_to_num(get(n.pdf_trailer(pdf),'Info')) else ('null','null')
    if trapped not in [('name','/True'),('name','/False')]:add('trapping','review','El estado de trapping no está declarado como True/False; debe revisarlo la imprenta.')
    version=doc.metadata.get('format','');add('pdf_version','review',f'Versión declarada: {version}. Comprueba restricciones de PDF 1.3 para X-1a o PDF 1.6 para X-4; no se reescribe el encabezado.')
    counts={status:sum(c['status']==status for c in checks) for status in ['error','warning','review','pass']}
    return {'id':profile,'label':PROFILES[profile],'status':'blocked' if counts['error'] else 'needs_full_validation','compliant':None,'validation_complete':False,'counts':counts,'checks':checks,'output_profile':output,'declarations':declarations,'scope':'Controles preparatorios específicos, no certificación ISO/PDF/X. No se evalúan todos los glifos, funciones de tinta, cobertura de tinta, mezcla/transparencia, perfiles de origen ni requisitos de imprenta.'}
