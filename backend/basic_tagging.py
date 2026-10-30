"""Reviewed initial text tagging for simple, previously untagged PDFs."""
import hashlib,math
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError
from .document_tools import editable
from .pdf_content import operations
from .form_structure import pdf_string

ROLES={'P','H','H1','H2','H3','H4','H5','H6'}


def plans(doc):
    if len(doc)>20:raise DocumentError('El etiquetado inicial admite hasta 20 páginas.')
    catalog=doc.pdf_catalog()
    if doc.xref_get_key(catalog,'StructTreeRoot')[0]!='null' or doc.xref_get_key(catalog,'MarkInfo/Marked')[1]=='true':raise DocumentError('El documento ya tiene estructura o declara etiquetas. Usa su editor existente.')
    result=[];total=0;total_bytes=0
    for page in doc:
        if doc.xref_get_key(page.xref,'StructParents')[0]!='null' or list(page.annots() or []) or list(page.widgets() or []) or page.get_links():raise DocumentError('El etiquetado inicial no admite estructura parcial, anotaciones, formularios ni enlaces.')
        content=page.read_contents();total_bytes+=len(content)
        if total_bytes>16*1024*1024:raise DocumentError('El contenido de etiquetado supera 16 MB.')
        digest=hashlib.sha256(content).digest();parts=[];start=None;shown=False
        for op,args,token in operations(content):
            begin=args[0].start if args else token.start
            if op in ['BMC','BDC','EMC','MP','DP','Do']:raise DocumentError('El etiquetado inicial necesita texto directo sin marcas previas, imágenes ni Forms. Conserva el original.')
            if op=='BT':
                if start is not None:raise DocumentError('Objeto de texto anidado.')
                start=begin;shown=False
            elif op in ['Tj','TJ',"'",'"']:
                if start is None:raise DocumentError('Texto fuera de un objeto BT/ET.')
                shown=True
            elif op=='ET':
                if start is None:raise DocumentError('Fin de objeto de texto sin inicio.')
                if shown:
                    parts.append({'start':start,'end':token.end,'id':hashlib.sha256(f'{page.number}:{start}:{token.end}:'.encode()+digest).hexdigest()[:32]})
                start=None
        if start is not None:raise DocumentError('Objeto de texto incompleto.')
        total+=len(parts)
        if len(parts)>200 or total>500:raise DocumentError('Hasta 200 objetos de texto por página y 500 por documento.')
        result.append({'page':page.number,'content':content,'parts':parts})
    if not total:raise DocumentError('No se encontraron objetos de texto directo. El etiquetado no realiza OCR.')
    return result


def build(doc,prepared,selection=None,language='es'):
    def new(value):
        x=doc.get_new_xref();doc.update_object(x,value);return x
    root=new('<< /Type /StructTreeRoot >>');document=new(f'<< /Type /StructElem /S /Document /P {root} 0 R /Lang {pdf_string(language)} >>');sections=[];parentnums=[]
    for plan in prepared:
        page=doc[plan['page']];parts=plan['parts'];section=new(f'<< /Type /StructElem /S /Sect /P {document} 0 R /Pg {page.xref} 0 R >>');sections.append(section);refs=[];content=[];previous=0;mapping={}
        for mcid,part in enumerate(parts):
            role=selection[part['id']]['role'] if selection else 'P'
            identity=new(f'<< /Type /StructElem /S /{role} /P {section} 0 R /Pg {page.xref} 0 R /K {mcid} >>');refs.append(identity);mapping[part['id']]=identity
            before=plan['content'][previous:part['start']]
            if before.strip():content.extend([b'/Artifact BMC\n',before,b'\nEMC\n'])
            content.extend([f'/{role} <</MCID {mcid}>> BDC\n'.encode(),plan['content'][part['start']:part['end']],b'\nEMC\n']);previous=part['end']
        tail=plan['content'][previous:]
        if tail.strip():content.extend([b'/Artifact BMC\n',tail,b'\nEMC\n'])
        stream=new('<<>>');doc.update_stream(stream,b''.join(content));page.set_contents(stream)
        ordered=sorted(parts,key=lambda p:selection[p['id']]['position']) if selection else parts
        doc.xref_set_key(section,'K','['+' '.join(f'{mapping[p["id"]]} 0 R' for p in ordered)+']')
        doc.xref_set_key(page.xref,'StructParents',str(page.number));parentnums.append(str(page.number)+' ['+' '.join(f'{r} 0 R' for r in refs)+']')
    doc.xref_set_key(document,'K','['+' '.join(f'{r} 0 R' for r in sections)+']')
    tree=new('<< /Nums ['+' '.join(parentnums)+'] >>');doc.xref_set_key(root,'K',f'[{document} 0 R]');doc.xref_set_key(root,'ParentTree',f'{tree} 0 R');doc.xref_set_key(root,'ParentTreeNextKey',str(len(prepared)))
    catalog=doc.pdf_catalog();doc.xref_set_key(catalog,'StructTreeRoot',f'{root} 0 R');doc.xref_set_key(catalog,'MarkInfo','<< /Marked true >>');doc.xref_set_key(catalog,'Lang',pdf_string(language))


def candidates(base,ops):
    with open_pdf(base) as source:
        editable(source)
        if not source.permissions&f.PDF_PERM_COPY:raise DocumentError('Se necesita permiso de lectura del contenido.')
    edited=export_pdf(base,ops)
    with open_pdf(edited) as doc:
        prepared=plans(doc);build(doc,prepared);entries=[]
        for plan in prepared:
            page=doc[plan['page']];found={}
            def walk(blocks):
                for block in blocks:
                    if block['type']==2:
                        if block.get('std')=='P':
                            text=[];boxes=[]
                            def collect(items):
                                for item in items:
                                    if item['type']==0:
                                        text.extend(''.join(s['text'] for s in line['spans']) for line in item['lines']);boxes.append(f.Rect(item['bbox']))
                                    elif item['type']==2:collect(item.get('blocks',[]))
                            collect(block.get('blocks',[]));index=block['index'];slot=found.setdefault(index,{'lines':[],'boxes':[]});slot['lines'].extend(text);slot['boxes'].extend(boxes)
                        else:walk(block.get('blocks',[]))
            walk(page.get_text('dict',flags=f.TEXT_COLLECT_STRUCTURE|f.TEXT_PRESERVE_WHITESPACE)['blocks'])
            for i,part in enumerate(plan['parts']):
                item=found.get(i);text='\n'.join(item['lines']).strip() if item else ''
                if not text or len(text)>4000:raise DocumentError('Un objeto no tiene texto extraíble o supera 4000 caracteres. No se crearon etiquetas parciales.')
                rect=f.Rect()
                for box in item['boxes']:rect|=box
                rect*=page.rotation_matrix
                entries.append({'id':part['id'],'page':page.number,'role':'P','text':text,'box':[rect.x0,rect.y0,rect.width,rect.height]})
        if sum(len(e['text']) for e in entries)>100000:raise DocumentError('La revisión supera 100000 caracteres.')
        return {'entries':entries,'pages':len(doc),'review_required':True,'scope':'Etiquetas de texto directo por objeto BT/ET; gráficos vectoriales restantes se consideran decorativos solo tras tu revisión. No reconoce tablas, listas ni figuras y no acredita PDF/UA.'}


def create(base,ops,entries,language='es',reviewed=False):
    from .accessibility import LANGUAGE
    if reviewed is not True:raise DocumentError('Revisa orden, roles y gráficos decorativos antes de crear las etiquetas.')
    if not isinstance(language,str) or len(language)>63 or not LANGUAGE.fullmatch(language):raise DocumentError('Idioma BCP 47 básico no válido.')
    info=candidates(base,ops);expected={e['id']:e for e in info['entries']}
    if not isinstance(entries,list) or len(entries)!=len(expected):raise DocumentError('Incluye todos los objetos de texto de la revisión actual.')
    selection={}
    for position,entry in enumerate(entries):
        if not isinstance(entry,dict) or set(entry)!={'id','role'} or not isinstance(entry['id'],str) or entry['id'] not in expected or entry['id'] in selection or not isinstance(entry['role'],str) or entry['role'] not in ROLES:raise DocumentError('La revisión contiene objetos repetidos, obsoletos o roles no compatibles.')
        selection[entry['id']]={'role':entry['role'],'position':position}
    page_order=[expected[e['id']]['page'] for e in entries]
    if page_order!=sorted(page_order):raise DocumentError('El orden se puede cambiar dentro de cada página, conservando la secuencia de páginas.')
    edited=export_pdf(base,ops)
    with open_pdf(edited) as before,open_pdf(edited) as doc:
        prepared=plans(doc);build(doc,prepared,selection,language);result=doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
        with open_pdf(result) as saved:
            for a,b in zip(before,saved):
                scale=min(.75,math.sqrt(4_000_000/max(1,a.rect.get_area())))
                if a.get_text()!=b.get_text() or a.get_pixmap(matrix=f.Matrix(scale,scale),alpha=False).samples!=b.get_pixmap(matrix=f.Matrix(scale,scale),alpha=False).samples:raise DocumentError('Las etiquetas alteraron contenido o apariencia. Se conserva el original.')
    return result,{'tagged_objects':len(entries),'pages':info['pages'],'language':language,'pdf_ua_validated':False}
