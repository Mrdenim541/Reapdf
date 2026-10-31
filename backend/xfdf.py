"""Bounded XFDF interchange for native geometry and compatible AcroForm values.

No scripts, external resources, rich text, DTDs or entities are interpreted.
Import is additive for annotations, idempotent for identical imported records,
and rejects a conflicting native name rather than overwriting a review.
"""
import hashlib,json,re
import xml.etree.ElementTree as E
import pymupdf as f
from .engine import DocumentError,open_pdf,export_pdf,finite
from .forms import form_model
from .form_structure import expand_values,pdf_string
from .existing_annotations import display_rgb

NS='http://ns.adobe.com/xfdf/'
PRIVATE='https://reapdf.local/xfdf/1'
E.register_namespace('',NS);E.register_namespace('reapdf',PRIVATE)
TYPES={f.PDF_ANNOT_TEXT:'text',f.PDF_ANNOT_SQUARE:'square',f.PDF_ANNOT_CIRCLE:'circle',f.PDF_ANNOT_LINE:'line',f.PDF_ANNOT_INK:'ink',f.PDF_ANNOT_POLY_LINE:'polyline',f.PDF_ANNOT_POLYGON:'polygon',f.PDF_ANNOT_HIGHLIGHT:'highlight',f.PDF_ANNOT_UNDERLINE:'underline',f.PDF_ANNOT_STRIKE_OUT:'strikeout',f.PDF_ANNOT_SQUIGGLY:'squiggly',f.PDF_ANNOT_FREE_TEXT:'freetext'}
MAX_XML=2*1024*1024
ENDS=['None','Square','Circle','Diamond','OpenArrow','ClosedArrow','Butt','ROpenArrow','RClosedArrow','Slash']


def tag(value):return '{'+NS+'}'+value

def binding(base,ops):return hashlib.sha256(base+json.dumps(ops,sort_keys=True,ensure_ascii=True).encode()).hexdigest()

def clean(value,limit=4000):
    if not isinstance(value,str) or len(value)>limit or any(ord(c)<32 and c not in '\n\r\t' for c in value):raise DocumentError('Texto XFDF fuera de límites o con caracteres XML no válidos.')
    return value

def number(v):return format(float(v),'.7g')

def coords(points):return ','.join(number(v) for p in points for v in p)

def annotation_node(doc,page,a):
    if a.type[0] not in TYPES or any(doc.xref_get_key(a.xref,k)[0]!='null' for k in ['Measure','OC','A','AA','ReapdfMeasurement','ReapdfMeasureLabel']):raise DocumentError('Anotación de tipo o estructura no compatible con este intercambio.')
    name=TYPES[a.type[0]];matrix=~page.transformation_matrix;rect=a.rect*matrix
    attrs={'page':str(page.number),'rect':','.join(number(v) for v in rect),'name':clean(a.info.get('id','') or 'reapdf-'+str(a.xref),100),'title':clean(a.info.get('title',''),100),'color':'#'+''.join(f'{round(v*255):02X}' for v in display_rgb(a.colors.get('stroke') or [])),'opacity':number(a.opacity if a.opacity>=0 else 1),'width':number(max(.25,a.border.get('width',1)))}
    from .xfdf_appearance import export_attributes
    attrs.update(export_attributes(doc,a,name))
    from .xfdf_threads import attributes
    attrs.update(attributes(doc,page,a))
    if name=='line':
        vertices=a.vertices
        if len(vertices)!=2:raise DocumentError('Línea sin extremos compatibles.')
        attrs.update(start=coords([f.Point(vertices[0])*matrix]),end=coords([f.Point(vertices[1])*matrix]))
        ends=a.line_ends or (0,0)
        attrs.update(head=ENDS[ends[0]],tail=ENDS[ends[1]])
    if name=='polyline':
        ends=a.line_ends or (0,0);attrs.update(head=ENDS[ends[0]],tail=ENDS[ends[1]])
    node=E.Element(tag(name),attrs);E.SubElement(node,tag('contents')).text=clean(a.info.get('content',''))
    if name in ['highlight','underline','strikeout','squiggly']:
        if len(a.vertices)%4:raise DocumentError('Cuadriláteros no compatibles.')
        node.set('coords',coords([f.Point(p)*matrix for p in a.vertices]))
    elif name in ['polyline','polygon']:E.SubElement(node,tag('vertices')).text=coords([f.Point(p)*matrix for p in a.vertices])
    elif name=='ink':
        gestures=E.SubElement(node,tag('inklist'))
        for path in a.vertices:E.SubElement(gestures,tag('gesture')).text=coords([f.Point(p)*matrix for p in path])
    return node


def export(base,ops,include_annotations=True,include_fields=True):
    with open_pdf(base) as doc:
        if not doc.permissions&f.PDF_PERM_COPY:raise DocumentError('El PDF no permite exportar estos datos.')
    root=E.Element(tag('xfdf'),{f'{{{PRIVATE}}}source_hash':binding(base,ops),'{http://www.w3.org/XML/1998/namespace}space':'preserve'});annots=E.SubElement(root,tag('annots'));fields=E.SubElement(root,tag('fields'));report={'annotations':0,'skipped_annotations':0,'fields':0,'skipped_fields':0}
    with open_pdf(export_pdf(base,ops)) as doc:
        if include_annotations:
            for page in doc:
                rotation=page.rotation;page.set_rotation(0)
                for a in page.annots() or []:
                    try:node=annotation_node(doc,page,a)
                    except DocumentError:report['skipped_annotations']+=1;continue
                    if report['annotations']>=500:raise DocumentError('Hasta 500 anotaciones por intercambio.')
                    annots.append(node);report['annotations']+=1
                page.set_rotation(rotation)
        if include_annotations:
            while True:
                names={(node.get('page'),node.get('name')) for node in annots};orphans=[node for node in annots if node.get('inreplyto') is not None and (node.get('page'),node.get('inreplyto')) not in names]
                if not orphans:break
                for node in orphans:annots.remove(node);report['annotations']-=1;report['skipped_annotations']+=1
            from .xfdf_threads import ordered
            sorted_nodes=ordered(list(annots),set());annots[:]=sorted_nodes
        if include_fields:
            groups=set()
            for row in form_model(doc)['fields']:
                if row['group'] in groups:continue
                groups.add(row['group'])
                if not row['editable']:report['skipped_fields']+=1;continue
                value=row['value']
                if row['kind']=='checkbox':
                    page=doc[row['page']];widget=page.load_widget(row['xref']);value=widget.on_state() if value else 'Off'
                node=E.SubElement(fields,tag('field'),{'name':clean(row['name'],200)});E.SubElement(node,tag('value')).text=clean(value);report['fields']+=1
    data=E.tostring(root,encoding='utf-8',xml_declaration=True)
    if len(data)>MAX_XML:raise DocumentError('Los datos XFDF superan 2 MB.')
    return data,report


def parse(data):
    if not isinstance(data,bytes) or not data or len(data)>MAX_XML:raise DocumentError('El XFDF debe medir de 1 byte a 2 MB.')
    try:xml=data.decode('utf-8-sig')
    except UnicodeError as exc:raise DocumentError('Usa un XFDF codificado en UTF-8.') from exc
    if '\x00' in xml or '<!DOCTYPE' in xml.upper() or '<!ENTITY' in xml.upper():raise DocumentError('No se admiten declaraciones DTD ni entidades XML.')
    declaration=re.match(r'\s*<\?xml[^>]*encoding=[\"\']([^\"\']+)',xml,re.I)
    if declaration and declaration[1].lower() not in ['utf-8','utf8']:raise DocumentError('Usa un XFDF codificado en UTF-8.')
    try:root=E.fromstring(xml)
    except (E.ParseError,ValueError) as exc:raise DocumentError('XML XFDF no válido.') from exc
    if root.tag!=tag('xfdf'):raise DocumentError('El archivo no es XFDF con el espacio de nombres esperado.')
    nodes=0
    def walk(node,depth):
        nonlocal nodes
        nodes+=1
        if depth>16 or nodes>10000:raise DocumentError('El XML supera los límites de anidación o nodos.')
        for child in node:walk(child,depth+1)
    walk(root,0);return root


def values(text,count=None):
    if not isinstance(text,str) or len(text)>100000:raise DocumentError('Coordenadas XFDF no válidas.')
    try:result=[float(v) for v in re.split(r'[,;\s]+',text.strip()) if v]
    except ValueError as exc:raise DocumentError('Coordenadas XFDF no numéricas.') from exc
    if len(result)>20000 or any(not finite(v) or abs(v)>1e7 for v in result) or count is not None and len(result)!=count:raise DocumentError('Coordenadas XFDF fuera de rango.')
    return result


def signature(node):
    def content(n):return [n.tag,sorted(n.attrib.items()),n.text or '',[content(c) for c in n]]
    return hashlib.sha256(json.dumps(content(node),ensure_ascii=True).encode()).hexdigest()


def import_data(base,ops,data,confirm=False,preview=False):
    root=parse(data)
    if root.get('{'+PRIVATE+'}source_hash')!=binding(base,ops) and confirm is not True:raise DocumentError('XFDF de otro origen. Verifica el documento y confirma expresamente antes de importar.')
    if any(child.tag not in [tag('annots'),tag('fields'),tag('f'),tag('ids')] for child in root):raise DocumentError('El XFDF contiene elementos no compatibles.')
    snapshot=export_pdf(base,ops)
    with open_pdf(snapshot) as doc:
        if doc.get_sigflags()>0:raise DocumentError('No se importan datos sobre un PDF firmado.')
        annotation_nodes=root.findall('./'+tag('annots')+'/*');field_nodes=root.findall('./'+tag('fields')+'/'+tag('field'))
        if len(annotation_nodes)>500:raise DocumentError('Hasta 500 anotaciones por importación.')
        if annotation_nodes and not doc.permissions&f.PDF_PERM_ANNOTATE:raise DocumentError('El PDF no permite anotar.')
        imported_fields={}
        def fields(nodes,prefix='',depth=0):
            for node in nodes:
                name=clean(node.get('name',''),200);name=prefix+'.'+name if prefix else name
                children=node.findall(tag('field'));entries=node.findall(tag('value'))
                if children:
                    if entries:raise DocumentError('No mezcles valor y campos descendientes.')
                    fields(children,name,depth+1)
                else:
                    if not name or len(entries)!=1 or name in imported_fields:raise DocumentError('Campo XFDF repetido o sin un valor único.')
                    imported_fields[name]=clean(entries[0].text or '')
                    if len(imported_fields)>500:raise DocumentError('Hasta 500 campos por importación.')
        fields(field_nodes)
        incoming=[];rows=form_model(doc)['fields'];known={r['name'] for r in rows}
        for name,value in imported_fields.items():
            if name not in known:raise DocumentError('Un campo importado no existe en este PDF: '+name)
            for row in [r for r in rows if r['name']==name]:
                if not row['editable']:raise DocumentError(row['reason'])
                converted=value
                if row['kind']=='checkbox':
                    page=doc[row['page']];widget=page.load_widget(row['xref']);on=widget.on_state()
                    if value not in ['Off',on]:raise DocumentError('Estado de casilla no compatible: '+name)
                    converted=value==on
                incoming.append({'page':row['page'],'xref':row['xref'],'value':converted})
        # Validate/apply fields first on this unpublished snapshot. A later
        # annotation error still publishes no document.
        if incoming:
            filled=export_pdf(snapshot,[{'type':'form_fill','page':0,'values':expand_values(rows,incoming)}])
            return _annotations(filled,annotation_nodes,len(imported_fields),preview)
        return _annotations(snapshot,annotation_nodes,0,preview)


def _annotations(snapshot,nodes,field_count,preview):
    report={'annotations':0,'duplicates':0,'fields':field_count}
    with open_pdf(snapshot) as doc:
        existing_names={};digests=set();parent_refs={}
        for page in doc:
            rotation=page.rotation;page.set_rotation(0)
            for a in page.annots() or []:
                native_name=a.info.get('id','') or 'reapdf-'+str(a.xref)
                if (page.number,native_name) in parent_refs:raise DocumentError('Nombres de anotación ambiguos en el PDF destino.')
                parent_refs[page.number,native_name]=a.xref
                kind,value=doc.xref_get_key(a.xref,'ReapdfXFDFDigest')
                if kind=='string':digests.add(value)
                try:node=annotation_node(doc,page,a);existing_names[(page.number,node.get('name'))]=signature(node)
                except DocumentError:
                    name=a.info.get('id','')
                    if name:existing_names[(page.number,name)]=None
            page.set_rotation(rotation)
        from .xfdf_threads import ordered,apply as apply_thread
        nodes=ordered(nodes,set(parent_refs))
        for node in nodes:
            if node.tag not in [tag(t) for t in TYPES.values()]:raise DocumentError('Anotación XFDF no compatible; no se importa parcialmente.')
            if node.find(tag('contents-richtext')) is not None:raise DocumentError('Texto enriquecido XFDF requiere otra importación.')
            sig=signature(node)
            if sig in digests:report['duplicates']+=1;continue
            try:number_page=int(node.get('page',''))
            except ValueError as exc:raise DocumentError('Página XFDF no válida.') from exc
            if not 0<=number_page<len(doc):raise DocumentError('La página XFDF no existe.')
            name=clean(node.get('name',''),100)
            if name and (number_page,name) in existing_names:
                if existing_names[(number_page,name)]==sig:report['duplicates']+=1;continue
                raise DocumentError('Existe una anotación con el mismo nombre y distinto contenido. Resuelve el conflicto antes de importar.')
            page=doc[number_page];rotation=page.rotation;page.set_rotation(0);matrix=page.transformation_matrix
            rect=f.Rect(values(node.get('rect',''),4))*matrix
            if rect.is_empty or not (page.rect+(-2,-2,2,2)).contains(rect):raise DocumentError('La anotación XFDF sale de la página.')
            kind=node.tag.split('}')[-1];content=clean(node.findtext(tag('contents'),''));author=clean(node.get('title',''),100)
            color=node.get('color','#000000')
            if not re.fullmatch(r'#[0-9a-fA-F]{6}',color):raise DocumentError('Color XFDF no compatible.')
            rgb=[int(color[i:i+2],16)/255 for i in [1,3,5]];opacity=values(node.get('opacity','1'),1)[0];width=values(node.get('width','1'),1)[0]
            from .xfdf_appearance import parse_attributes
            appearance=parse_attributes(node,kind)
            if not 0<=opacity<=1 or not (0 if kind=='freetext' else .25)<=width<=50:raise DocumentError('Opacidad o grosor XFDF fuera de límites.')
            def path(raw,minimum):
                flat=values(raw)
                if len(flat)%2 or len(flat)<minimum*2:raise DocumentError('Trazado XFDF no válido.')
                pts=[f.Point(flat[i],flat[i+1])*matrix for i in range(0,len(flat),2)]
                if any(not page.rect.contains(p) for p in pts):raise DocumentError('Un vértice sale de la página.')
                return pts
            if kind=='freetext':a=page.add_freetext_annot(rect,content,fontsize=appearance['size'],fontname=appearance['font'],text_color=appearance['text_color'],fill_color=appearance['fill'],align=appearance['align'],rotate=appearance['rotation'],border_width=width)
            elif kind=='text':
                a=page.add_text_annot(rect.tl,content,icon=appearance['icon']);a.set_rect(rect);doc.xref_set_key(a.xref,'Open','true' if appearance['open']=='yes' else 'false')
            elif kind=='square':
                fringe=appearance.get('fringe',[max(1,width/2)]*4);a=page.add_rect_annot(rect+(fringe[0],fringe[3],-fringe[2],-fringe[1]))
            elif kind=='circle':
                fringe=appearance.get('fringe',[max(1,width/2)]*4);a=page.add_circle_annot(rect+(fringe[0],fringe[3],-fringe[2],-fringe[1]))
            elif kind=='line':
                pts=path(node.get('start','')+','+node.get('end',''),2)
                if len(pts)!=2:raise DocumentError('La línea XFDF requiere dos extremos.')
                a=page.add_line_annot(*pts)
                if any(node.get(key,'None') not in ENDS for key in ['head','tail']):raise DocumentError('Extremos de línea XFDF no compatibles.')
                ends=[ENDS.index(node.get(key,'None')) for key in ['head','tail']]
                a.set_line_ends(*ends)
            elif kind in ['polyline','polygon']:
                pts=path(node.findtext(tag('vertices'),''),3 if kind=='polygon' else 2);a=page.add_polygon_annot(pts) if kind=='polygon' else page.add_polyline_annot(pts)
                if kind=='polyline':
                    if any(node.get(k,'None') not in ENDS for k in ['head','tail']):raise DocumentError('Extremos de polilínea no compatibles.')
                    a.set_line_ends(*[ENDS.index(node.get(k,'None')) for k in ['head','tail']])
            elif kind=='ink':
                gestures=node.findall('./'+tag('inklist')+'/'+tag('gesture'))
                if not 1<=len(gestures)<=100:raise DocumentError('Trazos de lápiz XFDF fuera de límites.')
                a=page.add_ink_annot([[list(p) for p in path(g.text or '',2)] for g in gestures])
            else:
                pts=path(node.get('coords',''),4)
                if len(pts)%4:raise DocumentError('Cuadriláteros XFDF incompletos.')
                quads=[f.Quad(pts[i:i+4]) for i in range(0,len(pts),4)]
                if any(not q.is_convex for q in quads):raise DocumentError('Cuadrilátero XFDF no convexo.')
                a=({'highlight':page.add_highlight_annot,'underline':page.add_underline_annot,'strikeout':page.add_strikeout_annot,'squiggly':page.add_squiggly_annot}[kind])(quads)
            a.set_info(content=content,title=author,**appearance['info'])
            if kind!='freetext':a.set_colors(stroke=rgb,fill=appearance['fill'])
            from .xfdf_appearance import apply_border
            a.set_opacity(opacity);apply_border(doc,a,width,appearance['dashes']);a.set_flags(appearance['flags']);a.update()
            if kind=='freetext':
                from .xfdf_styled_text import apply as styled_appearance
                styled_appearance(doc,a,appearance,rect,content,width,opacity)
            if name:
                doc.xref_set_key(a.xref,'NM',pdf_string(name));existing_names[(number_page,name)]=sig
            apply_thread(doc,a,node,parent_refs,number_page)
            if name:parent_refs[number_page,name]=a.xref
            doc.xref_set_key(a.xref,'ReapdfXFDFDigest',pdf_string(sig));digests.add(sig);report['annotations']+=1;page.set_rotation(rotation)
        if not report['annotations'] and not report['fields'] and not report['duplicates']:raise DocumentError('El XFDF no contiene anotaciones o valores compatibles.')
        return report if preview else (doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True),report)
