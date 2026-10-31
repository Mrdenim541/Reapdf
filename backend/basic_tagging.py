"""Reviewed initial direct-content tagging, including image occurrences and text links."""
import hashlib,math
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError
from .document_tools import editable
from .pdf_content import operations
from .form_structure import pdf_string

ROLES={'P','H','H1','H2','H3','H4','H5','H6','LI','TH','TD'}


def plans(doc):
    if len(doc)>20:raise DocumentError('El etiquetado inicial admite hasta 20 páginas.')
    catalog=doc.pdf_catalog()
    if doc.xref_get_key(catalog,'StructTreeRoot')[0]!='null' or doc.xref_get_key(catalog,'MarkInfo/Marked')[1]=='true':raise DocumentError('El documento ya tiene estructura o declara etiquetas. Usa su editor existente.')
    if doc.xref_get_key(catalog,'AcroForm/XFA')[0]!='null':raise DocumentError('Los formularios XFA requieren otro tratamiento.')
    result=[];total=0;total_bytes=0;image_pixels=0;form_budget={'nodes':0,'bytes':0}
    for page in doc:
        if doc.xref_get_key(page.xref,'StructParents')[0]!='null' or list(page.annots() or []) or list(page.widgets() or []):raise DocumentError('El etiquetado inicial no admite estructura parcial, anotaciones adicionales ni formularios.')
        from .link_editing import link_model
        link_info=link_model(doc,page.number)
        if link_info['truncated'] or len(link_info['links'])>100 or any(not link['editable'] or doc.xref_get_key(link['xref'],'StructParent')[0]!='null' for link in link_info['links']):raise DocumentError('Hay enlaces bloqueados, parciales o con acciones no compatibles.')
        images={item[7]:item for item in page.get_images(full=True) if item[9]==0};occurrences=page.get_image_info();image_index=0
        content=page.read_contents();total_bytes+=len(content)
        if total_bytes>16*1024*1024:raise DocumentError('El contenido de etiquetado supera 16 MB.')
        digest=hashlib.sha256(content).digest();parts=[];start=None;shown=False
        for op,args,token in operations(content):
            begin=args[0].start if args else token.start
            if op in ['BMC','BDC','EMC','MP','DP']:raise DocumentError('El etiquetado inicial necesita contenido directo sin marcas previas. Conserva el original.')
            if op=='Do':
                if start is None and len(args)==1 and args[0].kind=='name' and args[0].value not in images:
                    kind,value=doc.xref_get_key(page.xref,'Resources/XObject/'+args[0].value)
                    if kind=='xref' and doc.xref_get_key(int(value.split()[0]),'Subtype')==('name','/Form'):
                        from .tagging_forms import audit
                        audit(doc,int(value.split()[0]),form_budget)
                        parts.append({'start':begin,'end':token.end,'kind':'text','form_occurrence':True});continue
                if start is not None or len(args)!=1 or args[0].kind!='name' or args[0].value not in images or image_index>=len(occurrences):raise DocumentError('Solo se etiquetan imágenes directas; Forms y llamadas ambiguas necesitan otro tratamiento.')
                image=images[args[0].value];item=occurrences[image_index];image_index+=1
                if (image[2],image[3])!=(item['width'],item['height']):raise DocumentError('Las apariciones de imagen no tienen una asociación verificable.')
                image_pixels+=image[2]*image[3]
                if image[2]*image[3]>16_000_000 or image_pixels>64_000_000:raise DocumentError('Las imágenes superan el presupuesto de 16 MP por aparición/64 MP total.')
                rect=f.Rect(item['bbox'])*page.rotation_matrix
                if rect.is_empty or not page.rect.contains(rect):raise DocumentError('Una imagen queda recortada fuera de la página; requiere revisión especializada.')
                parts.append({'start':begin,'end':token.end,'kind':'image','box':[rect.x0,rect.y0,rect.width,rect.height],'text':f'Imagen {image_index} · {image[2]} × {image[3]} px'})
            elif op=='BT':
                if start is not None:raise DocumentError('Objeto de texto anidado.')
                start=begin;shown=False
            elif op in ['Tj','TJ',"'",'"']:
                if start is None:raise DocumentError('Texto fuera de un objeto BT/ET.')
                shown=True
            elif op=='ET':
                if start is None:raise DocumentError('Fin de objeto de texto sin inicio.')
                if shown:
                    parts.append({'start':start,'end':token.end,'kind':'text'})
                start=None
        if start is not None:raise DocumentError('Objeto de texto incompleto.')
        if image_index!=len(occurrences):raise DocumentError('No se pudo asociar cada aparición de imagen al contenido directo.')
        for part in parts:part['id']=hashlib.sha256(f'{page.number}:{part["start"]}:{part["end"]}:'.encode()+digest).hexdigest()[:32]
        total+=len(parts)
        if len(parts)>200 or total>500:raise DocumentError('Hasta 200 objetos de texto por página y 500 por documento.')
        result.append({'page':page.number,'content':content,'parts':parts,'links':link_info['links']})
    if not total:raise DocumentError('No se encontraron objetos directos compatibles. El etiquetado no realiza OCR.')
    return result


def build(doc,prepared,selection=None,language='es'):
    def new(value):
        x=doc.get_new_xref();doc.update_object(x,value);return x
    root=new('<< /Type /StructTreeRoot >>');document=new(f'<< /Type /StructElem /S /Document /P {root} 0 R /Lang {pdf_string(language)} >>');sections=[];parentnums=[];annotation_nums=[];next_key=len(prepared)
    for plan in prepared:
        page=doc[plan['page']];parts=plan['parts'];section=new(f'<< /Type /StructElem /S /Sect /P {document} 0 R /Pg {page.xref} 0 R >>');sections.append(section);refs=[];content=[];previous=0;mapping={}
        ordered=sorted(parts,key=lambda p:selection[p['id']]['position']) if selection else parts
        leaf_parents={};section_order=[];list_children={};current_list=None;tables={};rows={};list_stack=[];body_children={};previous_level=0
        for part in ordered:
            role=selection[part['id']]['role'] if selection else 'Figure' if part['kind']=='image' else 'P'
            if role in ['TH','TD']:
                current_list=None;list_stack=[];previous_level=0;settings=selection[part['id']];key=settings['table'];row=settings['row']
                if key not in tables:
                    tables[key]=new(f'<< /Type /StructElem /S /Table /P {section} 0 R /Pg {page.xref} 0 R >>');section_order.append(('node',tables[key]))
                    height=max(selection[p['id']]['row']+selection[p['id']]['rowspan']-1 for p in ordered if selection[p['id']]['role'] in ['TH','TD'] and selection[p['id']]['table']==key)
                    for r in range(1,height+1):rows[key,r]=new(f'<< /Type /StructElem /S /TR /P {tables[key]} 0 R /Pg {page.xref} 0 R /T (Fila {r}) >>')
                if (key,row) not in rows:rows[key,row]=new(f'<< /Type /StructElem /S /TR /P {tables[key]} 0 R /Pg {page.xref} 0 R >>')
                leaf_parents[part['id']]=rows[key,row]
            elif role=='LI':
                level=selection[part['id']].get('level',1)
                if level>previous_level+1:raise DocumentError('Las listas deben comenzar en nivel 1 y subir de uno en uno.')
                if level>len(list_stack):
                    parent=section if level==1 else previous_body
                    node=new(f'<< /Type /StructElem /S /L /P {parent} 0 R /Pg {page.xref} 0 R >>');list_children[node]=[]
                    if level==1:section_order.append(('node',node))
                    else:body_children[parent].append(('node',node))
                    list_stack.append(node)
                else:list_stack=list_stack[:level]
                current_list=list_stack[-1]
                item=new(f'<< /Type /StructElem /S /LI /P {current_list} 0 R /Pg {page.xref} 0 R >>');body=new(f'<< /Type /StructElem /S /LBody /P {item} 0 R /Pg {page.xref} 0 R >>')
                doc.xref_set_key(item,'K',f'[{body} 0 R]');list_children[current_list].append(item);leaf_parents[part['id']]=body;body_children[body]=[('part',part['id'])];previous_body=body;previous_level=level
            else:
                current_list=None;list_stack=[];previous_level=0;section_order.append(('part',part['id']))
        for key,node in tables.items():doc.xref_set_key(node,'K','['+' '.join(f'{r} 0 R' for (table,row),r in rows.items() if table==key)+']')
        row_children={r:[] for r in rows.values()};cell_nodes={};cell_mcids={}
        for node,children in list_children.items():doc.xref_set_key(node,'K','['+' '.join(f'{child} 0 R' for child in children)+']')
        for part in parts:
            settings=selection[part['id']] if selection else {'role':'Figure' if part['kind']=='image' else 'P','alt':''}
            role=settings['role'];is_item=role=='LI';role='P' if is_item else role;mcid=len(refs);parent=leaf_parents.get(part['id'],section)
            if role!='Artifact':
                alt=' /Alt '+pdf_string(settings.get('alt','')) if role in ['Figure','Link'] else ''
                kids=str(mcid)
                if role=='Link':kids=f'[{mcid} << /Type /OBJR /Obj {settings["annotation"]} 0 R /Pg {page.xref} 0 R >>]'
                attributes=''
                if role in ['TH','TD']:
                    attributes=' /A << /O /Table /RowSpan '+str(settings['rowspan'])+' /ColSpan '+str(settings['colspan'])+(' /Scope /'+settings['scope'] if role=='TH' else '')+' >>'
                cell_key=(settings['table'],settings['row'],settings['column']) if role in ['TH','TD'] else None
                identity=cell_nodes.get(cell_key) if cell_key is not None else None
                if identity is None:
                    identity=new(f'<< /Type /StructElem /S /{role} /P {parent} 0 R /Pg {page.xref} 0 R /K {kids}{alt}{attributes} >>')
                    if cell_key is not None:cell_nodes[cell_key]=identity;cell_mcids[identity]={}
                refs.append(identity);mapping[part['id']]=identity
                if cell_key is not None:cell_mcids[identity][part['id']]=mcid
                if role in ['TH','TD']:row_children[parent].append(identity)
                if role=='Link':
                    doc.xref_set_key(settings['annotation'],'StructParent',str(next_key));doc.xref_set_key(settings['annotation'],'Contents',pdf_string(settings['alt']))
                    annotation_nums.append(str(next_key)+f' {identity} 0 R');next_key+=1;doc.xref_set_key(page.xref,'Tabs','/S')
            before=plan['content'][previous:part['start']]
            if before.strip():content.extend([b'/Artifact BMC\n',before,b'\nEMC\n'])
            marker=b'/Artifact BMC\n' if role=='Artifact' else f'/{role} <</MCID {mcid}>> BDC\n'.encode()
            content.extend([marker,plan['content'][part['start']:part['end']],b'\nEMC\n']);previous=part['end']
        for node,children in body_children.items():doc.xref_set_key(node,'K','['+' '.join(f'{value if kind=="node" else mapping[value]} 0 R' for kind,value in children)+']')
        for node in row_children:doc.xref_set_key(node,'K','['+' '.join(f'{identity} 0 R' for identity in dict.fromkeys(mapping[p['id']] for p in ordered if leaf_parents.get(p['id'])==node))+']')
        for node,mcids in cell_mcids.items():doc.xref_set_key(node,'K','['+' '.join(str(mcids[p['id']]) for p in ordered if p['id'] in mcids)+']')
        tail=plan['content'][previous:]
        if tail.strip():content.extend([b'/Artifact BMC\n',tail,b'\nEMC\n'])
        stream=new('<<>>');doc.update_stream(stream,b''.join(content));page.set_contents(stream)
        section_refs=[value if kind=='node' else mapping[value] for kind,value in section_order if kind=='node' or value in mapping]
        doc.xref_set_key(section,'K','['+' '.join(f'{ref} 0 R' for ref in section_refs)+']')
        doc.xref_set_key(page.xref,'StructParents',str(page.number));parentnums.append(str(page.number)+' ['+' '.join(f'{r} 0 R' for r in refs)+']')
    doc.xref_set_key(document,'K','['+' '.join(f'{r} 0 R' for r in sections)+']')
    tree=new('<< /Nums ['+' '.join(parentnums+annotation_nums)+'] >>');doc.xref_set_key(root,'K',f'[{document} 0 R]');doc.xref_set_key(root,'ParentTree',f'{tree} 0 R');doc.xref_set_key(root,'ParentTreeNextKey',str(next_key))
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
                if part['kind']=='image':
                    entries.append({'id':part['id'],'page':page.number,'kind':'image','role':'Figure','alt':'','text':part['text'],'box':part['box']});continue
                if not text or len(text)>4000:raise DocumentError('Un objeto no tiene texto extraíble o supera 4000 caracteres. No se crearon etiquetas parciales.')
                rect=f.Rect()
                for box in item['boxes']:rect|=box
                rect*=page.rotation_matrix
                entries.append({'id':part['id'],'page':page.number,'kind':'text','form_occurrence':part.get('form_occurrence',False),'role':'P','text':text,'box':[rect.x0,rect.y0,rect.width,rect.height]})
            for link in plan['links']:
                rect=f.Rect(link['box']);targets=[]
                for entry in entries:
                    if entry['page']!=page.number:continue
                    x,y,w,h=entry['box'];box=f.Rect(x,y,x+w,y+h)
                    if (rect&box).get_area()>.1:targets.append((entry,box))
                if len(targets)!=1 or targets[0][0]['kind']!='text' or not (rect+(-1,-1,1,1)).contains(targets[0][1]):raise DocumentError('Cada enlace debe cubrir un único objeto de texto completo y no compartirlo con otros enlaces.')
                entry=targets[0][0];entry.update(kind='link',role='Link',alt=entry['text'] if len(entry['text'])<=2000 else '',annotation=link['xref'],destination=link.get('url') if link['destination']=='web' else 'Página '+str(link['target_page']+1))
        if sum(len(e['text']) for e in entries)>100000:raise DocumentError('La revisión supera 100000 caracteres.')
        return {'entries':entries,'pages':len(doc),'review_required':True,'scope':'Texto directo y Forms de solo texto como una unidad por aparición, imágenes por aparición y enlaces que cubren un objeto completo. Revisa alternativas, orden y gráficos decorativos. Los elementos consecutivos pueden formar listas revisadas de hasta seis niveles; permite tablas semánticas con celdas revisadas y no acredita PDF/UA.'}


def create(base,ops,entries,language='es',reviewed=False):
    from .accessibility import LANGUAGE
    if reviewed is not True:raise DocumentError('Revisa orden, roles y gráficos decorativos antes de crear las etiquetas.')
    if not isinstance(language,str) or len(language)>63 or not LANGUAGE.fullmatch(language):raise DocumentError('Idioma BCP 47 básico no válido.')
    info=candidates(base,ops);expected={e['id']:e for e in info['entries']}
    if not isinstance(entries,list) or len(entries)!=len(expected):raise DocumentError('Incluye todos los objetos de texto de la revisión actual.')
    selection={}
    for position,entry in enumerate(entries):
        if not isinstance(entry,dict) or not {'id','role'}<=set(entry)<= {'id','role','alt','table','row','column','rowspan','colspan','scope','level','merge_fragments'} or not isinstance(entry['id'],str) or entry['id'] not in expected or entry['id'] in selection or not isinstance(entry['role'],str):raise DocumentError('La revisión contiene objetos repetidos, obsoletos o roles no compatibles.')
        original=expected[entry['id']];kind=original['kind'];role=entry['role'];alt=entry.get('alt','')
        allowed=ROLES if kind=='text' else {'Figure','Artifact'} if kind=='image' else {'Link'}
        if role not in allowed:raise DocumentError('El rol no corresponde al tipo de objeto original.')
        if role in ['Figure','Link'] and (not isinstance(alt,str) or not 1<=len(alt.strip())<=2000 or any(ord(c)<32 and c not in '\n\t' or 0xd800<=ord(c)<=0xdfff for c in alt)):raise DocumentError('Escribe una alternativa o descripción de 1 a 2000 caracteres sin controles.')
        selection[entry['id']]={'role':role,'position':position,'alt':alt.strip() if role in ['Figure','Link'] else ''}
        if role=='LI':
            level=entry.get('level',1)
            if type(level) is not int or not 1<=level<=6:raise DocumentError('El nivel de lista debe estar entre 1 y 6.')
            selection[entry['id']]['level']=level
        elif 'level' in entry:raise DocumentError('El nivel corresponde solo a elementos de lista.')
        if role in ['TH','TD']:
            values={k:entry.get(k,1) for k in ['table','row','column','rowspan','colspan']}
            if any(type(v) is not int or not 1<=v<=100 for v in values.values()) or entry.get('scope','Column') not in ['Row','Column','Both']:raise DocumentError('Tabla, fila, columna y combinaciones deben estar entre 1 y 100; revisa el ámbito del encabezado.')
            if type(entry.get('merge_fragments',False)) is not bool:raise DocumentError('La agrupación de fragmentos de celda debe ser verdadera o falsa.')
            selection[entry['id']].update(**values,scope=entry.get('scope','Column'),merge_fragments=entry.get('merge_fragments',False))
        elif set(entry)&{'table','row','column','rowspan','colspan','scope','merge_fragments'}:raise DocumentError('Las coordenadas de tabla corresponden solo a celdas TH/TD.')
        if kind=='link':selection[entry['id']]['annotation']=original['annotation']
    page_order=[expected[e['id']]['page'] for e in entries]
    if page_order!=sorted(page_order):raise DocumentError('El orden se puede cambiar dentro de cada página, conservando la secuencia de páginas.')
    # Each table is a contiguous reviewed region with row-major, complete cells.
    groups={};closed=set();current=None
    for entry in entries:
        cfg=selection[entry['id']];key=(expected[entry['id']]['page'],cfg['table']) if cfg['role'] in ['TH','TD'] else None
        if current is not None and key!=current:closed.add(current)
        if key is not None:
            if key in closed:raise DocumentError('Cada tabla debe ocupar una secuencia continua de objetos revisados.')
            groups.setdefault(key,[]).append(cfg)
        current=key
    cell_count=0
    for cells in groups.values():
        occupied=set();unique={};positions=[(c['row'],c['column']) for c in cells]
        if positions!=sorted(positions):raise DocumentError('Ordena las celdas por fila y columna antes de crear la tabla.')
        for c in cells:
            key=c['row'],c['column']
            if key in unique:
                prior=unique[key]
                if not c['merge_fragments'] or not prior['merge_fragments'] or any(c[k]!=prior[k] for k in ['role','scope','rowspan','colspan']):raise DocumentError('Dos fragmentos comparten celda: confirma su agrupación y usa el mismo rol, ámbito y combinaciones.')
                continue
            unique[key]=c
            for r in range(c['row'],c['row']+c['rowspan']):
                for col in range(c['column'],c['column']+c['colspan']):
                    if r>100 or col>100 or (r,col) in occupied:raise DocumentError('Las celdas de tabla se superponen o exceden 100 filas/columnas.')
                    occupied.add((r,col))
        cell_count+=len(unique)
        height=max(r for r,c in occupied);width=max(c for r,c in occupied)
        if len(occupied)!=height*width:raise DocumentError('La tabla tiene huecos. Incluye cada celda, también las vacías, o revisa las combinaciones.')
        if not any(c['role']=='TH' for c in cells):raise DocumentError('Revisa al menos un encabezado TH por tabla.')
    edited=export_pdf(base,ops)
    with open_pdf(edited) as before,open_pdf(edited) as doc:
        prepared=plans(doc);build(doc,prepared,selection,language);result=doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
        with open_pdf(result) as saved:
            for a,b in zip(before,saved):
                scale=min(.75,math.sqrt(4_000_000/max(1,a.rect.get_area())))
                if a.get_text()!=b.get_text() or a.get_pixmap(matrix=f.Matrix(scale,scale),alpha=False).samples!=b.get_pixmap(matrix=f.Matrix(scale,scale),alpha=False).samples:raise DocumentError('Las etiquetas alteraron contenido o apariencia. Se conserva el original.')
    return result,{'tagged_objects':sum(v['role']!='Artifact' for v in selection.values()),'decorative_images':sum(v['role']=='Artifact' for v in selection.values()),'figures':sum(v['role']=='Figure' for v in selection.values()),'links':sum(v['role']=='Link' for v in selection.values()),'form_occurrences':sum(e.get('form_occurrence',False) for e in expected.values()),'tables':len(groups),'table_cells':cell_count,'table_fragments':sum(v['role'] in ['TH','TD'] for v in selection.values()),'list_items':sum(v['role']=='LI' for v in selection.values()),'pages':info['pages'],'language':language,'pdf_ua_validated':False}
