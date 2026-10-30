"""Bounded DOCX-to-PDF re-layout with explicit omissions; no Office execution."""
from collections import Counter
from io import BytesIO
from pathlib import Path,PurePosixPath
from zipfile import ZipFile,BadZipFile
from xml.etree import ElementTree as E
import hashlib,html,posixpath,re,unicodedata,zlib
from copy import deepcopy
import pymupdf as f
from .engine import DocumentError
from .content_tools import safe_web_url
from .images import image_dimensions
from .docx_styles import WordStyles
from .docx_headers import running_parts,PAGE_TOKEN,TOTAL_TOKEN
from .docx_fields import normalize_fields,PageFields,PREFIX
from .docx_tables import table_plan
from .docx_sections import sections
from .docx_notes import Notes,checked_text

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
FONTS=Path(__file__).resolve().parent.parent/'resources/fonts'
MAX_INPUT=10*1024*1024
MAX_EXPANDED=40*1024*1024
BREAK_TOKEN='REAPDF_MANUAL_PAGE_BREAK_042'


def tag(name):return '{'+W+'}'+name


def read_package(data):
    if not isinstance(data,bytes) or not data or len(data)>MAX_INPUT:raise DocumentError('Selecciona un DOCX de hasta 10 MB.')
    try:
        with ZipFile(BytesIO(data)) as z:
            files=z.infolist();names=[i.filename for i in files]
            if len(files)>400 or len(names)!=len(set(names)) or sum(i.file_size for i in files)>MAX_EXPANDED:raise DocumentError('El DOCX supera 400 recursos, 40 MB descomprimidos o contiene nombres repetidos.')
            for i in files:
                path=PurePosixPath(i.filename)
                if i.flag_bits&1 or path.is_absolute() or '..' in path.parts or '\\' in i.filename or any(ord(c)<32 for c in i.filename):raise DocumentError('El paquete DOCX contiene rutas o cifrado no compatibles.')
                if 'vbaproject' in i.filename.lower() or i.filename.startswith('word/embeddings/'):raise DocumentError('No se importan macros ni objetos incrustados de Office.')
            return {i.filename:z.read(i) for i in files if not i.is_dir()}
    except DocumentError:raise
    except (BadZipFile,RuntimeError,NotImplementedError,ValueError,zlib.error) as exc:raise DocumentError('No se pudo leer un paquete DOCX compatible.') from exc


def parse_xml(data):
    if not data or len(data)>2*1024*1024 or b'\0' in data or any(v in data.upper() for v in [b'<!DOCTYPE',b'<!ENTITY']):raise DocumentError('XML de Word no compatible: usa UTF-8, sin entidades y hasta 2 MB por parte.')
    try:root=E.fromstring(data)
    except E.ParseError as exc:raise DocumentError('El documento contiene XML de Word dañado.') from exc
    if sum(1 for _ in root.iter())>50000:raise DocumentError('Una parte de Word supera 50000 elementos XML.')
    return root


def import_docx(data,paper='source'):
    if not isinstance(paper,str) or paper not in ['source','A4','Letter']:raise DocumentError('Elige tamaño original, A4 o Carta.')
    package=read_package(data)
    types=parse_xml(package.get('[Content_Types].xml',b''))
    if not any(n.attrib.get('ContentType')=='application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml' for n in types):raise DocumentError('Solo se admite DOCX estándar, sin macros.')
    root=parse_xml(package.get('word/document.xml',b''));body=root.find(tag('body'))
    if body is None:raise DocumentError('No hay un cuerpo de documento Word compatible.')
    warnings=set();fonts=set();expected=[];images=[];pixels=0;paragraphs=0;tables=0;cells=0;characters=0
    styles=WordStyles(parse_xml(package["word/styles.xml"]) if "word/styles.xml" in package else None,parse_xml(package["word/numbering.xml"]) if "word/numbering.xml" in package else None,warnings)
    relationships={}
    if 'word/_rels/document.xml.rels' in package:
        for rel in parse_xml(package['word/_rels/document.xml.rels']):
            if rel.attrib.get('Id') in relationships:raise DocumentError('Relaciones Word repetidas.')
            relationships[rel.attrib.get('Id')]=rel.attrib
    if any(name.startswith('word/comments') for name in package):warnings.add('Los comentarios de Word no se incorporan.')
    notes=Notes(package,relationships,parse_xml,warnings)
    notes.active={kind for kind in ['footnote','endnote'] if any(n.tag==tag(kind+'Reference') for n in body.iter())}
    if any(any(token.encode() in raw for token in [PAGE_TOKEN,TOTAL_TOKEN,PREFIX,BREAK_TOKEN]) for raw in package.values()):raise DocumentError('El Word contiene un marcador interno reservado.')
    in_running=False;dynamic_fields=0;manual_breaks=0;page_fields=PageFields();complex_nodes=set();forced_cached=set();char_formats={}
    field_stats={"complex_fields":0,"complex_page_fields":0,"cached_fields":0}
    table_stats={"merged_tables":0,"combined_cells":0,"fallback_tables":0}
    if any(n.tag in {tag('del'),tag('ins'),tag('moveFrom'),tag('moveTo')} for n in body.iter()):raise DocumentError('Resuelve el control de cambios en Word antes de importar; no se elige una revisión por ti.')
    if any(n.tag in {tag('object'),tag('altChunk')} for n in body.iter()):raise DocumentError('El documento contiene objetos o contenido alternativo no compatible.')
    segments=sections(body,paper)
    size=segments[0]['size'];margins=segments[0]['margins']
    archive=f.Archive()
    for name in ['DejaVuSans.ttf','DejaVuSans-Bold.ttf','DejaVuSans-Oblique.ttf','DejaVuSans-BoldOblique.ttf']:archive.add(((FONTS/name).read_bytes(),name))
    face=f.Font(fontfile=str(FONTS/'DejaVuSans.ttf'))
    def text(value):
        nonlocal characters
        value=value or '';characters+=len(value)
        if characters>100000:raise DocumentError('El DOCX supera 100000 caracteres de contenido.')
        if any(ord(c)<32 and c not in '\n\t\r' or not face.has_glyph(ord(c),fallback=0) and not c.isspace() for c in value):raise DocumentError('El Word contiene caracteres que la fuente disponible no puede representar.')
        expected.append(value);return html.escape(value)
    def image(node):
        nonlocal pixels
        if any(el.tag=='{'+A+'}srcRect' and any(v not in ['0','0%',''] for v in el.attrib.values()) or el.tag=='{'+A+'}xfrm' and any(el.attrib.get(k,'0') not in ['0','false'] for k in ['rot','flipH','flipV']) for el in node.iter()):
            warnings.add('Imagen recortada, girada o reflejada: omitida para no exponer zonas fuera del recorte ni cambiar su apariencia.');return ''
        image_nodes=list(node.iter('{'+A+'}blip'))
        if not image_nodes:warnings.add('Dibujo vectorial, gráfico o forma de Word omitido.');return ''
        result=[]
        for blip in image_nodes:
            rel=relationships.get(blip.attrib.get('{'+R+'}embed'),{})
            if rel.get('TargetMode')=='External' or not rel.get('Target'):
                warnings.add('Imagen externa o sin recurso: omitida, sin descargarla.');continue
            target=posixpath.normpath(posixpath.join('word',rel['Target']))
            raw=package.get(target)
            if not raw or not(raw.startswith(b'\x89PNG\r\n\x1a\n') or raw.startswith(b'\xff\xd8\xff')):
                warnings.add('Imagen no PNG/JPEG o sin recurso: omitida.');continue
            w,h=image_dimensions(raw)
            if min(w,h)<=0:raise DocumentError('Dimensiones de imagen Word no válidas.')
            pixels+=w*h
            if w*h>20_000_000 or pixels>60_000_000 or len(images)>=50:raise DocumentError('Límite de 50 imágenes, 20 MP por imagen y 60 MP en total.')
            name=f'image{len(images)}'+('.png' if raw.startswith(b'\x89PNG') else '.jpg');archive.add((raw,name));images.append(name)
            extent=next(iter(node.iter('{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}extent')),None)
            try:width=int(extent.attrib['cx'])/12700 if extent is not None else w*72/150
            except (ValueError,KeyError):width=w*72/150
            if not 1<=width<=3000:raise DocumentError('Tamaño de imagen Word no válido.')
            result.append(f'<img src="{name}" style="width:{min(width,size[0]-margins[0]-margins[2],(size[1]-margins[1]-margins[3])*w/h):.2f}pt;max-width:100%"/>')
            if any(n.tag.endswith('}anchor') for n in node.iter()):warnings.add('Las imágenes flotantes se colocan en el flujo del texto.')
        return ''.join(result)
    def run(node,inherited,field_token=None):
        nonlocal manual_breaks
        style=[];props=styles.run(node,inherited)
        if props is not None:
            for name,css in [('b','font-weight:bold'),('i','font-style:italic'),('u','text-decoration:underline'),('strike','text-decoration:line-through')]:
                el=props.find(tag(name))
                if el is not None and el.attrib.get(tag('val')) not in ['0','false','off','none']:style.append(css)
            size=props.find(tag('sz'));color=props.find(tag('color'));font=props.find(tag('rFonts'))
            if size is not None:
                try:value=int(size.attrib[tag('val')])/2
                except (KeyError,ValueError):value=12
                if not 6<=value<=72:raise DocumentError('El Word contiene tamaño de texto fuera de 6–72 pt.')
                style.append(f'font-size:{value}pt')
            if color is not None and re.fullmatch('[0-9a-fA-F]{6}',color.attrib.get(tag('val'),'')):style.append('color:#'+color.attrib[tag('val')])
            if font is not None:fonts.update(v for k,v in font.attrib.items() if k in {tag('ascii'),tag('hAnsi')})
        parts=[]
        for child in node:
            if child.tag==tag('t'):parts.append(field_token if field_token is not None else text(child.text))
            elif child.tag in {tag('br'),tag('cr')}:
                expected.append(' ')
                if child.attrib.get(tag('type'))=='page':
                    if in_running:raise DocumentError('No se admiten saltos de página dentro de encabezados/pies Word.')
                    manual_breaks+=1;parts.append('</span>'+BREAK_TOKEN+'<span style="'+';'.join(style)+'">')
                else:parts.append('<br/>')
            elif child.tag in {tag('footnoteReference'),tag('endnoteReference')}:parts.append(notes.reference(child,in_running))
            elif child.tag in {tag('footnoteRef'),tag('endnoteRef')}:
                if not notes.inside:raise DocumentError('Marcador de nota fuera de su definición.')
            elif child.tag==tag('tab'):parts.append(text('    '));warnings.add('Las tabulaciones se convierten en espacios.')
            elif child.tag in {tag('drawing'),tag('pict')}:parts.append(image(child))
            elif child.tag in {tag('instrText'),tag('fldChar')}:warnings.add('Los campos automáticos se importan como su resultado de texto disponible, sin actualización.')
            elif child.tag not in {tag('rPr'),tag('lastRenderedPageBreak')}:warnings.add('Algunos elementos de texto de Word no compatibles se omiten.')
        return '<span style="'+';'.join(style)+'">'+''.join(parts)+'</span>'
    def paragraph(node):
        nonlocal paragraphs,dynamic_fields,manual_breaks
        paragraphs+=1
        if paragraphs>3000:raise DocumentError('Hasta 3000 párrafos por importación.')
        expected_start=len(expected)
        pieces=[];css=[];props,inherited=styles.paragraph(node)
        marker,depth=styles.marker(props)
        if marker:pieces.append(text(marker)+'&#160;');css.append(f'margin-left:{18*(depth+1)}pt')
        if props is not None:
            align=props.find(tag('jc'))
            if align is not None and align.attrib.get(tag('val')) in ['left','center','right','both']:css.append('text-align:'+{'both':'justify'}.get(align.attrib[tag('val')],align.attrib[tag('val')]))
            spacing=props.find(tag('spacing'));indent=props.find(tag('ind'))
            def twips(node,key,maximum=1440):
                raw=node.attrib.get(tag(key))
                try:value=int(raw)/20
                except (ValueError,TypeError):raise DocumentError('Espaciado o sangría Word no válidos.')
                if not -72<=value<=maximum:raise DocumentError('Espaciado o sangría Word fuera de límites.')
                return value
            if spacing is not None:
                for key,prop in [('before','margin-top'),('after','margin-bottom')]:
                    if tag(key) in spacing.attrib:
                        value=twips(spacing,key,360)
                        if value<0:raise DocumentError('El espaciado de párrafo no puede ser negativo.')
                        css.append(f'{prop}:{value}pt')
                if any(tag(k) in spacing.attrib for k in ['line','beforeAutospacing','afterAutospacing']):warnings.add('El interlineado y espaciado automático de Word se sustituyen por distribución compatible.')
            if indent is not None:
                for key,prop in [('left','margin-left'),('right','margin-right')]:
                    if tag(key) in indent.attrib:css.append(f'{prop}:{twips(indent,key)}pt')
                key='hanging' if tag('hanging') in indent.attrib else 'firstLine'
                if tag(key) in indent.attrib:css.append(f'text-indent:{twips(indent,key)*(-1 if key=="hanging" else 1)}pt')
                if any(tag(k) in indent.attrib for k in ['leftChars','rightChars','firstLineChars','hangingChars','start','end']):warnings.add('Sangrías por caracteres o direccionales no compatibles: revisa su distribución.')
            before=props.find(tag('pageBreakBefore'))
            if before is not None and before.attrib.get(tag('val'),'1') not in ['0','false','off']:
                if in_running:raise DocumentError('No se admiten saltos de página dentro de encabezados/pies Word.')
                css.append('page-break-before:always');manual_breaks+=1
            if any(props.find(tag(k)) is not None for k in ['keepNext','keepLines','tabs']):warnings.add('Las tabulaciones y agrupación de párrafos pueden cambiar durante la conversión.')
        def inline(child,allow_dynamic=True,depth=0):
            nonlocal dynamic_fields
            if depth>16:raise DocumentError('Demasiados campos o enlaces anidados en un párrafo Word.')
            if child.tag==tag('r'):return run(child,inherited)
            if child.tag==tag('hyperlink'):
                content=''.join(inline(r,allow_dynamic,depth+1) for r in child);rel=relationships.get(child.attrib.get('{'+R+'}id'),{})
                if BREAK_TOKEN in content:raise DocumentError('Divide el enlace Word antes de un salto manual de página para importarlo.')
                try:return '<a href="'+html.escape(safe_web_url(rel.get('Target')),quote=True)+'">'+content+'</a>'
                except DocumentError:warnings.add('Enlace no web o destino no compatible: se conserva solo su texto.');return content
            if child.tag==tag('fldSimple'):
                token=page_fields.register(child.attrib.get(tag('instr'))) if in_running and allow_dynamic and child not in forced_cached else None
                if token is not None:
                    replacement=E.Element(tag('r'));cached=child.find(tag('r'));properties=char_formats[child] if child in char_formats else cached.find(tag('rPr')) if cached is not None else None
                    if properties is not None:replacement.append(deepcopy(properties))
                    E.SubElement(replacement,tag('t'));dynamic_fields+=1
                    if dynamic_fields>500:raise DocumentError('Hasta 500 campos de página por documento Word.')
                    if child in complex_nodes:field_stats['complex_page_fields']+=1
                    return run(replacement,inherited,token)
                field_stats['cached_fields']+=1
                warnings.add('Los campos automáticos no compatibles conservan su resultado de texto disponible, sin actualización.')
                return ''.join(inline(r,False,depth+1) for r in child)
            if child.tag!=tag('pPr'):warnings.add('Elemento de párrafo no compatible omitido.')
            return ''
        pieces.extend(inline(child) for child in node)
        expected[expected_start:]=[''.join(expected[expected_start:])]
        fragments=''.join(pieces).split(BREAK_TOKEN)
        return ''.join('<p style="'+';'.join(css+(['page-break-before:always'] if index else []))+'">'+(fragment or '<br/>')+'</p>' for index,fragment in enumerate(fragments))
    def blocks(nodes):
        nonlocal tables,cells
        parts=[]
        for node in nodes:
            if node.tag==tag('p'):parts.append(paragraph(node))
            elif node.tag==tag('tbl'):
                tables+=1
                if tables>50:raise DocumentError('Hasta 50 tablas por importación.')
                physical=node.findall(tag('tr'));cells+=sum(len(row.findall(tag('tc'))) for row in physical)
                if cells>3000:raise DocumentError('Hasta 3000 celdas por importación.')
                plan,merged,reason=table_plan(node)
                def cell_content(cell):
                    if cell.find(tag('tbl')) is not None:warnings.add('Tabla anidada omitida.')
                    return ''.join(paragraph(p) for p in cell.findall(tag('p')))
                if plan is None:
                    table_stats['fallback_tables']+=1
                    warnings.add('Tabla no reconstruida ('+reason+'): se conserva como texto por filas, sin combinar celdas.')
                    parts.extend('<div>'+''.join(cell_content(cell) for cell in row.findall(tag('tc')))+'</div>' for row in physical)
                else:
                    if merged:table_stats['merged_tables']+=1
                    rows=[]
                    for row in plan:
                        content=[]
                        for cell in row:
                            if cell['skip']:continue
                            if cell['colspan']>1 or cell['rowspan']>1:table_stats['combined_cells']+=1
                            content.append(f'<td colspan="{cell["colspan"]}" rowspan="{cell["rowspan"]}">'+''.join(cell_content(tc) for tc in cell['nodes'])+'</td>')
                        rows.append('<tr>'+''.join(content)+'</tr>')
                    parts.append('<table>'+''.join(rows)+'</table>')
            elif node.tag!=tag('sectPr'):warnings.add('Contenido del cuerpo no compatible omitido.')
        return ''.join(parts)
    def render_running(root,rels):
        nonlocal relationships,in_running,complex_nodes,forced_cached,char_formats
        previous=relationships;relationships=rels;in_running=True
        root,complex_nodes,forced_cached,char_formats=normalize_fields(root);field_stats["complex_fields"]+=len(complex_nodes)
        counters=styles.counters;styles.counters={};start=len(expected)
        try:
            content=blocks(root);return content,expected[start:]
        finally:
            del expected[start:]
            relationships=previous;in_running=False;styles.counters=counters
    def render_note(root,rels):
        nonlocal relationships,complex_nodes,forced_cached,char_formats
        previous=relationships;old=(complex_nodes,forced_cached,char_formats);relationships=rels
        root,complex_nodes,forced_cached,char_formats=normalize_fields(root);field_stats['complex_fields']+=len(complex_nodes)
        counters=styles.counters;styles.counters={}
        try:return blocks(root)
        finally:relationships=previous;styles.counters=counters;complex_nodes,forced_cached,char_formats=old
    for segment_index,segment in enumerate(segments):
        notes.begin(segment['properties'],segment_index)
        size=segment['size'];margins=segment['margins'];section=segment['properties']
        page_fields=PageFields()
        segment['content']=blocks(segment['nodes'])
        segment['fields']=page_fields
        segment['running']=running_parts(package,section,relationships,parse_xml,render_running,warnings,page_fields)
    expected_references=sum(node.tag in {tag('footnoteReference'),tag('endnoteReference')} for node in body.iter())
    if expected_references!=len(notes.used):raise DocumentError('Hay referencias de notas en estructuras Word no compatibles. No se omiten sus notas ni se entrega un PDF incompleto.')
    notes.render(render_note)
    for index,segment in enumerate(segments):segment['content']+=notes.end_content(index,len(segments)-1)
    if len(segments)>1:warnings.discard('Encabezados/pies sin referencia en la sección importada no se incorporan.')
    if not characters and not images and not dynamic_fields:raise DocumentError('No hay texto ni imágenes compatibles para importar.')
    css='''@font-face{font-family:Reapdf;src:url(DejaVuSans.ttf)}@font-face{font-family:Reapdf;src:url(DejaVuSans-Bold.ttf);font-weight:bold}@font-face{font-family:Reapdf;src:url(DejaVuSans-Oblique.ttf);font-style:italic}@font-face{font-family:Reapdf;src:url(DejaVuSans-BoldOblique.ttf);font-weight:bold;font-style:italic}body{font-family:Reapdf;font-size:12pt;margin:0}p{margin:0 0 8pt 0}table{border-collapse:collapse;width:100%;margin-bottom:10pt}td{border:0.5pt solid #888;padding:4pt}a{color:#23644f}.word-note p{margin:0 0 4pt 0}.word-note{font-size:10pt;margin-bottom:4pt}.word-note-label{font-weight:bold}.word-footnotes{border-top:.5pt solid #888;padding-top:4pt}.word-endnotes{margin-top:14pt}'''
    section_report=[];page_labels=[];total=0;previous_format='decimal'
    try:
        for index,segment in enumerate(segments):
            width,height=segment['size'];left,top,right,bottom=segment['margins']
            running=segment['running'];fields=segment['fields'];section=segment['properties']
            fields.start=1 if index==0 else segments[index-1]['fields'].start+segments[index-1]['count']
            fields.format=previous_format
            # An omitted start continues the previous section; an explicit start restarts it.
            numbering=section.find(tag('pgNumType'))
            if numbering is not None:
                numbering=deepcopy(numbering)
                if tag('start') not in numbering.attrib:numbering.set(tag('start'),str(fields.start))
                if tag('fmt') not in numbering.attrib:numbering.set(tag('fmt'),fields.format)
                configured=E.Element(tag('sectPr'));configured.append(numbering);fields.configure(configured)
            previous_format=fields.format
            top,bottom=running.prepare(width,height,left,right,top,bottom,css,archive)
            note_plan=notes.prepare(index,segment['content'],css,archive,width,height,left,top,right,bottom,50-total)
            story=note_plan['story'];count=[note_plan['count']]
            segment.update(story=story,count=count[0],offset=total,note_plan=note_plan)
            # Store geometry rather than a closure over the loop's variables.
            segment['frame']=(width,height,left,top,right,bottom)
            from .docx_fields import number_label
            number_label(fields.start+count[0]-1,fields.format)
            page_labels.append({'startpage':total,'prefix':'','style':{'decimal':'D','upperRoman':'R','lowerRoman':'r','upperLetter':'A','lowerLetter':'a'}[fields.format],'firstpagenum':fields.start})
            section_report.append({'section':index+1,'first_page':total+1,'pages':count[0],'width':width,'height':height,'margins':list(segment['margins']),'number_start':fields.start,'number_format':fields.format,'header_footer_templates':len(running.templates)})
            total+=count[0]
        with f.open() as doc:
            all_positions=[]
            for segment in segments:
                width,height,left,top,right,bottom=segment['frame'];running=segment['running']
                def rectangle(n,filled):
                    if n>=segment['count']:raise DocumentError('La paginación Word cambió durante la conversión.')
                    return f.Rect(0,0,width,height),f.Rect(left,top,width-right,height-bottom-segment['note_plan']['reserves'].get(n,0)),None
                actual_refs={}
                def position(node):
                    if node.id in segment['note_plan']['ref_pages'] and node.open_close&1 and not f.Rect(node.rect).is_empty:actual_refs.setdefault(node.id,node.page_num-1)
                    node.page_num+=segment['offset'];all_positions.append(node)
                active_page=[0]
                def pagefn(number,box,device,after):
                    # Story.write reports the next number when closing a prior
                    # device. Bind bottom notes to the device actually opened.
                    if not after:
                        active_page[0]=number;running.draw(number,total,device,physical_page=segment['offset']+number,section_total=segment['count'])
                    else:notes.draw(segment['note_plan'],active_page[0],width,height,left,right,bottom,css,archive,device,position)
                stream=BytesIO();writer=f.DocumentWriter(stream)
                try:segment['story'].write(writer,rectangle,positionfn=position,pagefn=pagefn)
                finally:writer.close()
                with f.open(stream=stream.getvalue()) as part:
                    if len(part)!=segment['count'] or actual_refs!=segment['note_plan']['ref_pages']:raise DocumentError('La paginación de texto/notas Word cambió durante la conversión.')
                    doc.insert_pdf(part)
                for node in running.positions:node.page_num+=segment['offset'];all_positions.append(node)
            for node in all_positions:
                if node.href and f.Rect(node.rect).is_empty:node.href=None
            f.Story.add_pdf_links(doc,all_positions)
            page_labels_preserved=any(s['properties'].find(tag('pgNumType')) is not None for s in segments) or len(segments)>1
            if page_labels_preserved:doc.set_page_labels(page_labels)
            doc.set_metadata({'title':'Importado desde Word','producer':'Reapdf / DOCX compatible'})
            result=doc.tobytes(garbage=4,deflate=True);actual=checked_text(doc,all_positions) if notes.used else '\n'.join(p.get_text() for p in doc);pages=len(doc)
    except DocumentError:raise
    except Exception as exc:raise DocumentError('No se pudo distribuir el contenido Word; revisa tablas, imágenes y tamaños.') from exc
    if len(result)>30*1024*1024:raise DocumentError('El PDF importado supera 30 MB.')
    def tokens(value):
        value=re.sub(r'-\s*\n\s*','',unicodedata.normalize('NFKC',value).replace('\u00ad',''))
        return Counter(re.findall(r'\w+',value,flags=re.UNICODE))
    missing=tokens(' '.join(expected+[value for segment in segments for value in segment['running'].expected]))-tokens(actual)
    if missing and notes.used:raise DocumentError('La comprobación detectó texto perdido en el documento con notas. No se entrega un PDF incompleto.')
    if missing and table_stats['merged_tables']:raise DocumentError('La comprobación detectó texto perdido en una tabla combinada. Simplifica la tabla antes de importar; no se entrega un PDF incompleto.')
    if missing:warnings.add('La comprobación de texto detectó diferencias; revisa los fragmentos indicados y el PDF completo.')
    warnings.add('Las fuentes originales se sustituyen por DejaVu Sans. La paginación y el diseño pueden cambiar.')
    report={'schema':'reapdf-docx-import-1','source_sha256':hashlib.sha256(data).hexdigest(),'pdf_sha256':hashlib.sha256(result).hexdigest(),'pages':pages,'paragraphs':paragraphs,'tables':tables,'cells':cells,'images':len(images),'characters':characters,'manual_page_breaks':manual_breaks,'sections':section_report,'section_count':len(segments),'header_footer_templates':sum(len(s['running'].templates) for s in segments),'header_footer_instances':sum(s['running'].drawn for s in segments),'page_fields':dynamic_fields,**notes.report(),**field_stats,**table_stats,'page_number_start':segments[0]['fields'].start,'page_number_format':segments[0]['fields'].format,'page_labels_preserved':page_labels_preserved,'styles_applied':len(styles.used),'list_items':styles.list_items,'fonts_replaced':sorted(fonts),'warnings':sorted(warnings),'missing_words':list(missing)[:30],'text_check_passed':not missing,'layout_preserved':False,'output_bytes':len(result)}
    return result,report
