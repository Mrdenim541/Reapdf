"""Dependency-free OOXML export of editable PDF text with explicit fidelity limits."""
from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED
import hashlib,re
from xml.etree.ElementTree import Element,SubElement,tostring,register_namespace
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError,finite
from .document_tools import selected_pages
from .docx_content import page_images,page_tables
from .docx_links import page_links,span_link

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
register_namespace('w',W)
MAX_CHARACTERS=100000
MAX_RUNS=20000


def tag(name):return '{'+W+'}'+name


def element(parent,name,attrs=None):return SubElement(parent,tag(name),{tag(k):str(v) for k,v in (attrs or {}).items()})


def clean(value):
    return ''.join(c if ord(c) in [9,10,13] or 32<=ord(c)<=0xd7ff or 0xe000<=ord(c)<=0xfffd or 0x10000<=ord(c)<=0x10ffff else '\ufffd' for c in str(value))


def xml(node):return tostring(node,encoding='utf-8',xml_declaration=True)


def section(parent,width,height):
    props=element(parent,'sectPr');factor=min(1,1584/max(width,height));width=max(72,width*factor);height=max(72,height*factor)
    element(props,'type',{'val':'nextPage'});element(props,'pgSz',{'w':round(width*20),'h':round(height*20),'orient':'landscape' if width>height else 'portrait'})
    margin=round(min(36,min(width,height)/8)*20)
    element(props,'pgMar',{'top':margin,'right':margin,'bottom':margin,'left':margin,'header':0,'footer':0,'gutter':0})


R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
RPKG='http://schemas.openxmlformats.org/package/2006/relationships'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
WP='http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
PIC='http://schemas.openxmlformats.org/drawingml/2006/picture'
for prefix,uri in [('r',R),('a',A),('wp',WP),('pic',PIC)]:register_namespace(prefix,uri)


def text_run(parent,text,span=None):
    run=element(parent,'r')
    if span:
        props=element(run,'rPr');name=re.sub(r'^[A-Z]{6}\+','',span['font'])
        for prefix,family in [('Helvetica','Arial'),('Times','Times New Roman'),('Courier','Courier New')]:
            if name.startswith(prefix):name=family;break
        name=clean(name)[:63] or 'Arial'
        element(props,'rFonts',{'ascii':name,'hAnsi':name,'cs':name})
        size=span['size'] if finite(span['size']) else 11
        element(props,'sz',{'val':max(2,min(288,round(size*2)))})
        if span['flags']&16:element(props,'b')
        if span['flags']&2:element(props,'i')
        element(props,'color',{'val':f"{span['color']&0xffffff:06X}"})
    node=element(run,'t');node.set('{http://www.w3.org/XML/1998/namespace}space','preserve');node.text=clean(text)


def image_paragraph(body,item,index,page):
    p=element(body,'p');run=element(p,'r');drawing=element(run,'drawing')
    def add(parent,uri,name,attrs=None):return SubElement(parent,'{'+uri+'}'+name,{k:str(v) for k,v in (attrs or {}).items()})
    factor=min(1,1584/max(page.rect.width,page.rect.height))
    width=max(72,page.rect.width*factor);height=max(72,page.rect.height*factor);margin=min(36,min(width,height)/8)
    box=item['rect'];scale=min(factor,(width-2*margin)/box.width,(height-2*margin)/box.height)
    cx=max(1,round(box.width*scale*12700));cy=max(1,round(box.height*scale*12700))
    inline=add(drawing,WP,'inline',{'distT':0,'distB':0,'distL':0,'distR':0});add(inline,WP,'extent',{'cx':cx,'cy':cy})
    add(inline,WP,'docPr',{'id':index,'name':f'Imagen {index}','descr':f'Imagen extraída de la página {page.number+1}'})
    lock=add(inline,WP,'cNvGraphicFramePr');add(lock,A,'graphicFrameLocks',{'noChangeAspect':1})
    graphic=add(inline,A,'graphic');data=add(graphic,A,'graphicData',{'uri':PIC});pic=add(data,PIC,'pic')
    props=add(pic,PIC,'nvPicPr');add(props,PIC,'cNvPr',{'id':index,'name':f'image{index}.{item["ext"]}'});add(props,PIC,'cNvPicPr')
    fill=add(pic,PIC,'blipFill');add(fill,A,'blip',{'{'+R+'}embed':f'rIdImage{index}'});add(add(fill,A,'stretch'),A,'fillRect')
    props=add(pic,PIC,'spPr');transform=add(props,A,'xfrm');add(transform,A,'off',{'x':0,'y':0});add(transform,A,'ext',{'cx':cx,'cy':cy})
    add(add(props,A,'prstGeom',{'prst':'rect'}),A,'avLst')
    return p


def table_node(body,item):
    table=element(body,'tbl');props=element(table,'tblPr');element(props,'tblW',{'w':5000,'type':'pct'})
    borders=element(props,'tblBorders')
    for edge in ['top','left','bottom','right','insideH','insideV']:element(borders,edge,{'val':'single','sz':4,'color':'808080'})
    grid=element(table,'tblGrid');columns=max(len(r) for r in item['rows'])
    for _ in range(columns):element(grid,'gridCol',{'w':max(1,round(item['rect'].width*20/columns))})
    for values in item['rows']:
        row=element(table,'tr')
        for value in values:
            cell=element(row,'tc');element(element(cell,'tcPr'),'tcW',{'w':max(1,round(item['rect'].width*20/columns)),'type':'dxa'})
            p=element(cell,'p')
            for i,line in enumerate(value.split('\n')):
                if i:element(element(p,'r'),'br')
                text_run(p,line)
    return table


def export_docx(base,operations,pages,keep_lines=True,include_images=False,include_tables=False,include_links=False):
    if any(type(v) is not bool for v in [keep_lines,include_images,include_tables,include_links]):raise DocumentError('Las opciones de Word deben ser verdaderas o falsas.')
    with open_pdf(base) as source:
        if not source.permissions&f.PDF_PERM_COPY:raise DocumentError('El documento no permite exportar su texto.')
        selected_pages(source,pages)
    if len(pages)>50:raise DocumentError('Exporta hasta 50 páginas a Word por operación.')
    if include_tables and len(pages)>20:raise DocumentError('Selecciona hasta 20 páginas al detectar tablas para Word.')
    snapshot=export_pdf(base,operations);document=Element(tag('document'));body=element(document,'body');media=[];hyperlinks={}
    budget={'tables':0,'cells':0,'images_seen':0,'media_bytes':0}
    report={'schema':'reapdf-docx-2','source_sha256':hashlib.sha256(snapshot).hexdigest(),'pages':[],'characters':0,'runs':0,'keep_lines':keep_lines,'editable_text':True,'images_included':include_images,'tables_enabled':include_tables,'images':0,'tables':0,'cells':0,'ocr':False,'layout_preserved':False,'links_enabled':include_links,'links':0}
    def account(text,runs=1):
        report['characters']+=len(text);report['runs']+=runs
        if report['characters']>MAX_CHARACTERS or report['runs']>MAX_RUNS:raise DocumentError('El texto supera 100000 caracteres o 20000 fragmentos para esta exportación.')
    link_budget=0
    with open_pdf(snapshot) as doc:
        for index,number in enumerate(pages):
            page=doc[number];count_before=report['characters'];fonts=set();last=None
            tables,table_skipped=page_tables(page,budget) if include_tables else ([],[])
            images,image_skipped=page_images(page,budget) if include_images else ([],[])
            links,link_skipped=page_links(page) if include_links else ([],[])
            link_budget+=len(links)+len(link_skipped)
            if link_budget>1000:raise DocumentError('Word admite hasta 1000 enlaces web por documento.')
            blocks=page.get_text('dict',flags=f.TEXTFLAGS_TEXT,sort=True)['blocks'];items=[]
            for table in tables:items.append((table['rect'].y0,table['rect'].x0,'table',table))
            for image in images:items.append((image['rect'].y0,image['rect'].x0,'image',image))
            for block in blocks:
                lines=[]
                for line in block.get('lines',[]):
                    spans=[span for span in line['spans'] if not any((table['rect']+(-1,-1,1,1)).contains(f.Rect(span['bbox'])) for table in tables)]
                    if spans:lines.append({**line,'spans':spans})
                if lines:items.append((block['bbox'][1],block['bbox'][0],'text',lines))
            for _,__,kind,item in sorted(items,key=lambda v:(v[0],v[1])):
                if kind=='image':
                    media.append(item);last=image_paragraph(body,item,len(media),page);report['images']+=1
                elif kind=='table':
                    for row in item['rows']:
                        for value in row:account(clean(value),value.count('\n')+1)
                    table_node(body,item);last=element(body,'p');report['tables']+=1
                else:
                    p=element(body,'p');last=p
                    for li,line in enumerate(item):
                        if li:
                            if keep_lines:element(element(p,'r'),'br')
                            else:text_run(p,' ')
                        for span in line['spans']:
                            text=clean(span['text']);account(text);fonts.add(span['font'])
                            uri=span_link(span,links) if include_links else None
                            parent=p
                            if uri:
                                if uri not in hyperlinks:hyperlinks[uri]=f'rIdLink{len(hyperlinks)+1}'
                                parent=element(p,'hyperlink');parent.set('{'+R+'}id',hyperlinks[uri])
                            text_run(parent,text,span)
            if last is None:last=element(body,'p')
            if index<len(pages)-1:section(element(last,'pPr'),page.rect.width,page.rect.height)
            else:section(body,page.rect.width,page.rect.height)
            report['links']+=sum(item['used'] for item in links)
            for item in links:
                if not item['used'] or item['partial']:link_skipped.append({'reason':'Enlace sin fragmentos completos o con coincidencia parcial/ambigua; no se vinculan esos fragmentos.'})
            report['pages'].append({'page':number+1,'characters':report['characters']-count_before,'fonts':sorted(fonts),'rotation':page.rotation,'word_size_scaled':max(page.rect.width,page.rect.height)>1584,'has_digital_text':report['characters']>count_before,'images':len(images),'images_skipped':image_skipped,'links':sum(item['used'] for item in links),'links_skipped':link_skipped,'tables':[{'bbox':t['bbox'],'rows':t['rows']} for t in tables],'tables_skipped':table_skipped})
    report['cells']=budget['cells']
    if not report['characters'] and not media:raise DocumentError('No hay texto digital ni imágenes compatibles para convertir. Ejecuta OCR y revisa su resultado antes de exportar a Word.')
    for p in body.findall(tag('p')):
        props=p.find(tag('pPr'))
        if props is not None:p.remove(props);p.insert(0,props)
    styles=Element(tag('styles'));normal=element(styles,'style',{'type':'paragraph','default':1,'styleId':'Normal'});element(normal,'name',{'val':'Normal'})
    props=element(normal,'rPr');element(props,'rFonts',{'ascii':'Arial','hAnsi':'Arial'});element(props,'sz',{'val':22});element(props,'lang',{'val':'es-PE'})
    types=b'''<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'''
    rels=b'''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'''
    if media:
        types=types.replace(b'</Types>',b'<Default Extension="png" ContentType="image/png"/><Default Extension="jpeg" ContentType="image/jpeg"/></Types>')
    relations=Element('{'+RPKG+'}Relationships')
    SubElement(relations,'{'+RPKG+'}Relationship',{'Id':'rIdStyles','Type':R+'/styles','Target':'styles.xml'})
    for i,item in enumerate(media,1):
        SubElement(relations,'{'+RPKG+'}Relationship',{'Id':f'rIdImage{i}','Type':R+'/image','Target':f'media/image{i}.{item["ext"]}'})
    for uri,identifier in hyperlinks.items():
        SubElement(relations,'{'+RPKG+'}Relationship',{'Id':identifier,'Type':R+'/hyperlink','Target':uri,'TargetMode':'External'})
    word_rels=xml(relations)
    stream=BytesIO()
    with ZipFile(stream,'w',ZIP_DEFLATED) as archive:
        for name,data in [('[Content_Types].xml',types),('_rels/.rels',rels),('word/document.xml',xml(document)),('word/styles.xml',xml(styles)),('word/_rels/document.xml.rels',word_rels)]:archive.writestr(name,data)
        for i,item in enumerate(media,1):archive.writestr(f'word/media/image{i}.{item["ext"]}',item['data'])
    output=stream.getvalue()
    if len(output)>20*1024*1024:raise DocumentError('El documento Word supera 20 MB.')
    report['output_bytes']=len(output)
    return output,report
