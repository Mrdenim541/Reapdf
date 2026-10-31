"""Bounded Word note definitions, numbering, local relationships and foot layout."""
from copy import deepcopy
from pathlib import Path
from collections import defaultdict
import html,posixpath,re
from xml.etree import ElementTree as E
import pymupdf as f
from .engine import DocumentError
from .docx_fields import number_label
from .docx_headers import relationships
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PREFIX='REAPDF_NOTE_20261030_'
def tag(name):return '{'+W+'}'+name


class Notes:
    def __init__(self,package,rels,parse_xml,warnings):
        self.package=package;self.parse_xml=parse_xml;self.warnings=warnings;self.definitions={};self.rels={};self.used={};self.by_segment=defaultdict(list);self.current=0;self.counter={'footnote':1,'endnote':1};self.style={'footnote':'decimal','endnote':'lowerRoman'};self.placement={'footnote':'pageBottom','endnote':'docEnd'};self.defaults={};self.rendered={};self.inside=False;self.marker_font=None
        if any(PREFIX.encode() in raw for raw in package.values()):raise DocumentError('El Word contiene un marcador de notas reservado.')
        if 'word/settings.xml' in package:
            settings=parse_xml(package['word/settings.xml'])
            for kind in ['footnote','endnote']:self.defaults[kind]=settings.find(tag(kind+'Pr'))
        for kind in ['footnote','endnote']:
            matches=[v for v in rels.values() if v.get('Type')==R+'/'+kind+'s']
            if len(matches)>1:raise DocumentError('Relaciones de notas Word repetidas.')
            if not matches:
                if 'word/'+kind+'s.xml' in package:warnings.add('Parte de notas sin relación en el documento: no se incorpora.')
                continue
            rel=matches[0];raw=rel.get('Target','');path=posixpath.normpath(posixpath.join('word',raw))
            if rel.get('TargetMode')=='External' or not raw or raw.startswith(('/','\\')) or '\\' in raw or not path.startswith('word/') or path not in package:raise DocumentError('La parte de notas debe ser un recurso local válido del Word.')
            root=parse_xml(package[path])
            if root.tag!=tag(kind+'s'):raise DocumentError('Tipo de parte de notas Word incorrecto.')
            data={}
            for note in root:
                if note.tag!=tag(kind):raise DocumentError('Elemento de notas Word no compatible.')
                raw=note.attrib.get(tag('id'),'')
                if not re.fullmatch(r'-?\d{1,9}',raw):raise DocumentError('Identificador de nota Word no válido.')
                ident=int(raw)
                if ident in data:raise DocumentError('Identificadores de nota Word repetidos.')
                kind_=note.attrib.get(tag('type'),'normal')
                if kind_ in ['separator','continuationSeparator','continuationNotice']:
                    data[ident]=None;continue
                if kind_!='normal' or ident<0:raise DocumentError('Tipo o identificador de nota no compatible.')
                if any(n.tag in {tag(k) for k in ['del','ins','moveFrom','moveTo','object','altChunk','footnoteReference','endnoteReference']} for n in note.iter()):raise DocumentError('Resuelve revisiones, objetos o referencias anidadas dentro de las notas antes de importar.')
                data[ident]=note
                if len(data)>202:raise DocumentError('Hasta 200 notas por parte Word, además de sus separadores.')
            self.definitions[kind]=data;self.rels[kind]=relationships(package,posixpath.join(posixpath.dirname(path),'_rels',posixpath.basename(path)+'.rels'),parse_xml)
            # Image paths in notes are resolved relative to their own local part.
            for rel in self.rels[kind].values():
                if rel.get('TargetMode')!='External' and rel.get('Target'):
                    target=posixpath.normpath(posixpath.join(posixpath.dirname(path),rel['Target']))
                    if not target.startswith('word/'):raise DocumentError('Un recurso de notas sale del directorio Word.')
                    rel['Target']=posixpath.relpath(target,'word')

    def begin(self,section,index):
        self.current=index
        for kind in ['footnote','endnote']:
            if kind not in getattr(self,'active',{'footnote','endnote'}):continue
            nodes=[n for n in [self.defaults.get(kind),section.find(tag(kind+'Pr'))] if n is not None];options={}
            for node in nodes:
                for item in node:
                    name=item.tag.rsplit('}',1)[-1]
                    if name in ['numFmt','numStart','numRestart','pos']:options[name]=item.attrib.get(tag('val'),'')
            fmt=options.get('numFmt','decimal' if kind=='footnote' else 'lowerRoman');restart=options.get('numRestart','continuous');start=options.get('numStart','1');placement=options.get('pos','pageBottom' if kind=='footnote' else 'docEnd')
            if fmt not in ['decimal','lowerRoman','upperRoman','lowerLetter','upperLetter'] or restart not in ['continuous','eachSect'] or not re.fullmatch(r'\d{1,4}',start) or not 1<=int(start)<=9999:raise DocumentError('Numeración de notas no compatible: usa formato estándar y continuidad o reinicio por sección.')
            if placement not in (['pageBottom'] if kind=='footnote' else ['docEnd','sectEnd']):raise DocumentError('La posición de las notas Word todavía no es compatible.')
            if index==0 or restart=='eachSect':self.counter[kind]=int(start)
            self.style[kind]=fmt;self.placement[kind]=placement

    def reference(self,node,in_running=False,custom_label=None):
        if self.inside or in_running:raise DocumentError('No se admiten referencias de notas dentro de otras notas, encabezados o pies.')
        kind='footnote' if node.tag==tag('footnoteReference') else 'endnote';raw=node.attrib.get(tag('id'),'')
        if not re.fullmatch(r'\d{1,9}',raw) or node.attrib.get(tag('customMarkFollows'),'0') not in ['0','false','1','true']:raise DocumentError('La referencia de nota necesita un identificador y marcador compatibles.')
        custom=node.attrib.get(tag('customMarkFollows'),'0') in ['1','true']
        if custom!=(custom_label is not None) or custom and (not isinstance(custom_label,str) or not 1<=len(custom_label)<=4 or any(c.isspace() or not c.isprintable() for c in custom_label)):raise DocumentError('El marcador personalizado necesita de uno a cuatro caracteres visibles en el mismo fragmento.')
        if custom:
            if self.marker_font is None:self.marker_font=f.Font(fontfile=str(Path(__file__).resolve().parent.parent/'resources/fonts/DejaVuSans.ttf'))
            if any(not self.marker_font.has_glyph(ord(c),fallback=0) for c in custom_label):raise DocumentError('La fuente incluida no cubre la marca personalizada de la nota.')
        ident=int(raw);key=(kind,ident)
        if key in self.used:raise DocumentError('Una definición de nota tiene referencias repetidas; usa un enlace NOTEREF explícito antes de importar.')
        definition=self.definitions.get(kind,{}).get(ident)
        if definition is None:raise DocumentError('Falta el contenido de una nota referenciada; no se importa un documento incompleto.')
        if len(self.used)>=200:raise DocumentError('Hasta 200 referencias de notas por documento.')
        label=custom_label if custom else number_label(self.counter[kind],self.style[kind])
        if not custom:self.counter[kind]+=1
        stem=PREFIX+kind+'_'+str(ident);item={'kind':kind,'id':ident,'custom':custom,'label':label,'ref':stem+'_ref','dest':stem+'_body','node':definition,'segment':self.current,'placement':self.placement[kind]};self.used[key]=item;self.by_segment[self.current].append(item)
        return '<sup><a id="'+item['ref']+'" href="#'+item['dest']+'">'+html.escape(label)+'</a></sup>'

    def render(self,render):
        for key,item in self.used.items():
            self.inside=True
            try:
                definition=deepcopy(item['node'])
                if item['custom']:
                    first=next(definition.iter(tag('t')),None)
                    if first is not None and first.text and first.text.startswith(item['label']):
                        following=first.text[len(item['label']):]
                        # Remove only an explicit standalone/reviewable mark,
                        # never an arbitrary prefix of a source word.
                        if not following or following[0].isspace():first.text=following.lstrip()
                content=render(definition,self.rels[item['kind']])
            finally:self.inside=False
            self.rendered[key]='<div class="word-note" id="'+item['dest']+'"><p class="word-note-label"><a href="#'+item['ref']+'">'+html.escape(item['label'])+('' if item['custom'] else '.')+'</a></p>'+content+'</div>'
        unused=sum(1 for kind,data in self.definitions.items() for ident,node in data.items() if node is not None and (kind,ident) not in self.used)
        if unused:self.warnings.add(f'{unused} definiciones de notas sin referencia no se incorporan.')

    def foot(self,index):return {item['ref']:item for item in self.by_segment[index] if item['kind']=='footnote'}
    def end_content(self,index,last):
        items=[v for v in self.used.values() if v['kind']=='endnote' and (v['placement']=='sectEnd' and v['segment']==index or v['placement']=='docEnd' and index==last)]
        return ('<div class="word-endnotes"><h3>Notas finales</h3>'+''.join(self.rendered[(v['kind'],v['id'])] for v in items)+'</div>') if items else ''
    def page_content(self,items):return '<div class="word-footnotes">'+''.join(self.rendered[(v['kind'],v['id'])] for v in items)+'</div>'

    def prepare(self,index,content,css,archive,width,height,left,top,right,bottom,max_pages):
        refs=self.foot(index);story=f.Story('<html><body>'+content+'</body></html>',user_css=css,archive=archive);reserves={};previous=None
        for attempt in range(12):
            positions={};count=[0]
            def position(node):
                if node.id in refs and node.open_close&1 and not f.Rect(node.rect).is_empty:positions.setdefault(node.id,node.page_num-1)
            def rect(n,filled):
                if n>=max_pages:raise DocumentError('El Word necesita más de 50 páginas o tiene notas que no caben.')
                count[0]=n+1;reserve=reserves.get(n,0)
                if height-bottom-reserve-top<72:raise DocumentError('Las notas no dejan espacio suficiente para el texto de su página.')
                return f.Rect(0,0,width,height),f.Rect(left,top,width-right,height-bottom-reserve),None
            story.write(None,rect,positionfn=position);story.reset()
            if set(positions)!=set(refs):raise DocumentError('No se localizaron todas las referencias de notas al paginar.')
            by_page=defaultdict(list)
            for ref,page in positions.items():by_page[page].append(refs[ref])
            needed={};grew=False
            for page,items in by_page.items():
                html_=self.page_content(items);note_story=f.Story(html_,user_css=css,archive=archive);cap=min(216,(height-top-bottom)*.4);region=f.Rect(left,0,width-right,cap);more,filled=note_story.place(region)
                if more or f.Rect(filled).x1>region.x1+.1:raise DocumentError('Las notas de una página superan el espacio disponible. Simplifícalas o conviértelas a notas finales antes de importar.')
                needed[page]=f.Rect(filled).y1+8
                if needed[page]>reserves.get(page,0)+.05:reserves[page]=needed[page];grew=True
            if not refs or not grew and positions==previous:return {'story':story,'count':count[0],'reserves':reserves,'foot_pages':dict(by_page),'foot_heights':needed,'ref_pages':positions,'passes':attempt+1}
            previous=positions
        raise DocumentError('La distribución de las notas no converge dentro del límite. No se entrega un PDF incompleto.')

    def draw(self,plan,page,width,height,left,right,bottom,css,archive,device,position):
        items=plan['foot_pages'].get(page-1)
        if not items:return
        reserve=plan['foot_heights'][page-1];rect=f.Rect(left,height-bottom-reserve+8,width-right,height-bottom+.05);story=f.Story(self.page_content(items),user_css=css,archive=archive);more,filled=story.place(rect)
        if more or f.Rect(filled).y1>rect.y1+.1:raise DocumentError('Una nota no cabe completa en su página. No se entrega un PDF recortado.')
        def record(node):node.page_num=page;position(node)
        story.element_positions(record);story.draw(device)

    def report(self):return {'footnotes':sum(v['kind']=='footnote' for v in self.used.values()),'endnotes':sum(v['kind']=='endnote' for v in self.used.values()),'custom_note_marks':sum(v['custom'] for v in self.used.values()),'note_references':len(self.used),'notes_layout':'page_bottom_and_endnotes','notes_code_executed':False}


def checked_text(doc,positions):
    """Exclude only generated reference glyphs, preserving surrounding source words."""
    markers=defaultdict(list)
    for node in positions:
        if node.open_close&1 and node.id and node.id.startswith(PREFIX) and node.id.endswith('_ref'):markers[node.page_num-1].append(f.Rect(node.rect)+(-.4,-.4,.4,.4))
    result=[]
    for page in doc:
        for block in page.get_text('rawdict',flags=f.TEXTFLAGS_TEXT)['blocks']:
            for line in block.get('lines',[]):
                text=[]
                for span in line['spans']:
                    for char in span['chars']:
                        rect=f.Rect(char['bbox']);center=f.Point((rect.x0+rect.x1)/2,(rect.y0+rect.y1)/2)
                        text.append(' ' if any(r.contains(center) for r in markers[page.number]) else char['c'])
                result.append(''.join(text))
    return '\n'.join(result)
